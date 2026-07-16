import { MyEventsPanel } from "../components/MyEventsPanel";
import { PortalShell } from "../components/PortalShell";

export default function Home() {
  return (
    <PortalShell>
      <section className="hero">
        <p className="eyebrow">Ellenor Events Coordination System</p>
        <h1>A calm command center for ceremonies with many moving parts.</h1>
        <p>
          Coordinate weddings, introductions, committees, meetings, RSVP flows, contributions,
          and budget visibility without exposing sensitive details to people outside the event.
        </p>
      </section>

      <section className="grid twoColumns">
        <MyEventsPanel />
        <aside className="panel">
          <p className="eyebrow">Private by default</p>
          <h2>No personal event data is shown before login.</h2>
          <p>Guests see only public product information until Supabase Auth verifies their account and backend RBAC confirms project membership.</p>
        </aside>
      </section>
    </PortalShell>
  );
}
