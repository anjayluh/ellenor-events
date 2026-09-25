from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import PROJECT_ADMIN_ROLES, TASKS_MANAGE_PERMISSION, ProjectRole, has_permission
from app.models.project_member import ProjectMember
from app.models.timeline import ProjectTimelineItem
from app.models.user import User
from app.schemas.timeline import TimelineConflictRead, TimelineItemCreate, TimelineItemRead, TimelineItemUpdate, TimelineSummary, TimelineSummaryItem

MUTABLE_STATUS_VALUES = {"UPCOMING", "COMPLETED", "CANCELLED", "IN_PROGRESS"}


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def can_manage_timeline(membership: ProjectMember) -> bool:
    role = ProjectRole(membership.role)
    return role in PROJECT_ADMIN_ROLES or has_permission(role, getattr(membership, "permissions_json", None), TASKS_MANAGE_PERMISSION)


def require_timeline_manager(membership: ProjectMember) -> None:
    if can_manage_timeline(membership):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")


def effective_status(item: ProjectTimelineItem, *, current_time: datetime | None = None) -> str:
    if item.status in {"COMPLETED", "CANCELLED"}:
        return item.status
    current = current_time or now_utc()
    start_at = normalize_datetime(item.start_at)
    end_at = normalize_datetime(item.end_at)
    if start_at <= current < end_at:
        return "IN_PROGRESS"
    return "UPCOMING"


def validate_time_range(start_at: datetime, end_at: datetime) -> tuple[datetime, datetime]:
    normalized_start = normalize_datetime(start_at)
    normalized_end = normalize_datetime(end_at)
    if normalized_end <= normalized_start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="End time must be after start time")
    return normalized_start, normalized_end


def validate_assignee(db: Session, project_id: UUID, assignee_user_id: UUID | None) -> None:
    if assignee_user_id is None:
        return
    exists = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == assignee_user_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Timeline assignee must be an event member")


