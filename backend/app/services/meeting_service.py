from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingRsvp


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
