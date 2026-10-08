from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_role
from app.core.permissions import ProjectRole, require_role
from app.db.session import get_db
from app.models.meeting import Meeting, MeetingAgendaItem, MeetingDecision, MeetingDocument, MeetingParticipant
from app.models.task import Task
from app.schemas.meeting import (
    MeetingAgendaItemCreate,
    MeetingAgendaItemRead,
    MeetingAgendaItemUpdate,
    MeetingAgendaReorder,
    MeetingCreate,
    MeetingDecisionCreate,
    MeetingDecisionRead,
    MeetingDecisionUpdate,
    MeetingDocumentAttach,
    MeetingDocumentRead,
    MeetingNotesUpdate,
    MeetingParticipantRead,
    MeetingParticipantUpsert,
    MeetingRead,
    MeetingSummary,
    MeetingUpdate,
    RsvpCreate,
    RsvpRead,
)
from app.schemas.task import TaskCreate, TaskRead
from app.services.audit_service import write_audit_log
from app.services.meeting_service import (
    add_agenda_item,
    add_decision,
    add_or_update_participant,
    apply_meeting_create,
    apply_meeting_update,
    agenda_item_or_404,
    attach_document,
    decision_or_404,
    get_meeting_or_404,
    list_meetings,
    meeting_summary,
    require_meeting_manager,
    serialize_meeting,
    upsert_meeting_rsvp,
)
from app.services.notification_service import queue_project_notification
from app.services.project_task_service import assignee_map, create_project_task, serialize_task

router = APIRouter()

MEETING_DELETE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR}


@router.get("/summary", response_model=MeetingSummary)
def get_meeting_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return meeting_summary(db, project_id)


