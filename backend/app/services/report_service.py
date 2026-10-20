from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import membership_budget_visibility, membership_role
from app.core.permissions import BudgetVisibilityMode, ProjectRole, has_permission, require_budget_read
from app.models.budget import ProjectBudgetItem
from app.models.communication import ProjectCommunication
from app.models.document import ProjectDocument
from app.models.meeting import Meeting, MeetingDecision
from app.models.project import Project
from app.models.project_guest import ProjectGuest, ProjectGuestInvitation
from app.models.task import Task
from app.models.timeline import ProjectTimelineItem
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.report import (
    ReportCommunicationSummary,
    ReportDocumentSummary,
    ReportGuestSummary,
    ReportMeetingSummary,
    ReportSummary,
)
from app.services.communication_service import communication_summary
from app.services.meeting_service import list_meetings, meeting_summary
from app.services.project_budget_service import budget_item_summary, outstanding_amount, serialize_budget_item, vendor_map
from app.services.project_document_service import document_summary, list_documents, require_document_viewer
from app.services.project_guest_service import guest_summary_counts, guest_usage, invitation_email_usage
from app.services.project_task_service import list_project_tasks, serialize_task, task_summary
from app.services.project_timeline_service import active_items_for_conflicts, assignee_map as timeline_assignee_map, find_conflicts_for_item, list_project_timeline_items, serialize_timeline_item, timeline_summary
from app.services.project_vendor_service import list_project_vendors, serialize_vendor, vendor_summary


def _money(value: object) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _csv_value(value: object) -> object:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def csv_response(headers: list[str], rows: list[list[object]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_csv_value(value) for value in row])
    return output.getvalue()


