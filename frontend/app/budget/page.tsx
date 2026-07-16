import { PortalShell } from "../../components/PortalShell";
import { BudgetClientPage } from "../../components/ProtectedPages";

export default function BudgetPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Budget</p>
        <h1>Financial clarity, without leaking sensitive details.</h1>
        <p>Backend-shaped visibility controls what each role can see before data reaches the interface.</p>
      </section>
      <BudgetClientPage />
    </PortalShell>
  );
}
