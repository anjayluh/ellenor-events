from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import COMMUNICATIONS_MANAGE_PERMISSION, PROJECT_ADMIN_ROLES, ProjectRole, has_permission
from app.models.communication import ProjectCommunication, ProjectCommunicationRead, ProjectCommunicationRecipient
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.communication import CommunicationCreate, CommunicationRead, CommunicationSummary, CommunicationUpdate

PLANNING_ROLES = {ProjectRole.OWNER.value, ProjectRole.PARTNER.value, ProjectRole.COMMITTEE_CHAIR.value, ProjectRole.COMMITTEE_MEMBER.value}
VISIBLE_ROLES = PLANNING_ROLES | {ProjectRole.FAMILY_VIEWER.value}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def can_manage_communications(membership: ProjectMember) -> bool:
    role = ProjectRole(membership.role)
    return role in PROJECT_ADMIN_ROLES or has_permission(role, getattr(membership, "permissions_json", None), COMMUNICATIONS_MANAGE_PERMISSION)


def require_communication_manager(membership: ProjectMember) -> None:
    if not can_manage_communications(membership):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")


def eligible_recipient_ids(db: Session, project_id: UUID, *, planning_only: bool = False) -> set[UUID]:
    allowed_roles = PLANNING_ROLES if planning_only else VISIBLE_ROLES
    rows = db.query(ProjectMember.user_id).filter(ProjectMember.project_id == project_id, ProjectMember.role.in_(allowed_roles)).all()
    return {row[0] for row in rows}


def is_visible_to_user(db: Session, communication: ProjectCommunication, user_id: UUID) -> bool:
    member = db.query(ProjectMember).filter(ProjectMember.project_id == communication.project_id, ProjectMember.user_id == user_id).first()
    if not member:
        return False
    if communication.communication_type == "PLANNING_NOTE" and member.role not in PLANNING_ROLES:
        return False
    if communication.audience_mode == "ALL_MEMBERS":
        return member.role in (PLANNING_ROLES if communication.communication_type == "PLANNING_NOTE" else VISIBLE_ROLES)
    return db.query(ProjectCommunicationRecipient.id).filter(
        ProjectCommunicationRecipient.communication_id == communication.id,
        ProjectCommunicationRecipient.recipient_user_id == user_id,
    ).first() is not None


