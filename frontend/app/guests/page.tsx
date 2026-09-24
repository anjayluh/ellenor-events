import { GuestInvitesClientPage } from "../../components/GuestInvitesClientPage";
import { PortalShell } from "../../components/PortalShell";

export default function GuestsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Guests</p>
        <h1>Manage invitations and RSVPs for this event.</h1>
        <p>Add guests, organize them by family or group, send invitation emails, and track RSVP responses without giving guests access to the internal workspace.</p>
      </section>
      <GuestInvitesClientPage />
    </PortalShell>
  );
}
