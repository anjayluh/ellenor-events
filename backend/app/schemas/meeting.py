from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MeetingCreate(BaseModel):
    type: str
    title: str
    agenda: str | None = None
    notes: str | None = None
    decisions_log: str | None = None
    scheduled_time: datetime


class MeetingUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    agenda: str | None = None
    notes: str | None = None
    decisions_log: str | None = None
    status: str | None = None
    scheduled_time: datetime | None = None


class MeetingRead(BaseModel):
    id: UUID
    project_id: UUID
    type: str
    title: str
    agenda: str | None = None
    notes: str | None = None
    decisions_log: str | None = None
    status: str
    scheduled_time: datetime
    created_by: UUID

    model_config = ConfigDict(from_attributes=True)


class RsvpCreate(BaseModel):
    status: str
    comment: str | None = None


class RsvpRead(BaseModel):
    id: UUID
    meeting_id: UUID
    user_id: UUID
    status: str
    comment: str | None = None

    model_config = ConfigDict(from_attributes=True)
