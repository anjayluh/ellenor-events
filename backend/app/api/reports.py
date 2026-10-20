from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership
from app.db.session import get_db
from app.services.report_service import (
    budget_rows,
    build_report_summary,
    csv_response,
    decision_rows,
    guest_rows,
    meeting_rows,
    pdf_bytes,
    project_or_404,
    require_budget_export,
    require_guest_export,
    safe_filename,
    task_rows,
    timeline_rows,
    vendor_rows,
)

router = APIRouter()


@router.get("/summary")
def report_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return build_report_summary(db, project_id, membership)


@router.get("/export.pdf")
def report_pdf(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    project = project_or_404(db, project_id)
    filename = safe_filename(project.title)
    return Response(content=pdf_bytes(build_report_summary(db, project_id, membership)), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}-report.pdf"'})


@router.get("/exports/{dataset}.csv")
def report_csv(dataset: str, project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    project = project_or_404(db, project_id)
    if dataset == "guests":
        require_guest_export(membership)
        headers, rows = ["guest", "email", "phone", "category", "group", "invitation_status", "rsvp_status", "attendee_count", "rsvp_note", "sent_at", "opened_at"], guest_rows(db, project_id)
    elif dataset == "budget":
        require_budget_export(membership)
        headers, rows = ["item", "category", "vendor", "planned", "committed", "actual", "paid", "outstanding", "currency", "status", "due_date"], budget_rows(db, project_id)
    elif dataset == "vendors":
        headers, rows = ["vendor", "category", "status", "contact", "email", "phone", "planned", "paid", "outstanding", "linked_budget_items"], vendor_rows(db, project_id)
    elif dataset == "tasks":
        headers, rows = ["title", "category", "priority", "status", "assignee", "due_date", "completed_at"], task_rows(db, project_id)
    elif dataset == "timeline":
        headers, rows = ["title", "category", "start_at", "end_at", "location", "assignee", "status", "has_conflict"], timeline_rows(db, project_id)
    elif dataset == "meetings":
        headers, rows = ["title", "category", "status", "start_at", "end_at", "location", "timezone"], meeting_rows(db, project_id)
    elif dataset == "decisions":
        headers, rows = ["meeting", "decision", "context", "created_at"], decision_rows(db, project_id)
    else:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report export not found")
    body = csv_response(headers, rows)
    filename = safe_filename(project.title)
    return Response(content=body, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}-{dataset}.csv"'})
