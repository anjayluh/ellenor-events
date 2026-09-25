import { PortalShell } from "../../components/PortalShell";
import { BudgetTableClientPage } from "../../components/BudgetTableClientPage";

export default function BudgetPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Budget</p>
        <h1>Plan every commitment with calm financial clarity.</h1>
        <p>Open an event workspace to track planned costs, vendor-linked commitments, deposits, balances, and upcoming payment dates.</p>
      </section>
      <BudgetTableClientPage />
    </PortalShell>
  );
}
