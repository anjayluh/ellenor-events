from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import MEETINGS_MANAGE_PERMISSION, PROJECT_ADMIN_ROLES, ProjectRole, has_permission
from app.models.document import ProjectDocument
from app.models.meeting import Meeting, MeetingAgendaItem, MeetingDecision, MeetingDocument, MeetingParticipant, MeetingRsvp
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.meeting import (
    MeetingAgendaItemCreate,
    MeetingAgendaItemUpdate,
    MeetingCreate,
    MeetingDecisionCreate,
    MeetingDecisionUpdate,
    MeetingDocumentRead,
    MeetingParticipantRead,
    MeetingParticipantUpsert,
    MeetingRead,
    MeetingSummary,
    MeetingUpdate,
)
from app.services.project_task_service import assignee_map, serialize_task, validate_assignee


def get_meeting_or_404(db: Session, project_id: UUID, meeting_id: UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.project_id == project_id, Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return meeting


def upsert_meeting_rsvp(db: Session, meeting_id: UUID, user_id: UUID, status_value: str, comment: str | None) -> MeetingRsvp:
    rsvp = db.query(MeetingRsvp).filter(MeetingRsvp.meeting_id == meeting_id, MeetingRsvp.user_id == user_id).first()
    if rsvp:
        rsvp.status = status_value
        rsvp.comment = comment
        return rsvp
    rsvp = MeetingRsvp(meeting_id=meeting_id, user_id=user_id, status=status_value, comment=comment)
    db.add(rsvp)
    db.flush()
    return rsvp


def can_manage_meetings(membership: ProjectMember) -> bool:
    role = ProjectRole(membership.role)
    return role in PROJECT_ADMIN_ROLES or has_permission(role, getattr(membership, "permissions_json", None), MEETINGS_MANAGE_PERMISSION)


def require_meeting_manager(membership: ProjectMember) -> None:
    if not can_manage_meetings(membership):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")


def _start_time(meeting: Meeting) -> datetime:
    value = meeting.start_at or meeting.scheduled_time
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _status(value: str | None) -> str:
    normalized = (value or "scheduled").upper()
    normalized_status = {
        "SCHEDULED": "scheduled",
        "PLANNED": "PLANNED",
        "IN_PROGRESS": "IN_PROGRESS",
        "COMPLETED": "COMPLETED",
        "CANCELLED": "CANCELLED",
        "CANCELED": "CANCELLED",
    }.get(normalized)
    if normalized_status is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported meeting status")
    return normalized_status


def _validate_schedule(start_at: datetime, end_at: datetime | None) -> None:
    if end_at is not None and end_at < start_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting end time cannot be before its start time")


def apply_meeting_create(meeting: Meeting, payload: MeetingCreate, *, created_by: UUID) -> Meeting:
    start_at = payload.start_at or payload.scheduled_time
    if start_at is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A meeting start time is required")
    _validate_schedule(start_at, payload.end_at)
    meeting.created_by = created_by
    meeting.type = payload.type.strip()
    meeting.title = payload.title.strip()
    meeting.agenda = payload.agenda.strip() if payload.agenda else None
    meeting.notes = payload.notes.strip() if payload.notes else None
    meeting.decisions_log = payload.decisions_log.strip() if payload.decisions_log else None
    meeting.scheduled_time = payload.scheduled_time or start_at
    meeting.category = payload.category.value
    meeting.description = payload.description.strip() if payload.description else None
    meeting.location = payload.location.strip() if payload.location else None
    meeting.meeting_link = str(payload.meeting_link) if payload.meeting_link else None
    meeting.start_at = start_at
    meeting.end_at = payload.end_at
    meeting.timezone = payload.timezone
    return meeting


def apply_meeting_update(meeting: Meeting, payload: MeetingUpdate) -> Meeting:
    updates = payload.model_dump(exclude_unset=True)
    start_at = updates.get("start_at", meeting.start_at or meeting.scheduled_time)
    end_at = updates.get("end_at", meeting.end_at)
    _validate_schedule(start_at, end_at)
    if "start_at" in updates and updates["start_at"] is not None:
        meeting.start_at = updates["start_at"]
        meeting.scheduled_time = updates["start_at"]
    elif "scheduled_time" in updates and updates["scheduled_time"] is not None:
        meeting.start_at = updates["scheduled_time"]
        meeting.scheduled_time = updates["scheduled_time"]
    if "meeting_link" in updates:
        updates["meeting_link"] = str(updates["meeting_link"]) if updates["meeting_link"] else None
    if "category" in updates and updates["category"] is not None:
        updates["category"] = updates["category"].value
    for field, value in updates.items():
        if field in {"start_at", "scheduled_time"}:
            continue
        if isinstance(value, str) and field in {"title", "type", "agenda", "notes", "decisions_log", "description", "location", "timezone"}:
            value = value.strip() or None
        setattr(meeting, field, value)
    if "status" in updates:
        next_status = _status(updates["status"])
        meeting.status = next_status
        meeting.completed_at = datetime.now(timezone.utc) if next_status in {"COMPLETED", "completed"} else None
        meeting.cancelled_at = datetime.now(timezone.utc) if next_status in {"CANCELLED", "cancelled"} else None
    meeting.updated_at = datetime.now(timezone.utc)
    return meeting


def _conflict_ids(db: Session, meeting: Meeting) -> list[UUID]:
    if meeting.end_at is None:
        return []
    start = _start_time(meeting)
    others = db.query(Meeting).filter(Meeting.project_id == meeting.project_id, Meeting.id != meeting.id).all()
    return [
        other.id for other in others
        if other.end_at is not None
        and other.status not in {"CANCELLED", "cancelled", "CANCELED"}
        and start < _aware(other.end_at)
        and _start_time(other) < _aware(meeting.end_at)
    ]


def serialize_meeting(db: Session, meeting: Meeting, *, include_detail: bool = True) -> MeetingRead:
    participants: list[MeetingParticipantRead] = []
    agenda_items = []
    decisions = []
    documents: list[MeetingDocumentRead] = []
    follow_up_tasks = []
    if include_detail:
        participant_rows = db.query(MeetingParticipant, ProjectMember, User).join(ProjectMember, ProjectMember.project_id == MeetingParticipant.project_id).join(User, User.id == MeetingParticipant.user_id).filter(MeetingParticipant.meeting_id == meeting.id, ProjectMember.user_id == MeetingParticipant.user_id).all()
        participants = [MeetingParticipantRead(id=row.id, meeting_id=row.meeting_id, project_id=row.project_id, user_id=row.user_id, name=user.name, email=user.email, role=member.role, attendance_status=row.attendance_status, responded_at=row.responded_at) for row, member, user in participant_rows]
        agenda_items = db.query(MeetingAgendaItem).filter(MeetingAgendaItem.meeting_id == meeting.id).order_by(MeetingAgendaItem.sort_order.asc(), MeetingAgendaItem.created_at.asc()).all()
        decision_rows = db.query(MeetingDecision, User).join(User, User.id == MeetingDecision.recorded_by_user_id).filter(MeetingDecision.meeting_id == meeting.id).order_by(MeetingDecision.created_at.asc()).all()
        decisions = [dict(id=row.id, meeting_id=row.meeting_id, project_id=row.project_id, decision_text=row.decision_text, context=row.context, recorded_by_user_id=row.recorded_by_user_id, recorder_name=user.name, created_at=row.created_at, updated_at=row.updated_at) for row, user in decision_rows]
        document_rows = db.query(MeetingDocument, ProjectDocument).join(ProjectDocument, ProjectDocument.id == MeetingDocument.document_id).filter(MeetingDocument.meeting_id == meeting.id).order_by(MeetingDocument.created_at.desc()).all()
        documents = [MeetingDocumentRead(id=row.id, meeting_id=row.meeting_id, project_id=row.project_id, document_id=row.document_id, original_filename=document.original_filename, category=document.category, created_at=row.created_at) for row, document in document_rows]
        tasks = db.query(Task).filter(Task.project_id == meeting.project_id, Task.meeting_id == meeting.id).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
        users = assignee_map(db, tasks)
        follow_up_tasks = [serialize_task(task, users) for task in tasks]
    return MeetingRead(
        id=meeting.id, project_id=meeting.project_id, type=meeting.type, title=meeting.title,
        agenda=meeting.agenda, notes=meeting.notes, decisions_log=meeting.decisions_log,
        status=meeting.status, scheduled_time=meeting.scheduled_time, created_by=meeting.created_by,
        category=meeting.category or "PLANNING", description=meeting.description, location=meeting.location,
        meeting_link=meeting.meeting_link, start_at=meeting.start_at, end_at=meeting.end_at,
        timezone=meeting.timezone, completed_at=meeting.completed_at, cancelled_at=meeting.cancelled_at,
        updated_at=meeting.updated_at, participants=participants, agenda_items=agenda_items,
        decisions=decisions, follow_up_tasks=follow_up_tasks, documents=documents,
        conflict_ids=_conflict_ids(db, meeting),
    )


def list_meetings(db: Session, project_id: UUID, *, search: str | None = None, category: str | None = None, status_filter: str | None = None, assignee: UUID | None = None, upcoming: bool = False, today: bool = False) -> list[Meeting]:
    query = db.query(Meeting).filter(Meeting.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(Meeting.title.ilike(pattern), Meeting.description.ilike(pattern), Meeting.location.ilike(pattern)))
    if category:
        query = query.filter(Meeting.category == category.upper())
    if status_filter:
        query = query.filter(Meeting.status == _status(status_filter))
    if assignee:
        query = query.join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id).filter(MeetingParticipant.user_id == assignee)
    current = datetime.now(timezone.utc)
    if upcoming:
        query = query.filter(Meeting.start_at >= current, Meeting.status.notin_(["CANCELLED", "cancelled", "CANCELED", "COMPLETED", "completed"]))
    if today:
        day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(Meeting.start_at >= day_start, Meeting.start_at < day_start + timedelta(days=1))
    return query.order_by(Meeting.start_at.asc().nullslast(), Meeting.scheduled_time.asc()).all()


