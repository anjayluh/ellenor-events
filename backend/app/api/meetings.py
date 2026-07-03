from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_role
from app.core.permissions import ProjectRole, require_role
from app.db.session import get_db
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate, RsvpCreate, RsvpRead
from app.services.audit_service import write_audit_log
from app.services.meeting_service import get_meeting_or_404, upsert_meeting_rsvp
from app.services.notification_service import queue_project_notification

router = APIRouter()

MEETING_WRITE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR, ProjectRole.COMMITTEE_MEMBER}
MEETING_DELETE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR}


@router.get("", response_model=list[MeetingRead])
def list_meetings(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(Meeting).filter(Meeting.project_id == project_id).order_by(Meeting.scheduled_time.asc()).all()


@router.post("", response_model=MeetingRead)
def create_meeting(
    project_id: UUID,
    payload: MeetingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_role(membership_role(membership), MEETING_WRITE_ROLES)
    meeting = Meeting(project_id=project_id, created_by=current_user.id, **payload.model_dump())
    db.add(meeting)
    db.flush()
    queue_project_notification(
        db,
        project_id,
        "meeting.created",
        title=meeting.title,
        message=f"New meeting scheduled: {meeting.title}",
        actor_user_id=current_user.id,
        metadata={"meeting_id": str(meeting.id)},
    )
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(project_id: UUID, meeting_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return get_meeting_or_404(db, project_id, meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingRead)
def update_meeting(
    project_id: UUID,
    meeting_id: UUID,
    payload: MeetingUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_role(membership_role(membership), MEETING_WRITE_ROLES)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)
    meeting.updated_at = datetime.now(timezone.utc)
    queue_project_notification(
        db,
        project_id,
        "meeting.updated",
        title=meeting.title,
        message=f"Meeting updated: {meeting.title}",
        actor_user_id=current_user.id,
        metadata={"meeting_id": str(meeting.id)},
    )
    db.commit()
    db.refresh(meeting)
    return meeting


@router.delete("/{meeting_id}")
def delete_meeting(
    project_id: UUID,
    meeting_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_role(membership_role(membership), MEETING_DELETE_ROLES)
    meeting = get_meeting_or_404(db, project_id, meeting_id)
    db.delete(meeting)
    write_audit_log(db, "meeting.deleted", actor_user_id=current_user.id, project_id=project_id, metadata={"meeting_id": str(meeting_id)})
    db.commit()
    return {"status": "deleted"}


@router.post("/{meeting_id}/rsvp", response_model=RsvpRead)
def rsvp(
    project_id: UUID,
    meeting_id: UUID,
    payload: RsvpCreate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    get_meeting_or_404(db, project_id, meeting_id)
    response = upsert_meeting_rsvp(db, meeting_id, current_user.id, payload.status, payload.comment)
    write_audit_log(
        db,
        "meeting.rsvp_recorded",
        actor_user_id=current_user.id,
        project_id=project_id,
        metadata={"meeting_id": str(meeting_id), "status": payload.status},
    )
    db.commit()
    db.refresh(response)
    return response
