import { PortalShell } from "../../components/PortalShell";
import { CommitteeClientPage } from "../../components/ProtectedPages";

export default function CommitteePage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Committee</p>
        <h1>Tasks, ownership, and decisions in one place.</h1>
        <p>Authenticated members can view live project-scoped committee work.</p>
      </section>
      <CommitteeClientPage />
    </PortalShell>
  );
}
