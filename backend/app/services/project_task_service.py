from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.permissions import PROJECT_ADMIN_ROLES, TASKS_MANAGE_PERMISSION, ProjectRole, has_permission
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskAssigneeRead, TaskCreate, TaskRead, TaskSummary, TaskUpdate

ASSIGNED_STATUS_ONLY_FIELDS = {"status"}


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_due_soon(due_date: date | None, task_status: str) -> bool:
    if not due_date or task_status == "DONE":
        return False
    current = today_utc()
    return current <= due_date <= current + timedelta(days=7)


def is_overdue(due_date: date | None, task_status: str) -> bool:
    return bool(due_date and due_date < today_utc() and task_status != "DONE")


def can_manage_tasks(membership: ProjectMember) -> bool:
    role = ProjectRole(membership.role)
    return role in PROJECT_ADMIN_ROLES or has_permission(role, getattr(membership, "permissions_json", None), TASKS_MANAGE_PERMISSION)


def can_assignee_update_status(membership: ProjectMember, task: Task) -> bool:
    role = ProjectRole(membership.role)
    if role in {ProjectRole.FAMILY_VIEWER, ProjectRole.GUEST_VIEWER}:
        return False
    return task.assigned_to == membership.user_id


def require_task_manager(membership: ProjectMember) -> None:
    if can_manage_tasks(membership):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")


def validate_assignee(db: Session, project_id: UUID, assignee_user_id: UUID | None) -> None:
    if assignee_user_id is None:
        return
    exists = db.query(ProjectMember.id).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == assignee_user_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Task assignee must be an event member")


def get_task_or_404(db: Session, project_id: UUID, task_id: UUID) -> Task:
    task = db.query(Task).filter(Task.project_id == project_id, Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def assignee_map(db: Session, tasks: list[Task]) -> dict[UUID, User]:
    assignee_ids = {task.assigned_to for task in tasks if task.assigned_to}
    if not assignee_ids:
        return {}
    return {user.id: user for user in db.query(User).filter(User.id.in_(assignee_ids)).all()}


def serialize_task(task: Task, users: dict[UUID, User] | None = None) -> TaskRead:
    user = users.get(task.assigned_to) if users and task.assigned_to else None
    return TaskRead(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        assigned_to=task.assigned_to,
        assignee_name=user.name if user else None,
        assignee_email=user.email if user else None,
        created_by_user_id=task.created_by_user_id,
        status=task.status,
        priority=task.priority,
        category=task.category,
        due_date=task.due_date,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        is_overdue=is_overdue(task.due_date, task.status),
        is_due_soon=is_due_soon(task.due_date, task.status),
    )


def list_project_tasks(
    db: Session,
    project_id: UUID,
    *,
    current_user_id: UUID,
    search: str | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    assignee: UUID | None = None,
    overdue: bool | None = None,
    due_soon: bool | None = None,
    my_tasks: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Task]:
    query = db.query(Task).filter(Task.project_id == project_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority:
        query = query.filter(Task.priority == priority)
    if category:
        query = query.filter(Task.category == category)
    if assignee:
        query = query.filter(Task.assigned_to == assignee)
    if my_tasks:
        query = query.filter(Task.assigned_to == current_user_id)
    current = today_utc()
    if overdue is True:
        query = query.filter(Task.due_date.isnot(None), Task.due_date < current, Task.status != "DONE")
    if due_soon is True:
        query = query.filter(Task.due_date.isnot(None), Task.due_date >= current, Task.due_date <= current + timedelta(days=7), Task.status != "DONE")
    return query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 250)).all()


def create_project_task(db: Session, project_id: UUID, payload: TaskCreate, *, created_by_user_id: UUID) -> Task:
    validate_assignee(db, project_id, payload.assigned_to)
    task = Task(
        project_id=project_id,
        title=payload.title.strip(),
        description=clean_optional(payload.description),
        assigned_to=payload.assigned_to,
        created_by_user_id=created_by_user_id,
        status=payload.status,
        priority=payload.priority,
        category=payload.category,
        due_date=payload.due_date,
        completed_at=now_utc() if payload.status == "DONE" else None,
    )
    db.add(task)
    db.flush()
    return task


def update_project_task(db: Session, task: Task, payload: TaskUpdate, membership: ProjectMember) -> Task:
    updates = payload.model_dump(exclude_unset=True)
    if not can_manage_tasks(membership):
        if not can_assignee_update_status(membership, task) or set(updates) - ASSIGNED_STATUS_ONLY_FIELDS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient event permissions")
    if "assigned_to" in updates:
        validate_assignee(db, task.project_id, updates["assigned_to"])
    for field in {"title", "description"}:
        if field in updates:
            updates[field] = clean_optional(updates[field]) if field == "description" else str(updates[field]).strip()
    old_status = task.status
    for field, value in updates.items():
        setattr(task, field, value)
    if "status" in updates and updates["status"] != old_status:
        task.completed_at = now_utc() if updates["status"] == "DONE" else None
    task.updated_at = now_utc()
    db.flush()
    return task


def task_summary(db: Session, project_id: UUID, *, current_user_id: UUID) -> TaskSummary:
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    total = len(tasks)
    completed = sum(1 for task in tasks if task.status == "DONE")
    in_progress = sum(1 for task in tasks if task.status == "IN_PROGRESS")
    todo = sum(1 for task in tasks if task.status == "TODO")
    overdue = sum(1 for task in tasks if is_overdue(task.due_date, task.status))
    due_soon = sum(1 for task in tasks if is_due_soon(task.due_date, task.status))
    my_tasks = sum(1 for task in tasks if task.assigned_to == current_user_id)
    completion_percentage = round((completed / total) * 100) if total else 0
    return TaskSummary(
        project_id=project_id,
        total=total,
        todo=todo,
        in_progress=in_progress,
        completed=completed,
        overdue=overdue,
        due_soon=due_soon,
        completion_percentage=completion_percentage,
        my_tasks=my_tasks,
    )


def list_task_assignees(db: Session, project_id: UUID) -> list[TaskAssigneeRead]:
    rows = db.query(ProjectMember, User).join(User, User.id == ProjectMember.user_id).filter(ProjectMember.project_id == project_id).order_by(User.name.asc().nullslast(), User.email.asc().nullslast()).all()
    return [TaskAssigneeRead(user_id=member.user_id, name=user.name, email=user.email, role=member.role) for member, user in rows]
