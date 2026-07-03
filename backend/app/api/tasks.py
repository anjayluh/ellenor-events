from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import ProjectRole, require_role
from app.db.session import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()
TASK_WRITE_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR, ProjectRole.COMMITTEE_MEMBER}


def get_task_or_404(db: Session, project_id: UUID, task_id: UUID) -> Task:
    task = db.query(Task).filter(Task.project_id == project_id, Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(project_id: UUID, assigned_to: UUID | None = None, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    query = db.query(Task).filter(Task.project_id == project_id)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    return query.order_by(Task.due_date.asc().nullslast()).all()


@router.post("", response_model=TaskRead)
def create_task(project_id: UUID, payload: TaskCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), TASK_WRITE_ROLES)
    task = Task(project_id=project_id, **payload.model_dump())
    db.add(task)
    write_audit_log(db, "task.created", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(project_id: UUID, task_id: UUID, payload: TaskUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), TASK_WRITE_ROLES)
    task = get_task_or_404(db, project_id, task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    write_audit_log(db, "task.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"task_id": str(task_id)})
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(project_id: UUID, task_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), TASK_WRITE_ROLES)
    task = get_task_or_404(db, project_id, task_id)
    db.delete(task)
    write_audit_log(db, "task.deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"task_id": str(task_id)})
    db.commit()
    return {"status": "deleted"}
