import { PortalShell } from "../../components/PortalShell";

const visibilityCards = [
  { mode: "FULL_ACCESS", detail: "Totals, spent amount, line items, proposals, and contributions." },
  { mode: "SUMMARY_ACCESS", detail: "Total budget and contribution progress without spend breakdown." },
  { mode: "CONTRIBUTION_ONLY", detail: "Contribution progress only. No totals or spend details." },
  { mode: "NO_ACCESS", detail: "Budget tab is hidden or blocked by the backend." }
];

const lineItems = [
  { category: "Decor", estimate: "UGX 4,500,000", actual: "UGX 1,500,000" },
  { category: "Catering", estimate: "UGX 16,000,000", actual: "UGX 4,500,000" },
  { category: "Photography", estimate: "UGX 3,800,000", actual: "UGX 0" }
];

export default function BudgetPage() {
  return (
    <PortalShell>
      <section className="hero compact">
        <p className="eyebrow">Budget</p>
        <h1>Financial clarity, without leaking sensitive details.</h1>
        <p>Backend-shaped visibility controls what each role can see before data reaches the interface.</p>
      </section>

      <section className="grid fourColumns">
        {visibilityCards.map((card) => (
          <article className="panel" key={card.mode}>
            <p className="eyebrow">{card.mode.replaceAll("_", " ")}</p>
            <p>{card.detail}</p>
          </article>
        ))}
      </section>

      <section className="grid twoColumns">
        <article className="panel">
          <h2>Owner Export View</h2>
          <p>Total: UGX 42,000,000</p>
          <p>Spent: UGX 7,500,000</p>
          <p>Remaining: UGX 34,500,000</p>
          <button className="primaryButton">Export report</button>
        </article>
        <article className="panel">
          <h2>Contribution Progress</h2>
          <p>Paid: UGX 4,500,000</p>
          <div className="progressTrack"><div className="progressFill" /></div>
        </article>
      </section>

      <section className="grid threeColumns">
        {lineItems.map((item) => (
          <article className="panel" key={item.category}>
            <p className="eyebrow">{item.category}</p>
            <p>Estimated: {item.estimate}</p>
            <p>Actual: {item.actual}</p>
          </article>
        ))}
      </section>
    </PortalShell>
  );
}
