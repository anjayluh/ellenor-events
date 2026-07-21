import { InvitesClientPage } from "../../components/ProtectedPages";
import { PortalShell } from "../../components/PortalShell";

export default function InvitesPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Invites</p>
        <h1>Email-based onboarding for every event team.</h1>
        <p>Invite partners, committee leads, family viewers, and guests into the selected event with project-scoped permissions.</p>
      </section>
      <InvitesClientPage />
    </PortalShell>
  );
}