def meeting_summary(db: Session, project_id: UUID) -> MeetingSummary:
    meetings = list_meetings(db, project_id)
    current = datetime.now(timezone.utc)
    active = [meeting for meeting in meetings if meeting.status not in {"CANCELLED", "cancelled", "CANCELED"}]
    upcoming = [meeting for meeting in active if _start_time(meeting) >= current and meeting.status not in {"COMPLETED", "completed"}]
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    today = [meeting for meeting in meetings if day_start <= _start_time(meeting) < day_start + timedelta(days=1)]
    current_items = [meeting for meeting in active if _start_time(meeting) <= current and (meeting.end_at is None or current <= meeting.end_at) and meeting.status not in {"COMPLETED", "completed"}]
    conflicts = sum(1 for meeting in meetings if _conflict_ids(db, meeting))
    return MeetingSummary(
        project_id=project_id, total=len(meetings),
        planned=sum(1 for meeting in meetings if meeting.status.lower() in {"scheduled", "planned"}),
        in_progress=sum(1 for meeting in meetings if meeting.status.upper() == "IN_PROGRESS"),
        completed=sum(1 for meeting in meetings if meeting.status.lower() == "completed"),
        cancelled=sum(1 for meeting in meetings if meeting.status.lower() == "cancelled"),
        upcoming=len(upcoming), today=len(today),
        current_item=serialize_meeting(db, current_items[0]) if current_items else None,
        next_item=serialize_meeting(db, upcoming[0]) if upcoming else None,
        conflicts=conflicts,
    )


