from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

from app.core.permissions import ProjectRole


class InviteCreate(BaseModel):
    project_id: UUID
    contact: str
    role_assigned: ProjectRole
    delivery_channel: str = "email"


class InviteRead(BaseModel):
    id: UUID
    project_id: UUID
    contact: str
    role_assigned: ProjectRole
    status: str
    invite_link: str
    whatsapp_url: str | None = None
    delivery_channel: str = "email"
    expires_at: datetime
    sent_count: int = 0
    opened_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class InviteAccept(BaseModel):
    token: str
    name: str
    phone: str | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_contact(self):
        if not self.phone and not self.email:
            raise ValueError("Phone or email is required to accept an invite")
        return self


class InviteAcceptRead(BaseModel):
    status: str
    project_id: UUID
    user_id: UUID
    role: ProjectRole


class InviteAnalytics(BaseModel):
    project_id: UUID
    pending: int
    accepted: int
    expired: int
    cancelled: int
    total_sent: int
    total_opened: int
