import { PortalShell } from "../../components/PortalShell";
import { TimelineClientPage } from "../../components/TimelineClientPage";

export default function TimelinePage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Timeline</p>
        <h1>Plan the order, timing and responsibilities for the event day.</h1>
        <p>Build a clear schedule for ceremonies, family moments, vendors, travel, photography, meals, and everything that needs to happen on time.</p>
      </section>
      <TimelineClientPage />
    </PortalShell>
  );
}
