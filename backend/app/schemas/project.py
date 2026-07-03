from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import EventType


class ProjectCreate(BaseModel):
    type: EventType
    title: str
    event_date: date | None = None
    partner_user_id: UUID | None = None


class ProjectRead(ProjectCreate):
    id: UUID
    owner_user_id: UUID
    status: str
