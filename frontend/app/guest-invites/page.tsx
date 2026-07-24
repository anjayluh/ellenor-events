import { GuestInvitesClientPage } from "../../components/GuestInvitesClientPage";
import { PortalShell } from "../../components/PortalShell";

export default function GuestInvitesPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Guest RSVPs</p>
        <h1>Invite guests without giving them committee access.</h1>
        <p>Upload or link the invitation card, send email notifications, and track accepted, declined, pending, and rejected attendance.</p>
      </section>
      <GuestInvitesClientPage />
    </PortalShell>
  );
}
