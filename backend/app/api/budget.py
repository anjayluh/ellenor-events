from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_budget_visibility, membership_role
from app.core.permissions import BUDGET_WRITE_ROLES, PROJECT_ADMIN_ROLES, BudgetVisibilityMode, ProjectRole, require_budget_read, require_role
from app.db.session import get_db
from app.models.budget import Budget, BudgetLineItem, BudgetProposal, Contribution
from app.schemas.budget import (
    BudgetExport,
    BudgetLineItemCreate,
    BudgetLineItemRead,
    BudgetLineItemUpdate,
    BudgetProposalCreate,
    BudgetProposalRead,
    BudgetProposalReview,
    BudgetRead,
    BudgetUpdate,
    ContributionCreate,
    ContributionRead,
    ContributionUpdate,
)
from app.services.audit_service import write_audit_log
from app.services.budget_service import money, shape_budget_response

router = APIRouter()
CONTRIBUTION_WRITE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR, ProjectRole.COMMITTEE_MEMBER}
PROPOSAL_CREATE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR}


def get_budget_record(db: Session, project_id: UUID) -> Budget:
    budget = db.query(Budget).filter(Budget.project_id == project_id).first()
    if budget:
        return budget
    budget = Budget(project_id=project_id, total=0, spent=0)
    db.add(budget)
    db.flush()
    return budget


