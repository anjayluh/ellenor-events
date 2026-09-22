import { PortalShell } from "../../components/PortalShell";
import { BudgetTableClientPage } from "../../components/BudgetTableClientPage";

export default function BudgetPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Budget</p>
        <h1>Financial clarity, without leaking sensitive details.</h1>
        <p>Open an event workspace to review budget totals, deposits, balances, and upcoming payment dates.</p>
      </section>
      <BudgetTableClientPage />
    </PortalShell>
  );
}
