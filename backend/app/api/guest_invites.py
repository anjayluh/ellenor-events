from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_role
from app.core.permissions import GUEST_INVITES_MANAGE_PERMISSION, PROJECT_ADMIN_ROLES, require_permission
from app.db.session import get_db
from app.models.guest_invite import GuestInvite
from app.schemas.guest_invite import GuestInviteCreate, GuestInviteRead, GuestInviteResponse, GuestInviteSummary, GuestInviteUpdate
from app.services.audit_service import write_audit_log
from app.services.invite_service import build_invite_link, generate_invite_token
from app.services.notification_service import create_notification

router = APIRouter()
public_router = APIRouter()


def get_guest_invite_or_404(db: Session, project_id: UUID, invite_id: UUID) -> GuestInvite:
    invite = db.query(GuestInvite).filter(GuestInvite.project_id == project_id, GuestInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest invite not found")
    return invite


def find_guest_invite_by_token(db: Session, token: str) -> GuestInvite:
    invite = db.query(GuestInvite).filter(GuestInvite.token == token).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest invite not found")
    return invite


@router.get("", response_model=list[GuestInviteRead])
def list_guest_invites(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, GUEST_INVITES_MANAGE_PERMISSION)
    return db.query(GuestInvite).filter(GuestInvite.project_id == project_id).order_by(GuestInvite.created_at.desc()).all()


@router.post("", response_model=GuestInviteRead)
def create_guest_invite(
    project_id: UUID,
    payload: GuestInviteCreate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, GUEST_INVITES_MANAGE_PERMISSION)
    invite = GuestInvite(project_id=project_id, token=generate_invite_token(), **payload.model_dump())
    db.add(invite)
    write_audit_log(db, "guest_invite.created", actor_user_id=current_user.id, project_id=project_id)
    db.commit()
    db.refresh(invite)
    return invite


@router.patch("/{invite_id}", response_model=GuestInviteRead)
def update_guest_invite(
    project_id: UUID,
    invite_id: UUID,
    payload: GuestInviteUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, GUEST_INVITES_MANAGE_PERMISSION)
    invite = get_guest_invite_or_404(db, project_id, invite_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(invite, field, value)
    if "attendance_status" in updates:
        invite.responded_at = datetime.now(timezone.utc)
    write_audit_log(db, "guest_invite.updated", actor_user_id=current_user.id, project_id=project_id, metadata={"invite_id": str(invite_id)})
    db.commit()
    db.refresh(invite)
    return invite


@router.post("/{invite_id}/send", response_model=GuestInviteRead)
def send_guest_invite(
    project_id: UUID,
    invite_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, GUEST_INVITES_MANAGE_PERMISSION)
    invite = get_guest_invite_or_404(db, project_id, invite_id)
    if not invite.email and not invite.phone:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest invite has no contact")
    invite.status = "sent"
    invite.sent_count = (invite.sent_count or 0) + 1
    invite.last_sent_at = datetime.now(timezone.utc)
    link = build_invite_link(invite.token).replace("/invite/", "/guest-invite/")
    create_notification(
        db,
        project_id=project_id,
        channel="email" if invite.email else "whatsapp",
        recipient_contact=invite.email or invite.phone,
        subject="Your Ellenor Events invitation",
        body=f"You are invited to this event. RSVP here: {link}",
        actor_user_id=current_user.id,
        metadata={"guest_invite_id": str(invite.id), "invitation_card_url": invite.invitation_card_url},
    )
    write_audit_log(db, "guest_invite.sent", actor_user_id=current_user.id, project_id=project_id, metadata={"invite_id": str(invite_id)})
    db.commit()
    db.refresh(invite)
    return invite


@router.get("/summary", response_model=GuestInviteSummary)
def guest_invite_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, GUEST_INVITES_MANAGE_PERMISSION)
    rows = db.query(GuestInvite.attendance_status, func.count(GuestInvite.id)).filter(GuestInvite.project_id == project_id).group_by(GuestInvite.attendance_status).all()
    sent = db.query(GuestInvite).filter(GuestInvite.project_id == project_id, GuestInvite.sent_count > 0).count()
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    return GuestInviteSummary(
        project_id=project_id,
        total=total,
        sent=sent,
        accepted=counts.get("accepted", 0) + counts.get("confirmed", 0),
        declined=counts.get("declined", 0),
        pending=counts.get("pending", 0),
        rejected=counts.get("rejected", 0),
    )


@public_router.get("/{token}", response_model=GuestInviteRead)
def preview_guest_invite(token: str, db: Session = Depends(get_db)):
    return find_guest_invite_by_token(db, token)


@public_router.post("/{token}/respond", response_model=GuestInviteRead)
def respond_guest_invite(token: str, payload: GuestInviteResponse, db: Session = Depends(get_db)):
    invite = find_guest_invite_by_token(db, token)
    if payload.attendance_status not in {"accepted", "declined", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported attendance status")
    invite.attendance_status = payload.attendance_status
    invite.status = "responded"
    invite.responded_at = datetime.now(timezone.utc)
    write_audit_log(db, "guest_invite.responded", project_id=invite.project_id, metadata={"invite_id": str(invite.id), "attendance_status": payload.attendance_status})
    db.commit()
    db.refresh(invite)
    return invite
