from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.core.permissions import PROJECT_ADMIN_ROLES, ProjectRole, require_role
from app.db.session import get_db
from app.models.invite import Invite
from app.models.project_member import ProjectMember
from app.schemas.invite import InviteAccept, InviteAcceptRead, InviteAnalytics, InviteCreate, InviteRead
from app.services.audit_service import write_audit_log
from app.services.email_service import build_email_invite_payload
from app.services.invite_service import (
    build_invite_link,
    create_membership_from_invite,
    default_invite_expiry,
    ensure_invite_can_be_accepted,
    find_invite_by_token,
    generate_invite_token,
    get_or_create_invited_user,
    mark_invite_opened,
    mark_invite_sent,
    normalize_invite_contact,
)
from app.services.whatsapp_service import build_whatsapp_invite_url

router = APIRouter()


def require_invite_permission(project_id: UUID, current_user: CurrentUser, db: Session) -> ProjectMember:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project")
    require_role(ProjectRole(membership.role), PROJECT_ADMIN_ROLES)
    return membership


def serialize_invite(invite: Invite) -> InviteRead:
    invite_link = build_invite_link(invite.token)
    whatsapp_url = build_whatsapp_invite_url(invite.contact, invite_link) if invite.delivery_channel == "whatsapp" else None
    return InviteRead(
        id=invite.id,
        project_id=invite.project_id,
        contact=invite.contact,
        role_assigned=ProjectRole(invite.role_assigned),
        status=invite.status,
        invite_link=invite_link,
        whatsapp_url=whatsapp_url,
        delivery_channel=invite.delivery_channel,
        expires_at=invite.expires_at,
        sent_count=invite.sent_count or 0,
        opened_count=invite.opened_count or 0,
    )


@router.post("", response_model=InviteRead)
def create_invite(payload: InviteCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_invite_permission(payload.project_id, current_user, db)
    token = generate_invite_token()
    invite = Invite(
        project_id=payload.project_id,
        contact=normalize_invite_contact(payload.contact),
        role_assigned=payload.role_assigned.value,
        token=token,
        delivery_channel=payload.delivery_channel,
        sent_count=1,
        last_sent_at=datetime.now(timezone.utc),
        expires_at=default_invite_expiry(),
    )
    db.add(invite)
    invite_link = build_invite_link(token)
    delivery_metadata = (
        {"whatsapp_url": build_whatsapp_invite_url(invite.contact, invite_link)}
        if payload.delivery_channel == "whatsapp"
        else {"email": build_email_invite_payload(invite.contact, invite_link)}
    )
    write_audit_log(
        db,
        "invite.created",
        actor_user_id=current_user.id,
        project_id=payload.project_id,
        metadata={"contact": invite.contact, "role": payload.role_assigned.value, "delivery": delivery_metadata},
    )
    db.commit()
    db.refresh(invite)
    return serialize_invite(invite)


@router.get("/{token}", response_model=InviteRead)
def get_invite(token: str, db: Session = Depends(get_db)):
    invite = find_invite_by_token(db, token)
    if invite.status == "pending" and invite.expires_at < datetime.now(timezone.utc):
        invite.status = "expired"
    mark_invite_opened(invite)
    write_audit_log(db, "invite.opened", project_id=invite.project_id, metadata={"token_prefix": token[:8]})
    db.commit()
    db.refresh(invite)
    return serialize_invite(invite)


@router.post("/accept", response_model=InviteAcceptRead)
def accept_invite(payload: InviteAccept, db: Session = Depends(get_db)):
    invite = find_invite_by_token(db, payload.token)
    write_audit_log(db, "invite.accept_attempted", project_id=invite.project_id, metadata={"token_prefix": payload.token[:8]})
    ensure_invite_can_be_accepted(invite)
    user = get_or_create_invited_user(db, payload)
    membership = create_membership_from_invite(db, invite, user.id)
    invite.status = "accepted"
    invite.accepted_user_id = user.id
    invite.accepted_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        "invite.accepted",
        actor_user_id=user.id,
        project_id=invite.project_id,
        metadata={"invite_id": str(invite.id), "role": membership.role},
    )
    db.commit()
    return InviteAcceptRead(status="accepted", project_id=invite.project_id, user_id=user.id, role=ProjectRole(membership.role))


@router.post("/{invite_id}/resend", response_model=InviteRead)
def resend_invite(invite_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    require_invite_permission(invite.project_id, current_user, db)
    if invite.status == "accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Accepted invites cannot be resent")
    invite.status = "pending"
    invite.expires_at = default_invite_expiry()
    mark_invite_sent(invite)
    write_audit_log(db, "invite.resent", actor_user_id=current_user.id, project_id=invite.project_id, metadata={"invite_id": str(invite.id)})
    db.commit()
    db.refresh(invite)
    return serialize_invite(invite)


@router.post("/{invite_id}/cancel", response_model=InviteRead)
def cancel_invite(invite_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    require_invite_permission(invite.project_id, current_user, db)
    if invite.status == "accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Accepted invites cannot be cancelled")
    invite.status = "cancelled"
    invite.cancelled_at = datetime.now(timezone.utc)
    write_audit_log(db, "invite.cancelled", actor_user_id=current_user.id, project_id=invite.project_id, metadata={"invite_id": str(invite.id)})
    db.commit()
    db.refresh(invite)
    return serialize_invite(invite)


@router.get("/projects/{project_id}/analytics", response_model=InviteAnalytics)
def invite_analytics(project_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_invite_permission(project_id, current_user, db)
    rows = db.query(Invite.status, func.count(Invite.id)).filter(Invite.project_id == project_id).group_by(Invite.status).all()
    status_counts = {status: count for status, count in rows}
    totals = db.query(func.coalesce(func.sum(Invite.sent_count), 0), func.coalesce(func.sum(Invite.opened_count), 0)).filter(Invite.project_id == project_id).one()
    return InviteAnalytics(
        project_id=project_id,
        pending=status_counts.get("pending", 0),
        accepted=status_counts.get("accepted", 0),
        expired=status_counts.get("expired", 0),
        cancelled=status_counts.get("cancelled", 0),
        total_sent=int(totals[0] or 0),
        total_opened=int(totals[1] or 0),
    )
