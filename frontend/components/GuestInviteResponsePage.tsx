"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { StateBlock } from "./StateBlock";

type GuestInvite = { guest_name: string; invitation_card_url?: string | null; attendance_status: string; status: string; token: string };

export function GuestInviteResponsePage({ token }: { token: string }) {
  const [invite, setInvite] = useState<GuestInvite | null>(null);
  const [notice, setNotice] = useState("Choose whether you will attend.");
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    void apiGet<GuestInvite>(`/guest-invites/${token}`).then(setInvite).catch(() => setNotice("This invitation could not be loaded."));
  }, [token]);

  async function respond(attendance_status: "accepted" | "declined" | "cancelled") {
    setProcessing(attendance_status);
    setNotice("Saving your RSVP...");
    try {
      const nextInvite = await apiPost<GuestInvite, { attendance_status: string }>(`/guest-invites/${token}/respond`, { attendance_status });
      setInvite(nextInvite);
      setNotice(attendance_status === "accepted" ? "Thank you. Your attendance is recorded." : "Your response has been recorded.");
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
        <h1>{invite.guest_name}, you are invited</h1>
        <p>Status: {invite.attendance_status.replaceAll("_", " ")}</p>
        <div className="buttonRow">
          <button className="primaryButton" data-icon="✓" disabled={Boolean(processing)} type="button" onClick={() => void respond("accepted")}>{processing === "accepted" ? "Saving..." : "I will attend"}</button>
          <button className="secondaryButton" data-icon="×" disabled={Boolean(processing)} type="button" onClick={() => void respond("declined")}>{processing === "declined" ? "Saving..." : "I cannot attend"}</button>
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
