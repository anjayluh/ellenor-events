from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.budget import Budget
from app.models.meeting import Meeting, MeetingRsvp
from app.models.project import Project
from app.models.staff_member import StaffMember
from app.models.task import Task
from app.models.vendor import Vendor
from app.schemas.staff import StaffAnalytics, StaffDashboard, StaffProjectHealth, StaffRiskAlert
from app.services.audit_service import write_audit_log
from app.services.staff_service import build_risk_alert, missing_vendor_categories, project_event_date, risk_level

router = APIRouter()
STAFF_ROLES = {"PLATFORM_ADMIN", "OPERATIONS_MANAGER", "SUPPORT_AGENT", "STAFF_VIEWER"}


def require_staff_user(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> StaffMember:
    staff_member = (
        db.query(StaffMember)
        .filter(StaffMember.user_id == current_user.id, StaffMember.status == "active")
        .first()
    )
    if not staff_member or staff_member.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    write_audit_log(db, "staff.accessed", actor_user_id=current_user.id, metadata={"staff_role": staff_member.role})
    return staff_member


def project_health_rows(db: Session) -> tuple[list[StaffProjectHealth], list[StaffRiskAlert]]:
    projects = db.query(Project).all()
    health: list[StaffProjectHealth] = []
    alerts: list[StaffRiskAlert] = []
    today = date.today()

    for project in projects:
        meeting_count = db.query(Meeting).filter(Meeting.project_id == project.id).count()
        pending_task_count = db.query(Task).filter(Task.project_id == project.id, Task.status != "done").count()
        overdue_task_count = (
            db.query(Task)
            .filter(Task.project_id == project.id, Task.status != "done", Task.due_date.isnot(None), Task.due_date < today)
            .count()
        )
        vendor_categories = {row.category for row in db.query(Vendor).filter(Vendor.project_id == project.id).all()}
        missing_vendor_count = missing_vendor_categories(vendor_categories)
        budget = db.query(Budget).filter(Budget.project_id == project.id).first()
        total = float(budget.total or 0) if budget else 0
        spent = float(budget.spent or 0) if budget else 0
        budget_variance = (spent / total) if total else 0
        level = risk_level(overdue_task_count, missing_vendor_count, budget_variance)
        health.append(
            StaffProjectHealth(
                project_id=project.id,
                title=project.title,
                status=project.status,
                event_date=project_event_date(project),
                meeting_count=meeting_count,
                pending_task_count=pending_task_count,
                overdue_task_count=overdue_task_count,
                missing_vendor_count=missing_vendor_count,
                budget_variance=round(budget_variance, 4),
                risk_level=level,
            )
        )
        alerts.extend(StaffRiskAlert(**alert) for alert in build_risk_alert(project.id, project.title, overdue_task_count, missing_vendor_count, budget_variance))

    return health, alerts


@router.get("/dashboard", response_model=StaffDashboard)
def staff_dashboard(staff_member: StaffMember = Depends(require_staff_user), db: Session = Depends(get_db)):
    health, alerts = project_health_rows(db)
    active_projects = sum(1 for row in health if row.status == "active")
    archived_projects = sum(1 for row in health if row.status == "archived")
    rsvp_rows = db.query(MeetingRsvp.status).all()
    rsvp_summary = {"accepted": 0, "declined": 0, "tentative": 0}
    for row in rsvp_rows:
        if row.status in rsvp_summary:
            rsvp_summary[row.status] += 1
    write_audit_log(db, "staff.dashboard_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return StaffDashboard(
        active_projects=active_projects,
        archived_projects=archived_projects,
        risk_alerts=alerts,
        rsvp_summary=rsvp_summary,
        project_health=health,
    )


@router.get("/projects", response_model=list[StaffProjectHealth])
def staff_projects(staff_member: StaffMember = Depends(require_staff_user), db: Session = Depends(get_db)):
    health, _ = project_health_rows(db)
    write_audit_log(db, "staff.projects_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return health


@router.get("/analytics", response_model=StaffAnalytics)
def staff_analytics(staff_member: StaffMember = Depends(require_staff_user), db: Session = Depends(get_db)):
    health, _ = project_health_rows(db)
    analytics = StaffAnalytics(
        total_projects=len(health),
        active_projects=sum(1 for row in health if row.status == "active"),
        total_meetings=sum(row.meeting_count for row in health),
        total_vendors=db.query(Vendor).count(),
        total_pending_tasks=sum(row.pending_task_count for row in health),
        high_risk_projects=sum(1 for row in health if row.risk_level == "high"),
    )
    write_audit_log(db, "staff.analytics_viewed", actor_user_id=staff_member.user_id)
    db.commit()
    return analytics
