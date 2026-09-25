from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_role
from app.core.permissions import GUEST_INVITES_MANAGE_PERMISSION, PROJECT_ADMIN_ROLES, require_permission
from app.db.session import get_db
from app.models.project_guest import ProjectGuestInvitation
from app.schemas.project_guest import (
    GuestInviteSend,
    GuestInviteSendRead,
    PublicGuestInviteRead,
    PublicGuestRsvpRead,
    PublicGuestRsvpUpdate,
    ProjectGuestCreate,
    ProjectGuestInvitationRead,
    ProjectGuestRead,
    ProjectGuestSummary,
    ProjectGuestUpdate,
)
from app.services.audit_service import write_audit_log
from app.services.invite_service import build_invite_link
from app.services.notification_service import PreparedNotification, create_notification
from app.services.project_guest_service import (
    RSVP_STATUSES,
    consume_invitation_email,
    create_guest_invitation_record,
    create_project_guest,
    get_project_guest_or_404,
    guest_summary_counts,
    guest_usage,
    invitation_email_usage,
    latest_invitation,
    list_project_guests,
    project_or_404,
    public_invitation_by_token,
    update_project_guest,
)

router = APIRouter()
public_router = APIRouter()


def require_guest_manager(membership):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, GUEST_INVITES_MANAGE_PERMISSION)


def serialize_guest(guest) -> ProjectGuestRead:
    return ProjectGuestRead.model_validate(guest)


def serialize_invitation(invitation: ProjectGuestInvitation) -> ProjectGuestInvitationRead:
    return ProjectGuestInvitationRead.model_validate(invitation)


