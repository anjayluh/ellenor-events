from datetime import date
from uuid import UUID

from app.models.project import Project


def risk_level(overdue_task_count: int, missing_vendor_count: int, budget_variance: float) -> str:
    if overdue_task_count >= 3 or missing_vendor_count >= 2 or budget_variance > 0.2:
        return "high"
    if overdue_task_count > 0 or missing_vendor_count > 0 or budget_variance > 0.1:
        return "medium"
    return "low"


def build_risk_alert(project_id: UUID, title: str, overdue_task_count: int, missing_vendor_count: int, budget_variance: float) -> list[dict]:
    alerts: list[dict] = []
    if overdue_task_count:
        alerts.append({
            "project_id": project_id,
            "title": title,
            "severity": "high" if overdue_task_count >= 3 else "medium",
            "message": f"{overdue_task_count} overdue task(s) need staff attention.",
        })
    if missing_vendor_count:
        alerts.append({
            "project_id": project_id,
            "title": title,
            "severity": "high" if missing_vendor_count >= 2 else "medium",
            "message": f"{missing_vendor_count} critical vendor category gap(s) detected.",
        })
    if budget_variance > 0.1:
        alerts.append({
            "project_id": project_id,
            "title": title,
            "severity": "high" if budget_variance > 0.2 else "medium",
            "message": f"Budget variance is {budget_variance:.0%} of total budget.",
        })
    return alerts


def missing_vendor_categories(categories: set[str]) -> int:
    required = {"decor", "catering", "photography"}
    normalized = {category.lower() for category in categories}
    return len(required - normalized)


def project_event_date(project: Project) -> str | None:
    value = getattr(project, "event_date", None)
    if isinstance(value, date):
        return value.isoformat()
    return None
