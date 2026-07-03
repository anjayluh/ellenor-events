from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MeetingCreate(BaseModel):
    type: str
    title: str
    agenda: str | None = None
    scheduled_time: datetime


class MeetingRead(MeetingCreate):
    id: UUID
    project_id: UUID
    created_by: UUID


class RsvpCreate(BaseModel):
    status: str
    comment: str | None = None
