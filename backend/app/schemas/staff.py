from uuid import UUID

from pydantic import BaseModel


class StaffProjectHealth(BaseModel):
    project_id: UUID
    title: str
    status: str
    event_date: str | None = None
    meeting_count: int
    pending_task_count: int
    overdue_task_count: int
    missing_vendor_count: int
    budget_variance: float
    risk_level: str


class StaffRiskAlert(BaseModel):
    project_id: UUID
    title: str
    severity: str
    message: str


class StaffDashboard(BaseModel):
    active_projects: int
    archived_projects: int
    risk_alerts: list[StaffRiskAlert]
    rsvp_summary: dict[str, int]
    project_health: list[StaffProjectHealth]


class StaffAnalytics(BaseModel):
    total_projects: int
    active_projects: int
    total_meetings: int
    total_vendors: int
    total_pending_tasks: int
    high_risk_projects: int
