import { MyEventsPanel } from "../components/MyEventsPanel";
import { PortalShell } from "../components/PortalShell";

export default function Home() {
  return (
    <PortalShell>
      <section className="hero">
        <p className="eyebrow">Ellenor Events</p>
        <h1>A calm command center for ceremonies with many moving parts.</h1>
        <p>
          Coordinate weddings, introductions, committees, meetings, RSVP flows, contributions,
          and budget visibility without exposing sensitive details to people outside the event.
        </p>
      </section>

      <section className="grid twoColumns">
        <MyEventsPanel />
        <aside className="panel">
          <p className="eyebrow">Event Workspaces</p>
          <h2>Every event stays organized in its own workspace.</h2>
          <p>Open an event to see the planning tools and details that have been shared with your account.</p>
        </aside>
      </section>
    </PortalShell>
  );
}
