from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import BudgetVisibilityMode, ProjectRole
from app.core.security import decode_access_token, decode_supabase_access_token
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.models.user import User
from app.services.auth_service import normalize_email, supabase_auth_headers, supabase_auth_url

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
    if db.get_bind().dialect.name != "postgresql":
        return
    db.execute(text("set local role authenticated"))
    db.execute(
        text(
            """
            select
                set_config('request.jwt.claim.sub', :user_id, true),
                set_config('request.jwt.claim.role', 'authenticated', true)
            """
        ),
        {"user_id": str(user_id)},
    )
    db.info["supabase_rls_applied"] = True
    db.info["supabase_rls_user_id"] = str(user_id)


def restore_supabase_rls_context(db: Session) -> None:
    user_id = db.info.get("supabase_rls_user_id")
    if not user_id:
        return
    db.execute(text("set local role authenticated"))
    db.execute(
        text(
            """
            select
                set_config('request.jwt.claim.sub', :user_id, true),
                set_config('request.jwt.claim.role', 'authenticated', true)
            """
        ),
        {"user_id": user_id},
    )


@contextmanager
def trusted_backend_write(db: Session) -> Generator[None, None, None]:
    if not settings.uses_remote_supabase_auth:
        yield
        return
    if db.get_bind().dialect.name != "postgresql":
        yield
        return
    if not db.info.get("supabase_rls_applied"):
        yield
        return
    db.execute(text("reset role"))
    try:
        yield
    finally:
        restore_supabase_rls_context(db)


def resolve_supabase_user_from_token(token: str) -> tuple[UUID, dict]:
    try:
        response = httpx.get(
            supabase_auth_url("user"),
            headers={**supabase_auth_headers(), "Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Supabase Auth is unavailable") from exc

    auth_user = response.json()
    try:
        return UUID(auth_user["id"]), auth_user
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc


def sync_supabase_user_profile(db: Session, auth_user: dict) -> User:
    user_id = UUID(auth_user["id"])
    metadata = auth_user.get("user_metadata") or {}
    email = normalize_email(auth_user["email"]) if auth_user.get("email") else None
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if email and not user.email:
            user.email = email
        if auth_user.get("phone") and not user.phone:
            user.phone = auth_user.get("phone")
        if (metadata.get("name") or metadata.get("full_name")) and not user.name:
            user.name = metadata.get("name") or metadata.get("full_name")
        return user

    user = User(id=user_id, email=email, phone=auth_user.get("phone"), name=metadata.get("name") or metadata.get("full_name"))
    db.add(user)
    db.flush()
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> CurrentUser:
    user_id: UUID | None = None
    supabase_auth_user: dict | None = None

    if credentials:
        try:
            user_id = decode_access_token(credentials.credentials)
        except ValueError as exc:
            if not settings.uses_remote_supabase_auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc
            try:
                user_id, supabase_auth_user = decode_supabase_access_token(credentials.credentials)
            except ValueError:
                user_id, supabase_auth_user = resolve_supabase_user_from_token(credentials.credentials)
    elif settings.allow_dev_auth_headers and x_user_id:
        try:
            user_id = UUID(x_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid development user id") from exc

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token is required")

    apply_supabase_rls_context(db, user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user and supabase_auth_user:
        user = sync_supabase_user_profile(db, supabase_auth_user)
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



def membership_permissions(membership: ProjectMember) -> set[str]:
    from app.core.permissions import effective_permissions

    return effective_permissions(ProjectRole(membership.role), getattr(membership, "permissions_json", None))