def get_line_item_or_404(db: Session, project_id: UUID, item_id: UUID) -> BudgetLineItem:
    item = db.query(BudgetLineItem).filter(BudgetLineItem.project_id == project_id, BudgetLineItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget line item not found")
    return item


def get_contribution_or_404(db: Session, project_id: UUID, contribution_id: UUID) -> Contribution:
    contribution = db.query(Contribution).filter(Contribution.project_id == project_id, Contribution.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")
    return contribution


def get_proposal_or_404(db: Session, project_id: UUID, proposal_id: UUID) -> BudgetProposal:
    proposal = db.query(BudgetProposal).filter(BudgetProposal.project_id == project_id, BudgetProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget proposal not found")
    return proposal


@router.get("", response_model=BudgetRead)
def get_budget(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    visibility = membership_budget_visibility(membership)
    require_budget_read(visibility)
    budget = db.query(Budget).filter(Budget.project_id == project_id).first()
    contributions = db.query(Contribution).filter(Contribution.project_id == project_id).all()
    line_items = db.query(BudgetLineItem).filter(BudgetLineItem.project_id == project_id).all() if visibility == BudgetVisibilityMode.FULL_ACCESS else []
    return shape_budget_response(visibility, budget, contributions, line_items)


@router.patch("", response_model=BudgetRead)
def update_budget(project_id: UUID, payload: BudgetUpdate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    budget = get_budget_record(db, project_id)
    budget.total = payload.total
    budget.spent = payload.spent
    write_audit_log(db, "budget.updated", actor_user_id=current_user.id, project_id=project_id)
    db.commit()
    return shape_budget_response(BudgetVisibilityMode.FULL_ACCESS, budget, db.query(Contribution).filter(Contribution.project_id == project_id).all(), db.query(BudgetLineItem).filter(BudgetLineItem.project_id == project_id).all())


@router.get("/line-items", response_model=list[BudgetLineItemRead])
def list_line_items(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    if membership_budget_visibility(membership) != BudgetVisibilityMode.FULL_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Full budget access required")
    return db.query(BudgetLineItem).filter(BudgetLineItem.project_id == project_id).all()


@router.post("/line-items", response_model=BudgetLineItemRead)
def create_line_item(project_id: UUID, payload: BudgetLineItemCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    item = BudgetLineItem(project_id=project_id, **payload.model_dump())
    db.add(item)
    write_audit_log(db, "budget.line_item_created", actor_user_id=current_user.id, project_id=project_id)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/line-items/{item_id}", response_model=BudgetLineItemRead)
def update_line_item(project_id: UUID, item_id: UUID, payload: BudgetLineItemUpdate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    item = get_line_item_or_404(db, project_id, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    write_audit_log(db, "budget.line_item_updated", actor_user_id=current_user.id, project_id=project_id, metadata={"item_id": str(item_id)})
    db.commit()
    db.refresh(item)
    return item


@router.delete("/line-items/{item_id}")
def delete_line_item(project_id: UUID, item_id: UUID, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    item = get_line_item_or_404(db, project_id, item_id)
    db.delete(item)
    write_audit_log(db, "budget.line_item_deleted", actor_user_id=current_user.id, project_id=project_id, metadata={"item_id": str(item_id)})
    db.commit()
    return {"status": "deleted"}


@router.get("/contributions", response_model=list[ContributionRead])
def list_contributions(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_budget_read(membership_budget_visibility(membership))
    return db.query(Contribution).filter(Contribution.project_id == project_id).all()


@router.post("/contributions", response_model=ContributionRead)
def create_contribution(project_id: UUID, payload: ContributionCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), CONTRIBUTION_WRITE_ROLES)
    contribution = Contribution(project_id=project_id, **payload.model_dump())
    db.add(contribution)
    write_audit_log(db, "budget.contribution_created", actor_user_id=current_user.id, project_id=project_id)
    db.commit()
    db.refresh(contribution)
    return contribution


@router.patch("/contributions/{contribution_id}", response_model=ContributionRead)
def update_contribution(project_id: UUID, contribution_id: UUID, payload: ContributionUpdate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), CONTRIBUTION_WRITE_ROLES)
    contribution = get_contribution_or_404(db, project_id, contribution_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contribution, field, value)
    write_audit_log(db, "budget.contribution_updated", actor_user_id=current_user.id, project_id=project_id, metadata={"contribution_id": str(contribution_id)})
    db.commit()
    db.refresh(contribution)
    return contribution


@router.delete("/contributions/{contribution_id}")
def delete_contribution(project_id: UUID, contribution_id: UUID, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), CONTRIBUTION_WRITE_ROLES)
    contribution = get_contribution_or_404(db, project_id, contribution_id)
    db.delete(contribution)
    write_audit_log(db, "budget.contribution_deleted", actor_user_id=current_user.id, project_id=project_id, metadata={"contribution_id": str(contribution_id)})
    db.commit()
    return {"status": "deleted"}


@router.get("/proposals", response_model=list[BudgetProposalRead])
def list_proposals(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    return db.query(BudgetProposal).filter(BudgetProposal.project_id == project_id).all()


@router.post("/proposals", response_model=BudgetProposalRead)
def create_proposal(project_id: UUID, payload: BudgetProposalCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROPOSAL_CREATE_ROLES)
    proposal = BudgetProposal(project_id=project_id, proposed_by=current_user.id, **payload.model_dump())
    db.add(proposal)
    write_audit_log(db, "budget.proposal_created", actor_user_id=current_user.id, project_id=project_id)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.patch("/proposals/{proposal_id}/review", response_model=BudgetProposalRead)
def review_proposal(project_id: UUID, proposal_id: UUID, payload: BudgetProposalReview, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    proposal = get_proposal_or_404(db, project_id, proposal_id)
    proposal.status = payload.status
    proposal.reviewed_by = current_user.id
    proposal.reviewed_at = datetime.now(timezone.utc)
    write_audit_log(db, "budget.proposal_reviewed", actor_user_id=current_user.id, project_id=project_id, metadata={"proposal_id": str(proposal_id), "status": payload.status})
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get("/export", response_model=BudgetExport)
def export_budget(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), BUDGET_WRITE_ROLES)
    budget = get_budget_record(db, project_id)
    contributions = db.query(Contribution).filter(Contribution.project_id == project_id).all()
    line_items = db.query(BudgetLineItem).filter(BudgetLineItem.project_id == project_id).all()
    proposals = db.query(BudgetProposal).filter(BudgetProposal.project_id == project_id).all()
    paid_total = sum(money(item.paid) for item in contributions)
    pledged_total = sum(money(item.pledged) for item in contributions)
    total = money(budget.total)
    spent = money(budget.spent)
    return BudgetExport(
        project_id=project_id,
        total=total,
        spent=spent,
        remaining=max(total - spent, 0),
        contribution_progress=paid_total,
        pledged_total=pledged_total,
        line_items=line_items,
        contributions=contributions,
        proposals=proposals,
    )
