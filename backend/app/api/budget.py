from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_budget_visibility, membership_role
from app.core.permissions import BUDGET_WRITE_ROLES, BudgetVisibilityMode, require_budget_read, require_role
from app.db.session import get_db
from app.models.budget import Budget, Contribution
from app.schemas.budget import BudgetRead, BudgetUpdate

router = APIRouter()


@router.get("", response_model=BudgetRead)
def get_budget(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    visibility = membership_budget_visibility(membership)
    require_budget_read(visibility)
    budget = db.query(Budget).filter(Budget.project_id == project_id).first()
    contributions = db.query(Contribution).filter(Contribution.project_id == project_id).all()
    total_paid = sum(float(item.paid or 0) for item in contributions)

    if visibility == BudgetVisibilityMode.FULL_ACCESS:
        return BudgetRead(visibility=visibility, total=float(budget.total if budget else 0), spent=float(budget.spent if budget else 0), contribution_progress=total_paid)
    if visibility == BudgetVisibilityMode.SUMMARY_ACCESS:
        return BudgetRead(visibility=visibility, total=float(budget.total if budget else 0), contribution_progress=total_paid)
    return BudgetRead(visibility=visibility, contribution_progress=total_paid)


@router.patch("", response_model=BudgetRead)
def update_budget(project_id: UUID, payload: BudgetUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    budget = db.query(Budget).filter(Budget.project_id == project_id).first() or Budget(project_id=project_id)
    budget.total = payload.total
    budget.spent = payload.spent
    db.merge(budget)
    db.commit()
    return BudgetRead(visibility="FULL_ACCESS", total=payload.total, spent=payload.spent)
