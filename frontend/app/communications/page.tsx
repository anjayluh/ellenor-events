import { CommunicationsClientPage } from "../../components/CommunicationsClientPage";
import { PortalShell } from "../../components/PortalShell";

export default function CommunicationsPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Communications</p>
        <h1>Keep the planning team aligned.</h1>
        <p>Share important decisions, reminders, and planning notes with the people helping your event come together.</p>
      </section>
      <CommunicationsClientPage />
    </PortalShell>
  );
}
