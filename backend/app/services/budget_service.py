from app.core.permissions import BudgetVisibilityMode
from app.models.budget import Budget, BudgetLineItem, Contribution
from app.schemas.budget import BudgetRead


def calculate_spend_ratio(total: float, spent: float) -> float:
    if total <= 0:
        return 0
    return round((spent / total) * 100, 2)


def money(value) -> float:
    return float(value or 0)


def shape_budget_response(
    visibility: BudgetVisibilityMode,
    budget: Budget | None,
    contributions: list[Contribution],
    line_items: list[BudgetLineItem] | None = None,
) -> BudgetRead:
    total = money(budget.total if budget else 0)
    spent = money(budget.spent if budget else 0)
    paid_total = sum(money(item.paid) for item in contributions)
    pledged_total = sum(money(item.pledged) for item in contributions)

    if visibility == BudgetVisibilityMode.FULL_ACCESS:
        return BudgetRead(
            visibility=visibility.value,
            total=total,
            spent=spent,
            remaining=max(total - spent, 0),
            contribution_progress=paid_total,
            pledged_total=pledged_total,
            line_items=line_items or [],
            contributions=contributions,
        )

    if visibility == BudgetVisibilityMode.SUMMARY_ACCESS:
        return BudgetRead(
            visibility=visibility.value,
            total=total,
            contribution_progress=paid_total,
            pledged_total=pledged_total,
        )

    if visibility == BudgetVisibilityMode.CONTRIBUTION_ONLY:
        return BudgetRead(visibility=visibility.value, contribution_progress=paid_total)

    return BudgetRead(visibility=visibility.value)
