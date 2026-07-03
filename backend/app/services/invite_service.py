from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.invite import Invite
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.invite import InviteAccept


def build_invite_link(token: str) -> str:
    return f"{settings.frontend_url}/invite/{token}"


def generate_invite_token() -> str:
    return token_urlsafe(32)


def default_invite_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


def normalize_invite_contact(contact: str) -> str:
    cleaned = contact.strip()
    if cleaned.startswith("+"):
        return cleaned.replace(" ", "")
    return cleaned.lower()


def find_invite_by_token(db: Session, token: str) -> Invite:
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    return invite


def ensure_invite_can_be_accepted(invite: Invite) -> None:
    now = datetime.now(timezone.utc)
    if invite.status == "accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite has already been accepted")
    if invite.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite has been cancelled")
    if invite.expires_at < now:
        invite.status = "expired"
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite has expired")
    if invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Invite cannot be accepted from status {invite.status}")


def get_or_create_invited_user(db: Session, payload: InviteAccept) -> User:
    phone = normalize_invite_contact(payload.phone) if payload.phone else None
    email = normalize_invite_contact(str(payload.email)) if payload.email else None
    query = db.query(User).filter(User.phone == phone) if phone else db.query(User).filter(User.email == email)
    user = query.first()
    if user:
        if payload.name and not user.name:
            user.name = payload.name
        if phone and not user.phone:
            user.phone = phone
        if email and not user.email:
            user.email = email
        return user

    user = User(name=payload.name, phone=phone, email=email)
    db.add(user)
    db.flush()
    return user


def create_membership_from_invite(db: Session, invite: Invite, user_id: UUID) -> ProjectMember:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == invite.project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if membership:
        membership.role = invite.role_assigned
        return membership

    membership = ProjectMember(
        project_id=invite.project_id,
        user_id=user_id,
        role=invite.role_assigned,
        permissions_level="invited",
        budget_visibility_mode="NO_ACCESS",
    )
    db.add(membership)
    db.flush()
    return membership


def mark_invite_opened(invite: Invite) -> None:
    invite.opened_count = (invite.opened_count or 0) + 1
    invite.opened_at = datetime.now(timezone.utc)


def mark_invite_sent(invite: Invite) -> None:
    invite.sent_count = (invite.sent_count or 0) + 1
    invite.last_sent_at = datetime.now(timezone.utc)
    if invite.status == "expired" and invite.expires_at > datetime.now(timezone.utc):
        invite.status = "pending"