@router.get("", response_model=list[ProjectGuestRead])
def list_guests(
    project_id: UUID,
    search: str | None = None,
    category: str | None = None,
    group_name: str | None = None,
    invitation_status: str | None = None,
    rsvp_status: str | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_guest_manager(membership)
    return [
        serialize_guest(guest)
        for guest in list_project_guests(
            db,
            project_id,
            search=search,
            category=category,
            group_name=group_name,
            invitation_status=invitation_status,
            rsvp_status=rsvp_status,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/summary", response_model=ProjectGuestSummary)
def guest_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_guest_manager(membership)
    project = project_or_404(db, project_id)
    counts = guest_summary_counts(db, project_id)
    return ProjectGuestSummary(
        project_id=project_id,
        **counts,
        guest_usage=guest_usage(db, project),
        invitation_email_usage=invitation_email_usage(db, project),
    )


@router.post("", response_model=ProjectGuestRead)
def create_guest(
    project_id: UUID,
    payload: ProjectGuestCreate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_guest_manager(membership)
    project = project_or_404(db, project_id, lock=True)
    guest = create_project_guest(db, project, payload)
    write_audit_log(db, "project_guest.created", actor_user_id=current_user.id, project_id=project_id, metadata={"guest_id": str(guest.id)})
    db.commit()
    db.refresh(guest)
    return serialize_guest(guest)


@router.patch("/{guest_id}", response_model=ProjectGuestRead)
def update_guest(
    project_id: UUID,
    guest_id: UUID,
    payload: ProjectGuestUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_guest_manager(membership)
    guest = get_project_guest_or_404(db, project_id, guest_id)
    update_project_guest(db, guest, payload)
    write_audit_log(db, "project_guest.updated", actor_user_id=current_user.id, project_id=project_id, metadata={"guest_id": str(guest.id)})
    db.commit()
    db.refresh(guest)
    return serialize_guest(guest)


@router.delete("/{guest_id}")
def delete_guest(
    project_id: UUID,
    guest_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_guest_manager(membership)
    guest = get_project_guest_or_404(db, project_id, guest_id)
    db.delete(guest)
    write_audit_log(db, "project_guest.deleted", actor_user_id=current_user.id, project_id=project_id, metadata={"guest_id": str(guest_id)})
    db.commit()
    return {"status": "deleted"}


@router.post("/{guest_id}/invite", response_model=GuestInviteSendRead)
def send_guest_invitation(
    project_id: UUID,
    guest_id: UUID,
    payload: GuestInviteSend,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_guest_manager(membership)
    project = project_or_404(db, project_id)
    guest = get_project_guest_or_404(db, project_id, guest_id, lock=True)
    existing = latest_invitation(db, guest.id)
    if existing and guest.invitation_status in {"SENT", "OPENED", "RESPONDED"} and not payload.resend:
        return GuestInviteSendRead(
            guest=serialize_guest(guest),
            invitation=serialize_invitation(existing),
            already_sent=True,
            guest_usage=guest_usage(db, project),
            invitation_email_usage=invitation_email_usage(db, project),
        )

    if not guest.email:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest needs an email address before an email invitation can be sent")
    consume_invitation_email(db, project.customer_account_id)
    invitation = create_guest_invitation_record(db, guest)
    link = build_invite_link(invitation.token).replace("/invite/", "/guest-rsvp/")
    notification = create_notification(
        db,
        project_id=project_id,
        channel="email",
        recipient_contact=guest.email,
        subject=f"You're invited to {project.title}",
        body=f"Hello {guest.display_name}, you are invited to {project.title}. RSVP here: {link}",
        actor_user_id=current_user.id,
        metadata={"project_guest_id": str(guest.id), "project_guest_invitation_id": str(invitation.id), "invitation_card_url": guest.invitation_card_url},
    )
    invitation.notification_id = notification.id if isinstance(notification, PreparedNotification) else notification.id
    invitation.provider_reference = str(notification.id)
    guest.invitation_status = "SENT"
    guest.updated_at = datetime.now(timezone.utc)
    write_audit_log(db, "project_guest.invitation_sent", actor_user_id=current_user.id, project_id=project_id, metadata={"guest_id": str(guest.id), "invitation_id": str(invitation.id)})
    db.commit()
    db.refresh(guest)
    db.refresh(invitation)
    return GuestInviteSendRead(
        guest=serialize_guest(guest),
        invitation=serialize_invitation(invitation),
        already_sent=False,
        guest_usage=guest_usage(db, project),
        invitation_email_usage=invitation_email_usage(db, project),
    )


@public_router.get("/{token}", response_model=PublicGuestInviteRead)
def preview_guest_rsvp(token: str, db: Session = Depends(get_db)):
    invitation = public_invitation_by_token(db, token)
    guest = get_project_guest_or_404(db, invitation.project_id, invitation.project_guest_id)
    project = project_or_404(db, invitation.project_id)
    if invitation.status == "SENT":
        invitation.status = "OPENED"
        invitation.opened_at = invitation.opened_at or datetime.now(timezone.utc)
        guest.invitation_status = "OPENED"
        guest.updated_at = datetime.now(timezone.utc)
        db.commit()
    return PublicGuestInviteRead(
        token=token,
        recipient_name=guest.display_name,
        event_title=project.title,
        event_date=project.event_date,
        invitation_card_url=guest.invitation_card_url,
        invitation_status=guest.invitation_status,
        rsvp_status=guest.rsvp_status,
        rsvp_attendee_count=guest.rsvp_attendee_count,
        rsvp_note=guest.rsvp_note,
    )


@public_router.post("/{token}/respond", response_model=PublicGuestRsvpRead)
def respond_guest_rsvp(token: str, payload: PublicGuestRsvpUpdate, db: Session = Depends(get_db)):
    if payload.rsvp_status not in RSVP_STATUSES - {"PENDING"}:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported RSVP status")
    invitation = public_invitation_by_token(db, token)
    guest = get_project_guest_or_404(db, invitation.project_id, invitation.project_guest_id, lock=True)
    project = project_or_404(db, invitation.project_id)
    now = datetime.now(timezone.utc)
    attendee_count = payload.rsvp_attendee_count
    if payload.rsvp_status == "ATTENDING":
        attendee_count = 1 if attendee_count is None else attendee_count
        if attendee_count < 1:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Attending guests must include at least one attendee")
    else:
        attendee_count = 0 if attendee_count is None else attendee_count
    guest.rsvp_status = payload.rsvp_status
    guest.rsvp_attendee_count = attendee_count
    guest.rsvp_note = (payload.rsvp_note or "").strip() or None
    guest.rsvp_responded_at = now
    guest.invitation_status = "RESPONDED"
    guest.updated_at = now
    invitation.status = "RESPONDED"
    invitation.responded_at = now
    write_audit_log(db, "project_guest.rsvp_recorded", project_id=project.id, metadata={"guest_id": str(guest.id), "invitation_id": str(invitation.id), "rsvp_status": payload.rsvp_status})
    db.commit()
    db.refresh(guest)
    db.refresh(invitation)
    return PublicGuestRsvpRead(
        token=token,
        recipient_name=guest.display_name,
        event_title=project.title,
        event_date=project.event_date,
        invitation_card_url=guest.invitation_card_url,
        invitation_status=guest.invitation_status,
        rsvp_status=guest.rsvp_status,
        rsvp_attendee_count=guest.rsvp_attendee_count,
        rsvp_note=guest.rsvp_note,
        responded_at=guest.rsvp_responded_at,
    )