def get_timeline_item_or_404(db: Session, project_id: UUID, item_id: UUID) -> ProjectTimelineItem:
    item = db.query(ProjectTimelineItem).filter(ProjectTimelineItem.project_id == project_id, ProjectTimelineItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline item not found")
    return item


def assignee_map(db: Session, items: list[ProjectTimelineItem]) -> dict[UUID, User]:
    assignee_ids = {item.assignee_user_id for item in items if item.assignee_user_id}
    if not assignee_ids:
        return {}
    return {user.id: user for user in db.query(User).filter(User.id.in_(assignee_ids)).all()}


def active_items_for_conflicts(db: Session, project_id: UUID) -> list[ProjectTimelineItem]:
    return db.query(ProjectTimelineItem).filter(ProjectTimelineItem.project_id == project_id, ProjectTimelineItem.status != "CANCELLED").all()


def find_conflicts_for_item(item: ProjectTimelineItem, candidates: list[ProjectTimelineItem]) -> list[ProjectTimelineItem]:
    if item.status == "CANCELLED":
        return []
    conflicts: list[ProjectTimelineItem] = []
    item_start = normalize_datetime(item.start_at)
    item_end = normalize_datetime(item.end_at)
    for candidate in candidates:
        if candidate.id == item.id or candidate.status == "CANCELLED":
            continue
        candidate_start = normalize_datetime(candidate.start_at)
        candidate_end = normalize_datetime(candidate.end_at)
        if item_start < candidate_end and candidate_start < item_end:
            conflicts.append(candidate)
    return sorted(conflicts, key=lambda current: (current.start_at, current.sort_order, current.title))


def serialize_conflict(item: ProjectTimelineItem) -> TimelineConflictRead:
    return TimelineConflictRead(id=item.id, title=item.title, start_at=item.start_at, end_at=item.end_at)


def serialize_timeline_item(item: ProjectTimelineItem, users: dict[UUID, User] | None = None, conflicts: list[ProjectTimelineItem] | None = None) -> TimelineItemRead:
    user = users.get(item.assignee_user_id) if users and item.assignee_user_id else None
    start_at = normalize_datetime(item.start_at)
    end_at = normalize_datetime(item.end_at)
    item_conflicts = conflicts or []
    return TimelineItemRead(
        id=item.id,
        project_id=item.project_id,
        title=item.title,
        description=item.description,
        category=item.category,
        start_at=item.start_at,
        end_at=item.end_at,
        location=item.location,
        assignee_user_id=item.assignee_user_id,
        assignee_name=user.name if user else None,
        assignee_email=user.email if user else None,
        created_by_user_id=item.created_by_user_id,
        status=effective_status(item),
        stored_status=item.status,
        notes=item.notes,
        sort_order=item.sort_order,
        created_at=item.created_at,
        updated_at=item.updated_at,
        duration_minutes=max(round((end_at - start_at).total_seconds() / 60), 0),
        has_conflict=bool(item_conflicts),
        conflicts=[serialize_conflict(conflict) for conflict in item_conflicts],
    )


def day_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    return start, end


def overlaps_date(item: ProjectTimelineItem, target_date: date) -> bool:
    start, end = day_bounds(target_date)
    return normalize_datetime(item.start_at) <= end and normalize_datetime(item.end_at) >= start


def list_project_timeline_items(
    db: Session,
    project_id: UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    assignee: UUID | None = None,
    target_date: date | None = None,
    upcoming: bool = False,
    today: bool = False,
    completed: bool = False,
    conflicts_only: bool = False,
    limit: int = 150,
    offset: int = 0,
) -> list[ProjectTimelineItem]:
    query = db.query(ProjectTimelineItem).filter(ProjectTimelineItem.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(ProjectTimelineItem.title.ilike(pattern), ProjectTimelineItem.description.ilike(pattern), ProjectTimelineItem.location.ilike(pattern), ProjectTimelineItem.notes.ilike(pattern)))
    if category:
        query = query.filter(ProjectTimelineItem.category == category.upper())
    if assignee:
        query = query.filter(ProjectTimelineItem.assignee_user_id == assignee)

    items = query.order_by(ProjectTimelineItem.start_at.asc(), ProjectTimelineItem.sort_order.asc(), ProjectTimelineItem.title.asc()).all()
    current = now_utc()
    if today:
        target_date = current.date()
    if target_date:
        items = [item for item in items if overlaps_date(item, target_date)]
    if status_filter:
        normalized = status_filter.upper()
        items = [item for item in items if effective_status(item, current_time=current) == normalized]
    if upcoming:
        items = [item for item in items if effective_status(item, current_time=current) == "UPCOMING" and normalize_datetime(item.start_at) >= current]
    if completed:
        items = [item for item in items if effective_status(item, current_time=current) == "COMPLETED"]
    if conflicts_only:
        candidates = active_items_for_conflicts(db, project_id)
        items = [item for item in items if find_conflicts_for_item(item, candidates)]
    start = max(offset, 0)
    end = start + min(max(limit, 1), 250)
    return items[start:end]


def create_project_timeline_item(db: Session, project_id: UUID, payload: TimelineItemCreate, *, created_by_user_id: UUID) -> ProjectTimelineItem:
    validate_assignee(db, project_id, payload.assignee_user_id)
    start_at, end_at = validate_time_range(payload.start_at, payload.end_at)
    item = ProjectTimelineItem(
        project_id=project_id,
        title=payload.title.strip(),
        description=clean_optional(payload.description),
        category=payload.category,
        start_at=start_at,
        end_at=end_at,
        location=clean_optional(payload.location),
        assignee_user_id=payload.assignee_user_id,
        created_by_user_id=created_by_user_id,
        status=payload.status,
        notes=clean_optional(payload.notes),
        sort_order=payload.sort_order,
    )
    db.add(item)
    db.flush()
    return item


def update_project_timeline_item(db: Session, item: ProjectTimelineItem, payload: TimelineItemUpdate) -> ProjectTimelineItem:
    updates = payload.model_dump(exclude_unset=True)
    if "assignee_user_id" in updates:
        validate_assignee(db, item.project_id, updates["assignee_user_id"])
    for field in {"title", "category", "status"}:
        if field in updates and updates[field] is not None:
            updates[field] = str(updates[field]).strip().upper() if field in {"category", "status"} else str(updates[field]).strip()
    for field in {"description", "location", "notes"}:
        if field in updates:
            updates[field] = clean_optional(updates[field])

    start_at = updates.get("start_at", item.start_at)
    end_at = updates.get("end_at", item.end_at)
    normalized_start, normalized_end = validate_time_range(start_at, end_at)
    updates["start_at"] = normalized_start
    updates["end_at"] = normalized_end

    for field, value in updates.items():
        setattr(item, field, value)
    item.updated_at = now_utc()
    db.flush()
    return item


def timeline_summary_item(item: ProjectTimelineItem, users: dict[UUID, User]) -> TimelineSummaryItem:
    user = users.get(item.assignee_user_id) if item.assignee_user_id else None
    return TimelineSummaryItem(
        id=item.id,
        title=item.title,
        category=item.category,
        start_at=item.start_at,
        end_at=item.end_at,
        location=item.location,
        assignee_name=user.name if user else None,
        status=effective_status(item),
    )


def timeline_summary(db: Session, project_id: UUID) -> TimelineSummary:
    items = db.query(ProjectTimelineItem).filter(ProjectTimelineItem.project_id == project_id).order_by(ProjectTimelineItem.start_at.asc(), ProjectTimelineItem.sort_order.asc()).all()
    current = now_utc()
    statuses = [effective_status(item, current_time=current) for item in items]
    active_items = [item for item in items if item.status != "CANCELLED"]
    conflict_ids: set[UUID] = set()
    for item in active_items:
        if find_conflicts_for_item(item, active_items):
            conflict_ids.add(item.id)
    current_items = [item for item in active_items if effective_status(item, current_time=current) == "IN_PROGRESS"]
    upcoming_items = [item for item in active_items if effective_status(item, current_time=current) == "UPCOMING" and normalize_datetime(item.start_at) >= current]
    users = assignee_map(db, [*current_items[:1], *upcoming_items[:1]])
    return TimelineSummary(
        project_id=project_id,
        total=len(items),
        upcoming=sum(1 for status_value in statuses if status_value == "UPCOMING"),
        completed=sum(1 for status_value in statuses if status_value == "COMPLETED"),
        cancelled=sum(1 for status_value in statuses if status_value == "CANCELLED"),
        today=sum(1 for item in items if overlaps_date(item, current.date())),
        in_progress=sum(1 for status_value in statuses if status_value == "IN_PROGRESS"),
        conflicts=len(conflict_ids),
        current_item=timeline_summary_item(current_items[0], users) if current_items else None,
        next_item=timeline_summary_item(upcoming_items[0], users) if upcoming_items else None,
        next_upcoming_at=upcoming_items[0].start_at if upcoming_items else None,
    )
