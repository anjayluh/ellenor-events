"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { formatDate } from "../lib/customer-display";
import { StateBlock } from "./StateBlock";

type RsvpStatus = "PENDING" | "ATTENDING" | "NOT_ATTENDING";

type GuestInvite = {
  token: string;
  recipient_name: string;
  event_title: string;
  event_date?: string | null;
  invitation_card_url?: string | null;
  invitation_status: string;
  rsvp_status: RsvpStatus;
  rsvp_attendee_count: number;
  rsvp_note?: string | null;
  responded_at?: string | null;
};

function statusText(status: RsvpStatus) {
  if (status === "ATTENDING") return "Attending";
  if (status === "NOT_ATTENDING") return "Not attending";
  return "Pending response";
}

export function GuestInviteResponsePage({ token }: { token: string }) {
  const [invite, setInvite] = useState<GuestInvite | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "missing">("loading");
  const [notice, setNotice] = useState("Choose whether you will attend.");
  const [processing, setProcessing] = useState<string | null>(null);
  const [attendeeCount, setAttendeeCount] = useState(1);
  const [responseNote, setResponseNote] = useState("");

  useEffect(() => {
    let mounted = true;
    void apiGet<GuestInvite>(`/guest-rsvps/${token}`).then((nextInvite) => {
      if (!mounted) return;
      setInvite(nextInvite);
      setAttendeeCount(nextInvite.rsvp_attendee_count || 1);
      setResponseNote(nextInvite.rsvp_note ?? "");
      setLoadState("ready");
      setNotice(nextInvite.rsvp_status === "PENDING" ? "Choose whether you will attend." : "Your current RSVP is shown below. You can update it if your plans change.");
    }).catch(() => {
      if (!mounted) return;
      setLoadState("missing");
      setNotice("Invitation not found or no longer available.");
    });
    return () => {
      mounted = false;
    };
  }, [token]);

  async function respond(rsvp_status: "ATTENDING" | "NOT_ATTENDING") {
    const nextCount = rsvp_status === "ATTENDING" ? Math.max(attendeeCount, 1) : 0;
    setProcessing(rsvp_status);
    setNotice("Saving your RSVP...");
    try {
      const nextInvite = await apiPost<GuestInvite, { rsvp_status: RsvpStatus; rsvp_attendee_count: number; rsvp_note: string | null }>(`/guest-rsvps/${token}/respond`, {
        rsvp_status,
        rsvp_attendee_count: nextCount,
        rsvp_note: responseNote.trim() || null
      });
      setInvite(nextInvite);
      setAttendeeCount(nextInvite.rsvp_attendee_count || 1);
      setResponseNote(nextInvite.rsvp_note ?? "");
      setNotice(rsvp_status === "ATTENDING" ? "Thank you. Your attendance is recorded." : "Thank you. Your response has been recorded.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save RSVP.");
    } finally {
      setProcessing(null);
    }
  }

  if (loadState === "loading") return <StateBlock title="Loading invitation" message="We are opening your Ellenor Events invitation." />;
  if (loadState === "missing" || !invite) return <StateBlock title="Invitation not found" message="This invitation may have been changed, removed, or copied incorrectly. Please ask your event host to resend the invitation." />;

  return (
    <section className="grid twoColumns">
      <article className="hero compact">
        <p className="eyebrow">Private Event Invitation</p>
        <h1>{invite.recipient_name}, you are invited</h1>
        <p>{invite.event_title}{invite.event_date ? ` · ${formatDate(invite.event_date)}` : ""}</p>
        <div className="planningAreaList">
          <span className={invite.rsvp_status === "ATTENDING" ? "badge successBadge" : "badge softBadge"}>RSVP: {statusText(invite.rsvp_status)}</span>
          {invite.responded_at ? <span className="badge softBadge">Responded {formatDate(invite.responded_at)}</span> : null}
        </div>
        <label className="formField">
          Number attending
          <input min={1} max={50} type="number" value={attendeeCount} onChange={(event) => setAttendeeCount(Number(event.target.value) || 1)} />
          <span className="helperText">Use 1 unless this invitation covers more than one person.</span>
        </label>
        <label className="formField">
          Note to the host
          <textarea value={responseNote} onChange={(event) => setResponseNote(event.target.value)} placeholder="Optional dietary note, arrival note, or message" rows={3} />
        </label>
        <div className="buttonRow">
          <button className="primaryButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void respond("ATTENDING")}>{processing === "ATTENDING" ? "Saving..." : "I will attend"}</button>
          <button className="secondaryButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => void respond("NOT_ATTENDING")}>{processing === "NOT_ATTENDING" ? "Saving..." : "I cannot attend"}</button>
        </div>
        <p>{notice}</p>
      </article>
      <article className="panel">
        <p className="eyebrow">Invitation Card</p>
        {invite.invitation_card_url ? <div aria-label="Invitation card" className="inviteCardPreview imagePreview contain" role="img" style={{ backgroundImage: `url(${invite.invitation_card_url})` }} /> : <p>The event host has not attached a card yet, but your RSVP link is ready.</p>}
        <p className="helperText">This RSVP page only shows your invitation details. It does not provide access to the host&apos;s planning workspace.</p>
      </article>
    </section>
  );
}
