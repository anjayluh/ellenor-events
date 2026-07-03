import { PortalShell } from "../../components/PortalShell";

export default function StaffPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Staff Portal</p>
        <h1>Project health, risk alerts, and RSVP movement.</h1>
      </section>
      <section className="grid threeColumns">
        <article className="metric"><span>Active projects</span><strong>0</strong></article>
        <article className="metric"><span>Pending RSVPs</span><strong>0</strong></article>
        <article className="metric"><span>Risk alerts</span><strong>0</strong></article>
      </section>
    </PortalShell>
  );
}
