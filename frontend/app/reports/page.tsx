import { PortalShell } from "../../components/PortalShell";
import { ReportsClientPage } from "../../components/ReportsClientPage";

export default function ReportsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Event reports</p>
        <h1>See the shape of your planning at a glance.</h1>
        <p>Review the latest guest, budget, vendor, task, schedule, meeting, document, and communication information for the selected event.</p>
      </section>
      <ReportsClientPage />
    </PortalShell>
  );
}