def safe_filename(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return normalized or "event"


def project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _usage_values(db: Session, project: Project) -> tuple[int, int | None, int, int | None]:
    try:
        guest = guest_usage(db, project)
        guest_used, guest_limit = guest.used, guest.limit
    except HTTPException:
        guest_used, guest_limit = 0, 0
    try:
        emails = invitation_email_usage(db, project)
        email_used, email_limit = emails.used, emails.limit
    except HTTPException:
        email_used, email_limit = 0, 0
    return guest_used, guest_limit, email_used, email_limit


def build_report_summary(db: Session, project_id: UUID, membership) -> ReportSummary:
    project = project_or_404(db, project_id)
    role = membership_role(membership)
    guests = None
    if role in {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR} or has_permission(role, getattr(membership, "permissions_json", None), "guest_invites.manage"):
        counts = guest_summary_counts(db, project_id)
        guest_used, guest_limit, email_used, email_limit = _usage_values(db, project)
        guests = ReportGuestSummary(
            total=counts["total"], invitations_sent=counts["invitation_sent"], invitations_opened=counts["invitations_opened"],
            rsvp_responses=counts["rsvp_responses"], attending=counts["attending"], not_attending=counts["not_attending"],
            pending=counts["pending_rsvp"], guest_used=guest_used, guest_limit=guest_limit,
            invitation_email_used=email_used, invitation_email_limit=email_limit,
        )

    budget = None
    visibility = membership_budget_visibility(membership)
    if visibility != BudgetVisibilityMode.NO_ACCESS:
        require_budget_read(visibility)
        budget = budget_item_summary(db, project_id)

    documents = None
    try:
        require_document_viewer(membership)
        document_counts = document_summary(db, project_id)
        documents = ReportDocumentSummary(total=document_counts.total, active=document_counts.active, archived=document_counts.archived)
    except HTTPException:
        pass

    communications = communication_summary(db, project_id, membership.user_id)
    meetings = meeting_summary(db, project_id)
    decision_count = db.query(MeetingDecision.id).filter(MeetingDecision.project_id == project_id).count()
    guest_section = guests
    try:
        vendors = vendor_summary(db, project)
    except HTTPException:
        vendors = None
    return ReportSummary(
        project_id=project_id,
        title=project.title,
        event_type=project.type,
        event_date=project.event_date,
        generated_at=datetime.now(timezone.utc),
        guests=guest_section,
        budget=budget,
        vendors=vendors,
        tasks=task_summary(db, project_id, current_user_id=membership.user_id),
        timeline=timeline_summary(db, project_id),
        meetings=ReportMeetingSummary(summary=meetings, decisions=decision_count),
        documents=documents,
        communications=ReportCommunicationSummary(
            total_active=communications.total_active,
            unread_count=communications.unread_count,
            pinned_count=communications.pinned_count,
            recent_titles=[item.title for item in communications.recent],
        ),
    )


def require_budget_export(membership) -> None:
    if membership_budget_visibility(membership) == BudgetVisibilityMode.NO_ACCESS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Budget is not visible for this project role")


def require_guest_export(membership) -> None:
    role = membership_role(membership)
    if role in {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR} or has_permission(role, getattr(membership, "permissions_json", None), "guest_invites.manage"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guest records are not available for this project role")


def guest_rows(db: Session, project_id: UUID) -> list[list[object]]:
    guests = db.query(ProjectGuest).filter(ProjectGuest.project_id == project_id).order_by(ProjectGuest.created_at.asc()).all()
    rows: list[list[object]] = []
    for guest in guests:
        invitation = db.query(ProjectGuestInvitation).filter(ProjectGuestInvitation.project_guest_id == guest.id).order_by(ProjectGuestInvitation.created_at.desc()).first()
        rows.append([guest.display_name, guest.email, guest.phone, guest.category, guest.group_name, guest.invitation_status, guest.rsvp_status, guest.rsvp_attendee_count, guest.rsvp_note, invitation.sent_at if invitation else None, invitation.opened_at if invitation else None])
    return rows


def budget_rows(db: Session, project_id: UUID) -> list[list[object]]:
    items = db.query(ProjectBudgetItem).filter(ProjectBudgetItem.project_id == project_id).order_by(ProjectBudgetItem.created_at.asc()).all()
    vendors = vendor_map(db, items)
    return [[item.name, item.category, vendors.get(item.vendor_id).name if item.vendor_id and vendors.get(item.vendor_id) else None, _money(item.planned_amount), _money(item.committed_amount), _money(item.actual_amount), _money(item.paid_amount), _money(outstanding_amount(item)), item.currency, item.status, item.due_date] for item in items]


def vendor_rows(db: Session, project_id: UUID) -> list[list[object]]:
    rows: list[list[object]] = []
    for vendor in list_project_vendors(db, project_id, limit=250):
        serialized = serialize_vendor(db, vendor, include_budget_items=False)
        summary = serialized.financial_summary
        rows.append([vendor.name, vendor.category, vendor.status, vendor.contact_person, vendor.email, vendor.phone, _money(summary.planned_total), _money(summary.paid_total), _money(summary.outstanding_total), summary.linked_budget_items_count])
    return rows


def task_rows(db: Session, project_id: UUID) -> list[list[object]]:
    tasks = list_project_tasks(db, project_id, current_user_id=None, limit=250)
    users = {user.id: user for user in db.query(User).filter(User.id.in_({task.assigned_to for task in tasks if task.assigned_to})).all()} if tasks else {}
    return [[task.title, task.category, task.priority, task.status, users.get(task.assigned_to).name if task.assigned_to and users.get(task.assigned_to) else None, task.due_date, task.completed_at] for task in tasks]


def timeline_rows(db: Session, project_id: UUID) -> list[list[object]]:
    items = list_project_timeline_items(db, project_id, limit=250)
    users = timeline_assignee_map(db, items)
    candidates = active_items_for_conflicts(db, project_id)
    return [[item.title, item.category, item.start_at, item.end_at, item.location, users.get(item.assignee_user_id).name if item.assignee_user_id and users.get(item.assignee_user_id) else None, item.status, bool(find_conflicts_for_item(item, candidates))] for item in items]


def meeting_rows(db: Session, project_id: UUID) -> list[list[object]]:
    meetings = list_meetings(db, project_id)
    return [[meeting.title, meeting.category, meeting.status, meeting.start_at or meeting.scheduled_time, meeting.end_at, meeting.location, meeting.timezone] for meeting in meetings]


def decision_rows(db: Session, project_id: UUID) -> list[list[object]]:
    rows = db.query(MeetingDecision, Meeting).join(Meeting, Meeting.id == MeetingDecision.meeting_id).filter(MeetingDecision.project_id == project_id).order_by(MeetingDecision.created_at.asc()).all()
    return [[meeting.title, decision.decision_text, decision.context, decision.created_at] for decision, meeting in rows]


def pdf_bytes(summary: ReportSummary) -> bytes:
    # A small dependency-free PDF writer keeps exports deployable in the existing runtime.
    lines = [f"Ellenor Events — {summary.title}", f"Event type: {summary.event_type}", f"Event date: {summary.event_date or 'Not set'}", "", "REPORT OVERVIEW"]
    if summary.guests:
        lines += [f"Guests: {summary.guests.total} total; {summary.guests.rsvp_responses} RSVP responses; {summary.guests.attending} attending; {summary.guests.pending} pending"]
    if summary.budget:
        lines += [f"Budget: {summary.budget.total_items} items; planned {_money(summary.budget.total_planned)}; paid {_money(summary.budget.total_paid)}; outstanding {_money(summary.budget.total_outstanding)} {summary.budget.currency}"]
    if summary.vendors:
        lines += [f"Vendors: {summary.vendors.total} total; {summary.vendors.confirmed} confirmed; outstanding {_money(summary.vendors.outstanding_balance)}"]
    if summary.tasks:
        lines += [f"Tasks: {summary.tasks.total} total; {summary.tasks.completed} complete; {summary.tasks.overdue} overdue"]
    if summary.timeline:
        lines += [f"Timeline: {summary.timeline.total} items; {summary.timeline.upcoming} upcoming; {summary.timeline.conflicts} conflicts"]
    if summary.meetings:
        lines += [f"Meetings: {summary.meetings.summary.total} total; {summary.meetings.summary.upcoming} upcoming; {summary.meetings.decisions} decisions"]
    if summary.documents:
        lines += [f"Documents: {summary.documents.active} active; {summary.documents.archived} archived"]
    if summary.communications:
        lines += [f"Communications: {summary.communications.total_active} active; {summary.communications.unread_count} unread; {summary.communications.pinned_count} pinned"]
    lines += ["", f"Generated: {summary.generated_at.isoformat()}"]
    return _simple_pdf(lines)


def _simple_pdf(lines: list[str]) -> bytes:
    lines = [line[:150] for line in lines]
    content_lines = ["BT", "/F1 11 Tf", "50 770 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            content_lines.append("0 -16 Td")
        content_lines.append(f"({escaped}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)