@router.get("", response_model=list[MeetingRead])
def list_meeting_records(
    project_id: UUID,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    assignee: UUID | None = None,
    upcoming: bool = False,
    today: bool = False,
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    return [serialize_meeting(db, meeting) for meeting in list_meetings(db, project_id, search=search, category=category, status_filter=status_filter, assignee=assignee, upcoming=upcoming, today=today)]


@router.post("", response_model=MeetingRead)
def create_meeting(
    project_id: UUID,
    payload: MeetingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_meeting_manager(membership)
    meeting = Meeting(project_id=project_id)
    apply_meeting_create(meeting, payload, created_by=current_user.id)
    db.add(meeting)
    db.flush()
    queue_project_notification(db, project_id, "meeting.created", title=meeting.title, message=f"New meeting scheduled: {meeting.title}", actor_user_id=current_user.id, metadata={"meeting_id": str(meeting.id)})
    db.commit()
    db.refresh(meeting)
    return serialize_meeting(db, meeting)


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return serialize_meeting(db, get_meeting_or_404(db, project_id, meeting_id))


@router.patch("/{meeting_id}", response_model=MeetingRead)
def update_meeting(
    project_id: UUID,
    meeting_id: UUID,
    payload: MeetingUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_meeting_manager(membership)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    apply_meeting_update(meeting, payload)
    meeting.updated_by_user_id = current_user.id
    queue_project_notification(db, project_id, "meeting.updated", title=meeting.title, message=f"Meeting updated: {meeting.title}", actor_user_id=current_user.id, metadata={"meeting_id": str(meeting.id)})
    db.commit()
    db.refresh(meeting)
    return serialize_meeting(db, meeting)


@router.post("/{meeting_id}/complete", response_model=MeetingRead)
def complete_meeting(project_id: UUID, meeting_id: UUID, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    apply_meeting_update(meeting, MeetingUpdate(status="COMPLETED"))
    meeting.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(meeting)
    return serialize_meeting(db, meeting)


@router.post("/{meeting_id}/cancel", response_model=MeetingRead)
def cancel_meeting(project_id: UUID, meeting_id: UUID, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    apply_meeting_update(meeting, MeetingUpdate(status="CANCELLED"))
    meeting.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(meeting)
    return serialize_meeting(db, meeting)


@router.post("/{meeting_id}/reopen", response_model=MeetingRead)
def reopen_meeting(project_id: UUID, meeting_id: UUID, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    apply_meeting_update(meeting, MeetingUpdate(status="PLANNED"))
    meeting.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(meeting)
    return serialize_meeting(db, meeting)


@router.delete("/{meeting_id}")
def delete_meeting(project_id: UUID, meeting_id: UUID, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), MEETING_DELETE_ROLES)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    linked_tasks = db.query(func.count(Task.id)).filter(Task.project_id == project_id, Task.meeting_id == meeting_id).scalar() or 0
    if linked_tasks:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Remove or reassign follow-up tasks before deleting this meeting")
    db.delete(meeting)
    write_audit_log(db, "meeting.deleted", actor_user_id=current_user.id, project_id=project_id, metadata={"meeting_id": str(meeting_id)})
    db.commit()
    return {"status": "deleted"}


@router.post("/{meeting_id}/rsvp", response_model=RsvpRead)
def rsvp(project_id: UUID, meeting_id: UUID, payload: RsvpCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    get_meeting_or_404(db, project_id, meeting_id)
    response = upsert_meeting_rsvp(db, meeting_id, current_user.id, payload.status, payload.comment)
    write_audit_log(db, "meeting.rsvp_recorded", actor_user_id=current_user.id, project_id=project_id, metadata={"meeting_id": str(meeting_id), "status": payload.status})
    db.commit()
    db.refresh(response)
    return response


@router.get("/{meeting_id}/participants", response_model=list[MeetingParticipantRead])
def list_participants(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    return serialize_meeting(db, meeting).participants


@router.post("/{meeting_id}/participants", response_model=MeetingParticipantRead, status_code=status.HTTP_201_CREATED)
def add_participant(project_id: UUID, meeting_id: UUID, payload: MeetingParticipantUpsert, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    get_meeting_or_404(db, project_id, meeting_id)
    participant = add_or_update_participant(db, project_id, meeting_id, payload)
    db.commit()
    participants = serialize_meeting(db, get_meeting_or_404(db, project_id, meeting_id)).participants
    return next(item for item in participants if item.user_id == participant.user_id)


@router.patch("/{meeting_id}/participants/{user_id}", response_model=MeetingParticipantRead)
def update_participant(project_id: UUID, meeting_id: UUID, user_id: UUID, payload: MeetingParticipantUpsert, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    if payload.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Participant user ID does not match the route")
    get_meeting_or_404(db, project_id, meeting_id)
    add_or_update_participant(db, project_id, meeting_id, payload)
    db.commit()
    participants = serialize_meeting(db, get_meeting_or_404(db, project_id, meeting_id)).participants
    return next(participant for participant in participants if participant.user_id == user_id)


@router.delete("/{meeting_id}/participants/{user_id}")
def delete_participant(project_id: UUID, meeting_id: UUID, user_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    participant = db.query(MeetingParticipant).filter(MeetingParticipant.project_id == project_id, MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == user_id).first()
    if participant is None:
        get_meeting_or_404(db, project_id, meeting_id)
        return {"status": "deleted"}
    db.delete(participant)
    db.commit()
    return {"status": "deleted"}


@router.get("/{meeting_id}/agenda", response_model=list[MeetingAgendaItemRead])
def list_agenda(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    get_meeting_or_404(db, project_id, meeting_id)
    return db.query(MeetingAgendaItem).filter(MeetingAgendaItem.project_id == project_id, MeetingAgendaItem.meeting_id == meeting_id).order_by(MeetingAgendaItem.sort_order.asc(), MeetingAgendaItem.created_at.asc()).all()


@router.post("/{meeting_id}/agenda", response_model=MeetingAgendaItemRead, status_code=status.HTTP_201_CREATED)
def create_agenda_item(project_id: UUID, meeting_id: UUID, payload: MeetingAgendaItemCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    get_meeting_or_404(db, project_id, meeting_id)
    item = add_agenda_item(db, project_id, meeting_id, payload)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{meeting_id}/agenda/{item_id}", response_model=MeetingAgendaItemRead)
def update_agenda_item(project_id: UUID, meeting_id: UUID, item_id: UUID, payload: MeetingAgendaItemUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    item = agenda_item_or_404(db, project_id, meeting_id, item_id)
    updates = payload.model_dump(exclude_unset=True)
    if "owner_user_id" in updates and updates["owner_user_id"]:
        validate_assignee(db, project_id, updates["owner_user_id"])
    for field, value in updates.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{meeting_id}/agenda/reorder", response_model=list[MeetingAgendaItemRead])
def reorder_agenda(project_id: UUID, meeting_id: UUID, payload: MeetingAgendaReorder, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    get_meeting_or_404(db, project_id, meeting_id)
    items = db.query(MeetingAgendaItem).filter(MeetingAgendaItem.project_id == project_id, MeetingAgendaItem.meeting_id == meeting_id).all()
    item_map = {item.id: item for item in items}
    if set(item_map) != set(payload.item_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Agenda reorder must include exactly the meeting agenda items")
    for index, item_id in enumerate(payload.item_ids):
        item_map[item_id].sort_order = index
    db.commit()
    return db.query(MeetingAgendaItem).filter(MeetingAgendaItem.project_id == project_id, MeetingAgendaItem.meeting_id == meeting_id).order_by(MeetingAgendaItem.sort_order.asc()).all()


@router.delete("/{meeting_id}/agenda/{item_id}")
def delete_agenda_item(project_id: UUID, meeting_id: UUID, item_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    item = agenda_item_or_404(db, project_id, meeting_id, item_id)
    db.delete(item)
    db.commit()
    return {"status": "deleted"}


@router.get("/{meeting_id}/decisions", response_model=list[MeetingDecisionRead])
def list_decisions(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    return serialize_meeting(db, meeting).decisions


@router.post("/{meeting_id}/decisions", response_model=MeetingDecisionRead, status_code=status.HTTP_201_CREATED)
def create_decision(project_id: UUID, meeting_id: UUID, payload: MeetingDecisionCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    get_meeting_or_404(db, project_id, meeting_id)
    decision = add_decision(db, project_id, meeting_id, payload, current_user.id)
    db.commit()
    db.refresh(decision)
    return decision


@router.patch("/{meeting_id}/decisions/{decision_id}", response_model=MeetingDecisionRead)
def update_decision(project_id: UUID, meeting_id: UUID, decision_id: UUID, payload: MeetingDecisionUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    decision = decision_or_404(db, project_id, meeting_id, decision_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(decision, field, value)
    decision.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(decision)
    return decision


@router.delete("/{meeting_id}/decisions/{decision_id}")
def delete_decision(project_id: UUID, meeting_id: UUID, decision_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    decision = decision_or_404(db, project_id, meeting_id, decision_id)
    db.delete(decision)
    db.commit()
    return {"status": "deleted"}


@router.patch("/{meeting_id}/notes", response_model=MeetingRead)
def update_notes(project_id: UUID, meeting_id: UUID, payload: MeetingNotesUpdate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    meeting.notes = payload.notes
    meeting.decisions_log = payload.decisions_log
    meeting.updated_by_user_id = current_user.id
    meeting.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(meeting)
    return serialize_meeting(db, meeting)


@router.get("/{meeting_id}/tasks", response_model=list[TaskRead])
def list_follow_up_tasks(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    get_meeting_or_404(db, project_id, meeting_id)
    tasks = db.query(Task).filter(Task.project_id == project_id, Task.meeting_id == meeting_id).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    return [serialize_task(task, assignee_map(db, tasks)) for task in tasks]


@router.post("/{meeting_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_follow_up_task(project_id: UUID, meeting_id: UUID, payload: TaskCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    get_meeting_or_404(db, project_id, meeting_id)
    if payload.meeting_id not in {None, meeting_id}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Follow-up task must belong to this meeting")
    payload.meeting_id = meeting_id
    task = create_project_task(db, project_id, payload, created_by_user_id=current_user.id)
    db.commit()
    db.refresh(task)
    return serialize_task(task, assignee_map(db, [task]))


@router.get("/{meeting_id}/documents", response_model=list[MeetingDocumentRead])
def list_meeting_documents(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    return serialize_meeting(db, meeting).documents


@router.post("/{meeting_id}/documents", response_model=MeetingDocumentRead, status_code=status.HTTP_201_CREATED)
def attach_meeting_document(project_id: UUID, meeting_id: UUID, payload: MeetingDocumentAttach, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    get_meeting_or_404(db, project_id, meeting_id)
    attach_document(db, project_id, meeting_id, payload.document_id)
    db.commit()
    return next(document for document in serialize_meeting(db, get_meeting_or_404(db, project_id, meeting_id)).documents if document.document_id == payload.document_id)


@router.delete("/{meeting_id}/documents/{document_id}")
def detach_meeting_document(project_id: UUID, meeting_id: UUID, document_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_meeting_manager(membership)
    link = db.query(MeetingDocument).filter(MeetingDocument.project_id == project_id, MeetingDocument.meeting_id == meeting_id, MeetingDocument.document_id == document_id).first()
    if link:
        db.delete(link)
        db.commit()
    return {"status": "deleted"}
