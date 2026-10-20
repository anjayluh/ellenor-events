from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.budget import BudgetItemSummary
from app.schemas.meeting import MeetingSummary
from app.schemas.task import TaskSummary
from app.schemas.timeline import TimelineSummary
from app.schemas.vendor import VendorSummary


class ReportGuestSummary(BaseModel):
    total: int
    invitations_sent: int
    invitations_opened: int
    rsvp_responses: int
    attending: int
    not_attending: int
    pending: int
    guest_limit: int | None = None
    guest_used: int = 0
    invitation_email_limit: int | None = None
    invitation_email_used: int = 0


class ReportMeetingSummary(BaseModel):
    summary: MeetingSummary
    decisions: int


class ReportDocumentSummary(BaseModel):
    total: int
    active: int
    archived: int


class ReportCommunicationSummary(BaseModel):
    total_active: int
    unread_count: int
    pinned_count: int
    recent_titles: list[str] = Field(default_factory=list)


class ReportSummary(BaseModel):
    project_id: UUID
    title: str
    event_type: str
    event_date: date | None = None
    generated_at: datetime
    guests: ReportGuestSummary | None = None
    budget: BudgetItemSummary | None = None
    vendors: VendorSummary | None = None
    tasks: TaskSummary | None = None
    timeline: TimelineSummary | None = None
    meetings: ReportMeetingSummary | None = None
    documents: ReportDocumentSummary | None = None
    communications: ReportCommunicationSummary | None = None
