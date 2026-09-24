"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { formatDate } from "../lib/customer-display";
import { StateBlock } from "./StateBlock";

type GuestInvite = {
  token: string;
  recipient_name: string;
  event_title: string;
  event_date?: string | null;
  invitation_card_url?: string | null;
  invitation_status: string;
  rsvp_status: "PENDING" | "ATTENDING" | "NOT_ATTENDING";
  responded_at?: string | null;
};

export function GuestInviteResponsePage({ token }: { token: string }) {
  const [invite, setInvite] = useState<GuestInvite | null>(null);
  const [notice, setNotice] = useState("Choose whether you will attend.");
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    void apiGet<GuestInvite>(`/guest-rsvps/${token}`).then(setInvite).catch(() => setNotice("This invitation could not be loaded."));
  }, [token]);

  async function respond(rsvp_status: "ATTENDING" | "NOT_ATTENDING") {
    setProcessing(rsvp_status);
    setNotice("Saving your RSVP...");
    try {
      const nextInvite = await apiPost<GuestInvite, { rsvp_status: string }>(`/guest-rsvps/${token}/respond`, { rsvp_status });
      setInvite(nextInvite);
      setNotice(rsvp_status === "ATTENDING" ? "Thank you. Your attendance is recorded." : "Thank you. Your response has been recorded.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save RSVP.");
    } finally {
      setProcessing(null);
    }
  }

  if (!invite) return <StateBlock title="Loading invitation" message={notice} />;

  return (
    <section className="grid twoColumns">
      <article className="hero compact">
        <p className="eyebrow">Event Invitation</p>
        <h1>{invite.recipient_name}, you are invited</h1>
        <p>{invite.event_title}{invite.event_date ? ` · ${formatDate(invite.event_date)}` : ""}</p>
        <p>RSVP status: {invite.rsvp_status.toLowerCase().replaceAll("_", " ")}</p>
        <div className="buttonRow">
          <button className="primaryButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void respond("ATTENDING")}>{processing === "ATTENDING" ? "Saving..." : "I will attend"}</button>
          <button className="secondaryButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => void respond("NOT_ATTENDING")}>{processing === "NOT_ATTENDING" ? "Saving..." : "I cannot attend"}</button>
        </div>
        <p>{notice}</p>
      </article>
      <article className="panel">
        <p className="eyebrow">Invitation Card</p>
        {invite.invitation_card_url ? <div aria-label="Invitation card" className="inviteCardPreview imagePreview contain" role="img" style={{ backgroundImage: `url(${invite.invitation_card_url})` }} /> : <p>The event manager has not attached a card yet.</p>}
      </article>
    </section>
  );
}
