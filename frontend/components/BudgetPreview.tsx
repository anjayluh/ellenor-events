type BudgetVisibility = "FULL_ACCESS" | "SUMMARY_ACCESS" | "CONTRIBUTION_ONLY" | "NO_ACCESS";

export function BudgetPreview({ visibility }: { visibility: BudgetVisibility }) {
  const canSeeTotals = visibility === "FULL_ACCESS" || visibility === "SUMMARY_ACCESS";

  return (
    <aside className="panel">
      <p className="eyebrow">Budget Visibility</p>
      <h2>{visibility.replaceAll("_", " ")}</h2>
      {canSeeTotals ? <p>Total budget summary: UGX 42,000,000</p> : <p>Contribution progress only.</p>}
      <div className="progressTrack" aria-label="Contribution progress">
        <div className="progressFill" />
      </div>
    </aside>
  );
}
