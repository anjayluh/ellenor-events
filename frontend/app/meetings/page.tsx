import { PortalShell } from "../../components/PortalShell";
import { MeetingsClientPage } from "../../components/ProtectedPages";

export default function MeetingsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Meetings</p>
        <h1>Keep committees and family aligned without the chaos swirl.</h1>
        <p>Upcoming meetings, notes, decisions, and RSVP responses load from the backend.</p>
      </section>
      <MeetingsClientPage />
    </PortalShell>
  );
}
