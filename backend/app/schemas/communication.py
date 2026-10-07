from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


COMMUNICATION_TYPES = {"ANNOUNCEMENT", "UPDATE", "REMINDER", "PLANNING_NOTE"}
COMMUNICATION_PRIORITIES = {"NORMAL", "IMPORTANT", "URGENT"}
COMMUNICATION_AUDIENCES = {"ALL_MEMBERS", "SELECTED_MEMBERS"}
COMMUNICATION_STATUSES = {"ACTIVE", "ARCHIVED", "ALL"}


class CommunicationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=1, max_length=10000)
    communication_type: str = "UPDATE"
    priority: str = "NORMAL"
    audience_mode: str = "ALL_MEMBERS"
    recipient_user_ids: list[UUID] = Field(default_factory=list, max_length=100)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_values(self):
        self.communication_type = self.communication_type.upper()
        self.priority = self.priority.upper()
        self.audience_mode = self.audience_mode.upper()
        if self.communication_type not in COMMUNICATION_TYPES:
            raise ValueError("Unsupported communication type")
        if self.priority not in COMMUNICATION_PRIORITIES:
            raise ValueError("Unsupported communication priority")
        if self.audience_mode not in COMMUNICATION_AUDIENCES:
            raise ValueError("Unsupported communication audience")
        if self.audience_mode == "SELECTED_MEMBERS" and not self.recipient_user_ids:
            raise ValueError("Select at least one event member")
        if self.audience_mode == "ALL_MEMBERS" and self.recipient_user_ids:
            raise ValueError("Recipient selection is only available for targeted updates")
        self.title = self.title.strip()
        self.body = self.body.strip()
        if len(self.title) < 3 or not self.body:
            raise ValueError("Title and body are required")
        return self


class CommunicationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    communication_type: str | None = None
    priority: str | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.communication_type is not None:
            self.communication_type = self.communication_type.upper()
            if self.communication_type not in COMMUNICATION_TYPES:
                raise ValueError("Unsupported communication type")
        if self.priority is not None:
            self.priority = self.priority.upper()
            if self.priority not in COMMUNICATION_PRIORITIES:
                raise ValueError("Unsupported communication priority")
        if self.title is not None:
            self.title = self.title.strip()
        if self.body is not None:
            self.body = self.body.strip()
        if self.title is not None and len(self.title) < 3:
            raise ValueError("Title must be at least 3 characters")
        if self.body is not None and not self.body:
            raise ValueError("Message body is required")
        return self


class CommunicationRecipientRead(BaseModel):
    user_id: UUID
    user_name: str | None = None
    user_email: str | None = None
    read_at: datetime | None = None


class CommunicationRead(BaseModel):
    id: UUID
    project_id: UUID
    author_user_id: UUID
    author_name: str | None = None
    author_email: str | None = None
    title: str
    body: str
    communication_type: str
    priority: str
    audience_mode: str
    recipient_user_ids: list[UUID] = Field(default_factory=list)
    recipient_read_states: list[CommunicationRecipientRead] = Field(default_factory=list)
    recipient_count: int = 0
    read_recipient_count: int = 0
    is_pinned: bool
    is_archived: bool
    published_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    is_read: bool = False

    model_config = ConfigDict(from_attributes=True)


class CommunicationSummary(BaseModel):
    project_id: UUID
    total_active: int
    unread_count: int
    pinned_count: int
    recent: list[CommunicationRead] = Field(default_factory=list)
