from uuid import UUID

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import BudgetVisibilityMode, ProjectRole
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user: User):
        self.id = user.id
        self.name = user.name
        self.phone = user.phone
        self.email = user.email


def apply_supabase_rls_context(db: Session, user_id: UUID) -> None:
    if not settings.uses_remote_supabase_auth:
        return
    db.execute(text("set role authenticated"))
    db.execute(text("select set_config('request.jwt.claim.sub', :user_id, false)"), {"user_id": str(user_id)})
    db.execute(text("select set_config('request.jwt.claim.role', 'authenticated', false)"))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> CurrentUser:
    user_id: UUID | None = None

    if credentials:
        try:
            user_id = decode_access_token(credentials.credentials)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc
    elif settings.allow_dev_auth_headers and x_user_id:
        try:
            user_id = UUID(x_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid development user id") from exc

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token is required")

    apply_supabase_rls_context(db, user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated user does not exist")
    return CurrentUser(user)


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
