from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.customer_account import AccountEntitlement
from app.models.project import Project
from app.models.project_guest import ProjectGuest, ProjectGuestInvitation
from app.schemas.project_guest import GuestUsageRead, ProjectGuestCreate, ProjectGuestUpdate
from app.services.entitlement_service import active_entitlements, entitlement_is_active, entitlement_priority
from app.services.invite_service import generate_invite_token

GUESTS_PER_EVENT_ENTITLEMENT_KEY = "guests_per_event"
INVITATION_EMAILS_ENTITLEMENT_KEY = "invitation_emails_per_month"
INVITATION_STATUSES = {"NOT_SENT", "SENT", "OPENED", "RESPONDED"}
RSVP_STATUSES = {"PENDING", "ATTENDING", "NOT_ATTENDING"}


def display_name(first_name: str, last_name: str | None = None) -> str:
    return " ".join(part for part in [first_name.strip(), (last_name or "").strip()] if part).strip()


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def project_or_404(db: Session, project_id: UUID, *, lock: bool = False) -> Project:
    query = db.query(Project).filter(Project.id == project_id)
    if lock:
        query = query.with_for_update()
    project = query.first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def active_entitlements_for_update(db: Session, customer_account_id: UUID, key: str) -> list[AccountEntitlement]:
    entitlements = [
        entitlement
        for entitlement in db.query(AccountEntitlement)
        .filter(AccountEntitlement.customer_account_id == customer_account_id, AccountEntitlement.key == key)
        .with_for_update()
        .all()
        if entitlement_is_active(entitlement)
    ]
    return sorted(entitlements, key=entitlement_priority)


def select_available_entitlement(db: Session, customer_account_id: UUID, key: str, *, amount: int = 1) -> AccountEntitlement:
    for entitlement in active_entitlements_for_update(db, customer_account_id, key):
        if entitlement.quantity is None or entitlement.used_quantity + amount <= entitlement.quantity:
            return entitlement
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "INVITATION_EMAIL_ENTITLEMENT_REQUIRED" if key == INVITATION_EMAILS_ENTITLEMENT_KEY else "GUEST_ENTITLEMENT_REQUIRED",
            "message": "Your Ellenor Events package limit has been reached for this action.",
        },
    )


def resolve_event_guest_entitlement(db: Session, customer_account_id: UUID) -> AccountEntitlement:
    entitlements = active_entitlements(db, customer_account_id, GUESTS_PER_EVENT_ENTITLEMENT_KEY)
    if not entitlements:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "GUEST_ENTITLEMENT_REQUIRED", "message": "Choose an active package before adding guests."},
        )
    return entitlements[0]


def guest_count(db: Session, project_id: UUID) -> int:
    return db.query(ProjectGuest).filter(ProjectGuest.project_id == project_id).count()


def usage_from_count(key: str, label: str, used: int, limit: int | None) -> GuestUsageRead:
    return GuestUsageRead(key=key, label=label, used=used, limit=limit, remaining=None if limit is None else max(limit - used, 0))


def guest_usage(db: Session, project: Project) -> GuestUsageRead:
    entitlement = resolve_event_guest_entitlement(db, project.customer_account_id)
    return usage_from_count(GUESTS_PER_EVENT_ENTITLEMENT_KEY, "Guests", guest_count(db, project.id), entitlement.quantity)


def invitation_email_usage(db: Session, project: Project) -> GuestUsageRead:
    entitlements = active_entitlements(db, project.customer_account_id, INVITATION_EMAILS_ENTITLEMENT_KEY)
    if not entitlements:
        return usage_from_count(INVITATION_EMAILS_ENTITLEMENT_KEY, "Invitation emails", 0, 0)
    entitlement = entitlements[0]
    return usage_from_count(INVITATION_EMAILS_ENTITLEMENT_KEY, "Invitation emails", entitlement.used_quantity or 0, entitlement.quantity)


def assert_guest_capacity(db: Session, project: Project) -> None:
    project_or_404(db, project.id, lock=True)
    entitlement = resolve_event_guest_entitlement(db, project.customer_account_id)
    current_count = guest_count(db, project.id)
    if entitlement.quantity is not None and current_count + 1 > entitlement.quantity:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "GUEST_ENTITLEMENT_REQUIRED", "message": "This event has reached its guest limit for the current package."},
        )


def list_project_guests(
    db: Session,
    project_id: UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    group_name: str | None = None,
    invitation_status: str | None = None,
    rsvp_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ProjectGuest]:
    query = db.query(ProjectGuest).filter(ProjectGuest.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(ProjectGuest.display_name.ilike(pattern), ProjectGuest.email.ilike(pattern), ProjectGuest.phone.ilike(pattern)))
    if category:
        query = query.filter(ProjectGuest.category == category)
    if group_name:
        query = query.filter(ProjectGuest.group_name == group_name)
    if invitation_status:
        query = query.filter(ProjectGuest.invitation_status == invitation_status)
    if rsvp_status:
        query = query.filter(ProjectGuest.rsvp_status == rsvp_status)
    return query.order_by(ProjectGuest.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 250)).all()