def meeting_participant_or_404(db: Session, project_id: UUID, meeting_id: UUID, user_id: UUID) -> MeetingParticipant:
    participant = db.query(MeetingParticipant).filter(MeetingParticipant.project_id == project_id, MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == user_id).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting participant not found")
    return participant


def add_or_update_participant(db: Session, project_id: UUID, meeting_id: UUID, payload: MeetingParticipantUpsert) -> MeetingParticipant:
    member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meeting participant must be an event member")
    participant = db.query(MeetingParticipant).filter(MeetingParticipant.project_id == project_id, MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == payload.user_id).first()
    if participant is None:
        participant = MeetingParticipant(project_id=project_id, meeting_id=meeting_id, user_id=payload.user_id)
        db.add(participant)
    participant.attendance_status = payload.attendance_status.value
    participant.responded_at = datetime.now(timezone.utc) if payload.attendance_status.value != "INVITED" else None
    db.flush()
    return participant


def agenda_item_or_404(db: Session, project_id: UUID, meeting_id: UUID, item_id: UUID) -> MeetingAgendaItem:
    item = db.query(MeetingAgendaItem).filter(MeetingAgendaItem.project_id == project_id, MeetingAgendaItem.meeting_id == meeting_id, MeetingAgendaItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agenda item not found")
    return item


def decision_or_404(db: Session, project_id: UUID, meeting_id: UUID, decision_id: UUID) -> MeetingDecision:
    decision = db.query(MeetingDecision).filter(MeetingDecision.project_id == project_id, MeetingDecision.meeting_id == meeting_id, MeetingDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting decision not found")
    return decision


def add_agenda_item(db: Session, project_id: UUID, meeting_id: UUID, payload: MeetingAgendaItemCreate) -> MeetingAgendaItem:
    if payload.owner_user_id:
        validate_assignee(db, project_id, payload.owner_user_id)
    item = MeetingAgendaItem(project_id=project_id, meeting_id=meeting_id, **payload.model_dump())
    db.add(item)
    db.flush()
    return item


def add_decision(db: Session, project_id: UUID, meeting_id: UUID, payload: MeetingDecisionCreate, user_id: UUID) -> MeetingDecision:
    decision = MeetingDecision(project_id=project_id, meeting_id=meeting_id, recorded_by_user_id=user_id, **payload.model_dump())
    db.add(decision)
    db.flush()
    return decision


def attach_document(db: Session, project_id: UUID, meeting_id: UUID, document_id: UUID) -> MeetingDocument:
    document = db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id, ProjectDocument.id == document_id, ProjectDocument.is_archived.is_(False)).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found for this event")
    link = db.query(MeetingDocument).filter(MeetingDocument.project_id == project_id, MeetingDocument.meeting_id == meeting_id, MeetingDocument.document_id == document_id).first()
    if link is None:
        link = MeetingDocument(project_id=project_id, meeting_id=meeting_id, document_id=document_id)
        db.add(link)
        db.flush()
    return link
