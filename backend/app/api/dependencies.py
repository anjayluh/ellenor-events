from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import BudgetVisibilityMode, ProjectRole
from app.db.session import get_db
from app.models.project_member import ProjectMember


class CurrentUser:
    def __init__(self, user_id: UUID):
        self.id = user_id


def get_current_user(x_user_id: str = Header(..., alias="X-User-Id")) -> CurrentUser:
    # MVP adapter: replace this with Supabase/Firebase JWT validation before production.
    try:
        return CurrentUser(UUID(x_user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id") from exc


def get_project_membership(
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectMember:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project")
    return membership


def membership_role(membership: ProjectMember) -> ProjectRole:
    return ProjectRole(membership.role)


def membership_budget_visibility(membership: ProjectMember) -> BudgetVisibilityMode:
    return BudgetVisibilityMode(membership.budget_visibility_mode)
