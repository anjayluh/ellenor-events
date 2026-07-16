from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import EventType


class ProjectCreate(BaseModel):
    type: EventType
    title: str
    event_date: date | None = None
    partner_user_id: UUID | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    event_date: date | None = None
    partner_user_id: UUID | None = None


class ProjectRead(ProjectCreate):
    id: UUID
    owner_user_id: UUID
    status: str
    role: str | None = None
    budget_visibility_mode: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectSettingsUpdate(BaseModel):
    whatsapp_first: bool | None = None
    email_fallback: bool | None = None
    rsvp_required: bool | None = None
    budget_editing_mode: str | None = None
    vendor_mode: str | None = None


class ProjectSettingsRead(BaseModel):
    project_id: UUID
    whatsapp_first: bool
    email_fallback: bool
    rsvp_required: bool
    budget_editing_mode: str
    vendor_mode: str

    model_config = ConfigDict(from_attributes=True)
