from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership
from app.db.session import get_db
from app.schemas.task import TaskAssigneeRead, TaskCreate, TaskRead, TaskSummary, TaskUpdate
from app.services.audit_service import write_audit_log
from app.services.project_task_service import (
    create_project_task,
    get_task_or_404,
    list_project_tasks,
    list_task_assignees,
    require_task_manager,
    serialize_task,
    task_summary,
    update_project_task,
)

router = APIRouter()


@router.get("", response_model=list[TaskRead])
def list_tasks(
    project_id: UUID,
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    category: str | None = None,
    assignee: UUID | None = None,
    assigned_to: UUID | None = None,
    overdue: bool | None = None,
    due_soon: bool | None = None,
    my_tasks: bool = False,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    effective_assignee = assignee or assigned_to
    tasks = list_project_tasks(
        db,
        project_id,
        current_user_id=membership.user_id,
        search=search,
        status_filter=status_filter,
        priority=priority,
        category=category,
        assignee=effective_assignee,
        overdue=overdue,
        due_soon=due_soon,
        my_tasks=my_tasks,
        limit=limit,
        offset=offset,
    )
    from app.services.project_task_service import assignee_map

    users = assignee_map(db, tasks)
    return [serialize_task(task, users) for task in tasks]


@router.get("/summary", response_model=TaskSummary)
def get_task_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return task_summary(db, project_id, current_user_id=membership.user_id)


@router.get("/assignees", response_model=list[TaskAssigneeRead])
def get_task_assignees(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return list_task_assignees(db, project_id)


@router.post("", response_model=TaskRead)
def create_task(project_id: UUID, payload: TaskCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_task_manager(membership)
    task = create_project_task(db, project_id, payload, created_by_user_id=membership.user_id)
    write_audit_log(db, "task.created", actor_user_id=membership.user_id, project_id=project_id, metadata={"task_id": str(task.id)})
    db.commit()
    db.refresh(task)
    return serialize_task(task, {})


@router.get("/{task_id}", response_model=TaskRead)
def get_task(project_id: UUID, task_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    task = get_task_or_404(db, project_id, task_id)
    from app.services.project_task_service import assignee_map

    return serialize_task(task, assignee_map(db, [task]))


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(project_id: UUID, task_id: UUID, payload: TaskUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    task = get_task_or_404(db, project_id, task_id)
    update_project_task(db, task, payload, membership)
    write_audit_log(db, "task.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"task_id": str(task_id)})
    db.commit()
    db.refresh(task)
    from app.services.project_task_service import assignee_map

    return serialize_task(task, assignee_map(db, [task]))


@router.delete("/{task_id}")
def delete_task(project_id: UUID, task_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_task_manager(membership)
    task = get_task_or_404(db, project_id, task_id)
    db.delete(task)
    write_audit_log(db, "task.deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"task_id": str(task_id)})
    db.commit()
    return {"status": "deleted"}