def get_communication_or_404(db: Session, project_id: UUID, communication_id: UUID, user_id: UUID | None = None) -> ProjectCommunication:
    communication = db.query(ProjectCommunication).filter(ProjectCommunication.project_id == project_id, ProjectCommunication.id == communication_id).first()
    if not communication or (user_id is not None and not is_visible_to_user(db, communication, user_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Communication not found")
    return communication


def recipient_ids(db: Session, communication_id: UUID) -> list[UUID]:
    return [row[0] for row in db.query(ProjectCommunicationRecipient.recipient_user_id).filter(ProjectCommunicationRecipient.communication_id == communication_id).order_by(ProjectCommunicationRecipient.recipient_user_id).all()]


def read_ids(db: Session, communication_ids: list[UUID], user_id: UUID) -> set[UUID]:
    if not communication_ids:
        return set()
    return {row[0] for row in db.query(ProjectCommunicationRead.communication_id).filter(ProjectCommunicationRead.communication_id.in_(communication_ids), ProjectCommunicationRead.user_id == user_id).all()}


def serialize_communication(db: Session, communication: ProjectCommunication, user_id: UUID) -> CommunicationRead:
    author = db.query(User).filter(User.id == communication.author_user_id).first()
    return CommunicationRead(
        id=communication.id,
        project_id=communication.project_id,
        author_user_id=communication.author_user_id,
        author_name=author.name if author else None,
        author_email=author.email if author else None,
        title=communication.title,
        body=communication.body,
        communication_type=communication.communication_type,
        priority=communication.priority,
        audience_mode=communication.audience_mode,
        recipient_user_ids=recipient_ids(db, communication.id),
        is_pinned=communication.is_pinned,
        is_archived=communication.is_archived,
        published_at=communication.published_at,
        created_at=communication.created_at,
        updated_at=communication.updated_at,
        archived_at=communication.archived_at,
        is_read=communication.id in read_ids(db, [communication.id], user_id),
    )


def list_visible_communications(
    db: Session,
    project_id: UUID,
    user_id: UUID,
    *,
    search: str | None = None,
    communication_type: str | None = None,
    priority: str | None = None,
    author_user_id: UUID | None = None,
    status_filter: str = "ACTIVE",
    limit: int = 100,
    offset: int = 0,
) -> list[ProjectCommunication]:
    query = db.query(ProjectCommunication).filter(ProjectCommunication.project_id == project_id)
    if status_filter.upper() != "ALL":
        query = query.filter(ProjectCommunication.is_archived == (status_filter.upper() == "ARCHIVED"))
    if communication_type:
        query = query.filter(ProjectCommunication.communication_type == communication_type.upper())
    if priority:
        query = query.filter(ProjectCommunication.priority == priority.upper())
    if author_user_id:
        query = query.filter(ProjectCommunication.author_user_id == author_user_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(ProjectCommunication.title.ilike(pattern), ProjectCommunication.body.ilike(pattern)))
    rows = query.order_by(ProjectCommunication.is_pinned.desc(), ProjectCommunication.created_at.desc()).all()
    visible = [row for row in rows if is_visible_to_user(db, row, user_id)]
    priority_order = {"URGENT": 0, "IMPORTANT": 1, "NORMAL": 2}
    visible.sort(key=lambda row: (not row.is_pinned, priority_order.get(row.priority, 3)))
    return visible[max(offset, 0): max(offset, 0) + min(max(limit, 1), 250)]


def validate_recipients(db: Session, project_id: UUID, payload: CommunicationCreate) -> list[UUID]:
    if payload.audience_mode == "ALL_MEMBERS":
        return []
    allowed = eligible_recipient_ids(db, project_id, planning_only=payload.communication_type == "PLANNING_NOTE")
    selected = list(dict.fromkeys(payload.recipient_user_ids))
    if any(user_id not in allowed for user_id in selected):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every recipient must be an eligible member of this event")
    return selected


def create_communication(db: Session, project_id: UUID, author_user_id: UUID, payload: CommunicationCreate) -> ProjectCommunication:
    recipients = validate_recipients(db, project_id, payload)
    communication = ProjectCommunication(
        project_id=project_id,
        author_user_id=author_user_id,
        title=payload.title,
        body=payload.body,
        communication_type=payload.communication_type,
        priority=payload.priority,
        audience_mode=payload.audience_mode,
    )
    db.add(communication)
    db.flush()
    db.add_all([
        ProjectCommunicationRecipient(communication_id=communication.id, project_id=project_id, recipient_user_id=user_id)
        for user_id in recipients
    ])
    db.flush()
    return communication


def update_communication(db: Session, communication: ProjectCommunication, payload: CommunicationUpdate) -> ProjectCommunication:
    if communication.is_archived:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived communications cannot be edited")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(communication, field, value)
    communication.updated_at = now_utc()
    db.flush()
    return communication


def set_pinned(communication: ProjectCommunication, pinned: bool) -> ProjectCommunication:
    if communication.is_archived:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived communications cannot be changed")
    communication.is_pinned = pinned
    communication.updated_at = now_utc()
    return communication


def archive_communication(communication: ProjectCommunication) -> ProjectCommunication:
    if not communication.is_archived:
        communication.is_archived = True
        communication.is_pinned = False
        communication.archived_at = now_utc()
        communication.updated_at = now_utc()
    return communication


def mark_communication_read(db: Session, communication: ProjectCommunication, user_id: UUID) -> ProjectCommunicationRead:
    read_state = db.query(ProjectCommunicationRead).filter(ProjectCommunicationRead.communication_id == communication.id, ProjectCommunicationRead.user_id == user_id).first()
    if read_state:
        read_state.read_at = now_utc()
        return read_state
    read_state = ProjectCommunicationRead(communication_id=communication.id, project_id=communication.project_id, user_id=user_id)
    db.add(read_state)
    db.flush()
    return read_state


def communication_summary(db: Session, project_id: UUID, user_id: UUID) -> CommunicationSummary:
    active = list_visible_communications(db, project_id, user_id, status_filter="ACTIVE", limit=250)
    active_ids = [item.id for item in active]
    read = read_ids(db, active_ids, user_id)
    recent = active[:5]
    return CommunicationSummary(
        project_id=project_id,
        total_active=len(active),
        unread_count=sum(1 for item_id in active_ids if item_id not in read),
        pinned_count=sum(1 for item in active if item.is_pinned),
        recent=[serialize_communication(db, item, user_id) for item in recent],
    )
