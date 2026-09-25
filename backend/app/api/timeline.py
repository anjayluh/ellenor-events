from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership
from app.db.session import get_db
from app.schemas.task import TaskAssigneeRead
from app.schemas.timeline import TimelineItemCreate, TimelineItemRead, TimelineItemUpdate, TimelineSummary
from app.services.project_task_service import list_task_assignees
from app.services.audit_service import write_audit_log
from app.services.project_timeline_service import (
    active_items_for_conflicts,
    assignee_map,
    create_project_timeline_item,
    find_conflicts_for_item,
    get_timeline_item_or_404,
    list_project_timeline_items,
    require_timeline_manager,
    serialize_timeline_item,
    timeline_summary,
    update_project_timeline_item,
)

router = APIRouter()


@router.get("", response_model=list[TimelineItemRead])
def list_timeline_items(
    project_id: UUID,
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    assignee: UUID | None = None,
    date_filter: date | None = Query(default=None, alias="date"),
    upcoming: bool = False,
    today: bool = False,
    completed: bool = False,
    conflicts: bool = False,
    limit: int = Query(default=150, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    items = list_project_timeline_items(
        db,
        project_id,
        search=search,
        category=category,
        status_filter=status_filter,
        assignee=assignee,
        target_date=date_filter,
        upcoming=upcoming,
        today=today,
        completed=completed,
        conflicts_only=conflicts,
        limit=limit,
        offset=offset,
    )
    users = assignee_map(db, items)
    candidates = active_items_for_conflicts(db, project_id)
    return [serialize_timeline_item(item, users, find_conflicts_for_item(item, candidates)) for item in items]


@router.get("/summary", response_model=TimelineSummary)
def get_timeline_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return timeline_summary(db, project_id)


@router.get("/assignees", response_model=list[TaskAssigneeRead])
def get_timeline_assignees(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return list_task_assignees(db, project_id)


@router.post("", response_model=TimelineItemRead)
def create_timeline_item(project_id: UUID, payload: TimelineItemCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_timeline_manager(membership)
    item = create_project_timeline_item(db, project_id, payload, created_by_user_id=membership.user_id)
    write_audit_log(db, "timeline.item_created", actor_user_id=membership.user_id, project_id=project_id, metadata={"item_id": str(item.id)})
    db.commit()
    db.refresh(item)
    return serialize_timeline_item(item, assignee_map(db, [item]), find_conflicts_for_item(item, active_items_for_conflicts(db, project_id)))


@router.get("/{item_id}", response_model=TimelineItemRead)
def get_timeline_item(project_id: UUID, item_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    item = get_timeline_item_or_404(db, project_id, item_id)
    return serialize_timeline_item(item, assignee_map(db, [item]), find_conflicts_for_item(item, active_items_for_conflicts(db, project_id)))


@router.patch("/{item_id}", response_model=TimelineItemRead)
def update_timeline_item(project_id: UUID, item_id: UUID, payload: TimelineItemUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_timeline_manager(membership)
    item = get_timeline_item_or_404(db, project_id, item_id)
    update_project_timeline_item(db, item, payload)
    write_audit_log(db, "timeline.item_updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"item_id": str(item_id)})
    db.commit()
    db.refresh(item)
    return serialize_timeline_item(item, assignee_map(db, [item]), find_conflicts_for_item(item, active_items_for_conflicts(db, project_id)))


@router.delete("/{item_id}")
def delete_timeline_item(project_id: UUID, item_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_timeline_manager(membership)
    item = get_timeline_item_or_404(db, project_id, item_id)
    db.delete(item)
    write_audit_log(db, "timeline.item_deleted", actor_user_id=membership.user_id, project_id=project_id, metadata={"item_id": str(item_id)})
    db.commit()
    return {"status": "deleted"}
