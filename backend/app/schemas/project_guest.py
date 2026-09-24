from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ProjectGuestCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=80)
    group_name: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    invitation_card_url: str | None = None

    @model_validator(mode="after")
    def require_contact(self):
        if self.email is None and not (self.phone or "").strip():
            raise ValueError("Add an email or phone number for this guest")
        return self


class ProjectGuestUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=80)
    group_name: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    invitation_card_url: str | None = None
    invitation_status: str | None = None
    rsvp_status: str | None = None


class ProjectGuestRead(BaseModel):
    id: UUID
    project_id: UUID
    first_name: str
    last_name: str | None = None
    display_name: str
    email: str | None = None
    phone: str | None = None
    category: str | None = None
    group_name: str | None = None
    notes: str | None = None
    invitation_card_url: str | None = None
    invitation_status: str
    rsvp_status: str
    rsvp_responded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectGuestInvitationRead(BaseModel):
    id: UUID
    project_guest_id: UUID
    project_id: UUID
    recipient_email: str
    recipient_name: str
    token: str
    status: str
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    responded_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuestUsageRead(BaseModel):
    key: str
    used: int
    limit: int | None = None
    remaining: int | None = None
    label: str


class ProjectGuestSummary(BaseModel):
    project_id: UUID
    total: int
    invitation_sent: int
    attending: int
    not_attending: int
    pending_rsvp: int
    opened: int
    responded: int
    guest_usage: GuestUsageRead
    invitation_email_usage: GuestUsageRead


class GuestInviteSend(BaseModel):
    resend: bool = False


class GuestInviteSendRead(BaseModel):
    guest: ProjectGuestRead
    invitation: ProjectGuestInvitationRead
    already_sent: bool = False
    guest_usage: GuestUsageRead
    invitation_email_usage: GuestUsageRead


class PublicGuestInviteRead(BaseModel):
    token: str
    recipient_name: str
    event_title: str
    event_date: date | None = None
    invitation_card_url: str | None = None
    invitation_status: str
    rsvp_status: str


class PublicGuestRsvpUpdate(BaseModel):
    rsvp_status: str


class PublicGuestRsvpRead(PublicGuestInviteRead):
    responded_at: datetime | None = None