def create_project_guest(db: Session, project: Project, payload: ProjectGuestCreate) -> ProjectGuest:
    assert_guest_capacity(db, project)
    first_name = payload.first_name.strip()
    last_name = clean_optional(payload.last_name)
    guest = ProjectGuest(
        project_id=project.id,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name(first_name, last_name),
        email=str(payload.email).lower() if payload.email else None,
        phone=clean_optional(payload.phone),
        category=clean_optional(payload.category),
        group_name=clean_optional(payload.group_name),
        notes=clean_optional(payload.notes),
        invitation_card_url=clean_optional(payload.invitation_card_url),
    )
    db.add(guest)
    db.flush()
    return guest


def get_project_guest_or_404(db: Session, project_id: UUID, guest_id: UUID, *, lock: bool = False) -> ProjectGuest:
    query = db.query(ProjectGuest).filter(ProjectGuest.project_id == project_id, ProjectGuest.id == guest_id)
    if lock:
        query = query.with_for_update()
    guest = query.first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return guest


def update_project_guest(db: Session, guest: ProjectGuest, payload: ProjectGuestUpdate) -> ProjectGuest:
    updates = payload.model_dump(exclude_unset=True)
    if "invitation_status" in updates and updates["invitation_status"] not in INVITATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported invitation status")
    if "rsvp_status" in updates and updates["rsvp_status"] not in RSVP_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported RSVP status")
    for field, value in updates.items():
        if field == "email" and value:
            value = str(value).lower()
        if field in {"last_name", "phone", "category", "group_name", "notes", "invitation_card_url", "rsvp_note"}:
            value = clean_optional(value)
        setattr(guest, field, value)
    if "first_name" in updates or "last_name" in updates:
        guest.display_name = display_name(guest.first_name, guest.last_name)
    if "rsvp_status" in updates:
        if updates["rsvp_status"] != "PENDING":
            guest.rsvp_responded_at = datetime.now(timezone.utc)
        else:
            guest.rsvp_responded_at = None
            guest.rsvp_attendee_count = 1
            guest.rsvp_note = None
    guest.updated_at = datetime.now(timezone.utc)
    db.flush()
    return guest


def latest_invitation(db: Session, guest_id: UUID) -> ProjectGuestInvitation | None:
    return (
        db.query(ProjectGuestInvitation)
        .filter(ProjectGuestInvitation.project_guest_id == guest_id)
        .order_by(ProjectGuestInvitation.created_at.desc())
        .first()
    )


def consume_invitation_email(db: Session, customer_account_id: UUID) -> AccountEntitlement:
    entitlement = select_available_entitlement(db, customer_account_id, INVITATION_EMAILS_ENTITLEMENT_KEY)
    entitlement.used_quantity = (entitlement.used_quantity or 0) + 1
    entitlement.updated_at = datetime.now(timezone.utc)
    db.flush()
    return entitlement


def create_guest_invitation_record(db: Session, guest: ProjectGuest) -> ProjectGuestInvitation:
    if not guest.email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest needs an email address before an email invitation can be sent")
    invitation = ProjectGuestInvitation(
        project_guest_id=guest.id,
        project_id=guest.project_id,
        recipient_email=guest.email,
        recipient_name=guest.display_name,
        token=generate_invite_token(),
        status="SENT",
        sent_at=datetime.now(timezone.utc),
    )
    db.add(invitation)
    db.flush()
    return invitation


def public_invitation_by_token(db: Session, token: str) -> ProjectGuestInvitation:
    invitation = db.query(ProjectGuestInvitation).filter(ProjectGuestInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    return invitation


def guest_summary_counts(db: Session, project_id: UUID) -> dict[str, int]:
    total = db.query(ProjectGuest).filter(ProjectGuest.project_id == project_id).count()
    rsvp_rows = db.query(ProjectGuest.rsvp_status, func.count(ProjectGuest.id)).filter(ProjectGuest.project_id == project_id).group_by(ProjectGuest.rsvp_status).all()
    rsvp_counts = {status: count for status, count in rsvp_rows}
    invitation_sent = (
        db.query(func.count(func.distinct(ProjectGuestInvitation.project_guest_id)))
        .filter(ProjectGuestInvitation.project_id == project_id, ProjectGuestInvitation.status.in_(["SENT", "OPENED", "RESPONDED"]))
        .scalar()
        or 0
    )
    invitations_opened = (
        db.query(func.count(func.distinct(ProjectGuestInvitation.project_guest_id)))
        .filter(ProjectGuestInvitation.project_id == project_id, ProjectGuestInvitation.opened_at.isnot(None))
        .scalar()
        or 0
    )
    rsvp_responses = rsvp_counts.get("ATTENDING", 0) + rsvp_counts.get("NOT_ATTENDING", 0)
    return {
        "total": total,
        "invitation_sent": invitation_sent,
        "opened": invitations_opened,
        "responded": rsvp_responses,
        "invitations_opened": invitations_opened,
        "rsvp_responses": rsvp_responses,
        "attending": rsvp_counts.get("ATTENDING", 0),
        "not_attending": rsvp_counts.get("NOT_ATTENDING", 0),
        "pending_rsvp": rsvp_counts.get("PENDING", 0),
    }
