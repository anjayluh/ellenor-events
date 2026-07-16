import { PortalShell } from "../../components/PortalShell";
import { StaffClientPage } from "../../components/ProtectedPages";

export default function StaffPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Staff Portal</p>
        <h1>Project health, risk alerts, and RSVP movement.</h1>
        <p>Internal-only oversight uses staff roles, separate from client project roles.</p>
      </section>
      <StaffClientPage />
    </PortalShell>
  );
}
