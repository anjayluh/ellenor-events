import { PortalShell } from "../../components/PortalShell";
import { StaffClientPage } from "../../components/ProtectedPages";

export default function StaffPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Ellenor Events Team</p>
        <h1>Operational oversight for active events.</h1>
        <p>Team members can review event health, risk alerts, and follow-up activity in one place.</p>
      </section>
      <StaffClientPage />
    </PortalShell>
  );
}
