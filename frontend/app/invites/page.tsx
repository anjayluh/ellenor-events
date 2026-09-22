import { InvitesClientPage } from "../../components/ProtectedPages";
import { PortalShell } from "../../components/PortalShell";

export default function InvitesPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Invites</p>
        <h1>Email-based onboarding for every event team.</h1>
        <p>Manage guest invitations, committee access, and RSVP follow-up for the selected event.</p>
      </section>
      <InvitesClientPage />
    </PortalShell>
  );
}
