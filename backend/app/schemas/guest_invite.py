from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator


class GuestInviteCreate(BaseModel):
    guest_name: str
    email: EmailStr | None = None
    phone: str | None = None
    invitation_card_url: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Email or phone is required")
        return self


class GuestInviteUpdate(BaseModel):
    guest_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    invitation_card_url: str | None = None
    status: str | None = None
    attendance_status: str | None = None
    notes: str | None = None


class GuestInviteResponse(BaseModel):
    attendance_status: str


class GuestInviteRead(BaseModel):
    id: UUID
    project_id: UUID
    guest_name: str
    email: str | None = None
    phone: str | None = None
    invitation_card_url: str | None = None
    token: str
    status: str
    attendance_status: str
    sent_count: int = 0
    last_sent_at: datetime | None = None
    responded_at: datetime | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GuestInviteSummary(BaseModel):
    project_id: UUID
    total: int
    sent: int
    accepted: int
    declined: int
    pending: int
    rejected: int
