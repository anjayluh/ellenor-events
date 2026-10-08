import { PortalShell } from "../../components/PortalShell";
import { MeetingsWorkspace } from "../../components/MeetingsWorkspace";

export default function MeetingsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Meetings</p>
        <h1>Keep committees and family aligned without the chaos swirl.</h1>
        <p>Open an event workspace to track meetings, notes, decisions, and follow-ups.</p>
      </section>
      <MeetingsWorkspace />
    </PortalShell>
  );
}
