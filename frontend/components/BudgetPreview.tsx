type BudgetVisibility = "FULL_ACCESS" | "SUMMARY_ACCESS" | "CONTRIBUTION_ONLY" | "NO_ACCESS";

const visibilityCopy: Record<BudgetVisibility, string> = {
  FULL_ACCESS: "You can view totals, spend, remaining balance, line items, and contribution records.",
  SUMMARY_ACCESS: "You can view totals and contribution progress without sensitive spend details.",
  CONTRIBUTION_ONLY: "You can view contribution progress only.",
  NO_ACCESS: "Budget details are hidden for this role."
};

export function BudgetPreview({ visibility }: { visibility: BudgetVisibility }) {
  return (
    <aside className="panel">
      <p className="eyebrow">Budget Visibility</p>
      <h2>{visibility.replaceAll("_", " ")}</h2>
      <p>{visibilityCopy[visibility]}</p>
    </aside>
  );
}
