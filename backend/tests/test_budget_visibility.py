from uuid import uuid4

from app.core.permissions import BudgetVisibilityMode
from app.models.budget import Budget, BudgetLineItem, Contribution
from app.services.budget_service import shape_budget_response


def make_budget():
    return Budget(project_id=uuid4(), total=42000000, spent=7500000)


def make_contributions():
    return [
        Contribution(
            id=uuid4(),
            project_id=uuid4(),
            contributor="Committee",
            pledged=12000000,
            paid=4500000,
            status="partial",
        )
    ]


def make_line_items():
    return [
        BudgetLineItem(
            id=uuid4(),
            project_id=uuid4(),
            category="Catering",
            description="Reception catering",
            estimated_amount=16000000,
            actual_amount=4500000,
            status="approved",
        )
    ]


def test_full_access_budget_response_includes_sensitive_detail():
    response = shape_budget_response(
        BudgetVisibilityMode.FULL_ACCESS,
        make_budget(),
        make_contributions(),
        make_line_items(),
    )

    assert response.total == 42000000
    assert response.spent == 7500000
    assert response.remaining == 34500000
    assert response.line_items is not None
    assert response.contributions is not None


def test_summary_access_budget_response_hides_spend_and_line_items():
    response = shape_budget_response(
        BudgetVisibilityMode.SUMMARY_ACCESS,
        make_budget(),
        make_contributions(),
        make_line_items(),
    )

    assert response.total == 42000000
    assert response.contribution_progress == 4500000
    assert response.spent is None
    assert response.remaining is None
    assert response.line_items is None
    assert response.contributions is None


def test_contribution_only_budget_response_hides_totals_and_spend():
    response = shape_budget_response(
        BudgetVisibilityMode.CONTRIBUTION_ONLY,
        make_budget(),
        make_contributions(),
        make_line_items(),
    )

    assert response.contribution_progress == 4500000
    assert response.total is None
    assert response.spent is None
    assert response.remaining is None
    assert response.line_items is None
    assert response.contributions is None
