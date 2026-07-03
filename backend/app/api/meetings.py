from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership
from app.db.session import get_db
from app.models.meeting import Meeting, MeetingRsvp
from app.schemas.meeting import MeetingCreate, MeetingRead, RsvpCreate

router = APIRouter()


@router.get("", response_model=list[MeetingRead])
def list_meetings(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(Meeting).filter(Meeting.project_id == project_id).order_by(Meeting.scheduled_time.asc()).all()


@router.post("", response_model=MeetingRead)
def create_meeting(project_id: UUID, payload: MeetingCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    meeting = Meeting(project_id=project_id, created_by=current_user.id, **payload.model_dump())
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/rsvp")
def rsvp(project_id: UUID, meeting_id: UUID, payload: RsvpCreate, current_user: CurrentUser = Depends(get_current_user), membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    response = MeetingRsvp(meeting_id=meeting_id, user_id=current_user.id, **payload.model_dump())
    db.add(response)
    db.commit()
    return {"status": "recorded"}
