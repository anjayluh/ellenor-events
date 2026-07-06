from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: UUID
    project_id: UUID
    recipient_user_id: UUID | None = None
    recipient_contact: str | None = None
    channel: str
    provider: str
    subject: str | None = None
    body: str
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None = None
    next_retry_at: datetime | None = None
    prepared_at: datetime
    sent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    whatsapp_enabled: bool | None = None
    email_fallback_enabled: bool | None = None
    meeting_updates: bool | None = None
    invite_updates: bool | None = None
    budget_updates: bool | None = None


class NotificationPreferenceRead(BaseModel):
    project_id: UUID
    whatsapp_enabled: bool
    email_fallback_enabled: bool
    meeting_updates: bool
    invite_updates: bool
    budget_updates: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationRetryRead(BaseModel):
    id: UUID
    status: str
    attempts: int
    next_retry_at: datetime | None = None
