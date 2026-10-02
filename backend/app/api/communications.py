from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership
from app.db.session import get_db
from app.schemas.communication import CommunicationCreate, CommunicationRead, CommunicationSummary, CommunicationUpdate
from app.services.audit_service import write_audit_log
from app.services.communication_service import (
    archive_communication,
    communication_summary,
    create_communication,
    get_communication_or_404,
    list_visible_communications,
    mark_communication_read,
    require_communication_manager,
    serialize_communication,
    set_pinned,
    update_communication,
)

router = APIRouter()


@router.get("", response_model=list[CommunicationRead])
def list_communications(
    project_id: UUID,
    search: str | None = None,
    communication_type: str | None = Query(default=None, alias="type"),
    priority: str | None = None,
    author_user_id: UUID | None = None,
    status_filter: str = Query(default="ACTIVE", alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    rows = list_visible_communications(db, project_id, membership.user_id, search=search, communication_type=communication_type, priority=priority, author_user_id=author_user_id, status_filter=status_filter, limit=limit, offset=offset)
    return [serialize_communication(db, row, membership.user_id) for row in rows]


@router.get("/summary", response_model=CommunicationSummary)
def get_communication_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return communication_summary(db, project_id, membership.user_id)


@router.post("", response_model=CommunicationRead)
def create_project_communication(project_id: UUID, payload: CommunicationCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_communication_manager(membership)
    communication = create_communication(db, project_id, membership.user_id, payload)
    write_audit_log(db, "communication.created", actor_user_id=membership.user_id, project_id=project_id, metadata={"communication_id": str(communication.id), "type": communication.communication_type})
    db.commit()
    db.refresh(communication)
    return serialize_communication(db, communication, membership.user_id)


@router.get("/{communication_id}", response_model=CommunicationRead)
def get_project_communication(project_id: UUID, communication_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    communication = get_communication_or_404(db, project_id, communication_id, membership.user_id)
    return serialize_communication(db, communication, membership.user_id)


@router.patch("/{communication_id}", response_model=CommunicationRead)
def edit_project_communication(project_id: UUID, communication_id: UUID, payload: CommunicationUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_communication_manager(membership)
    communication = get_communication_or_404(db, project_id, communication_id)
    update_communication(db, communication, payload)
    write_audit_log(db, "communication.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"communication_id": str(communication.id)})
    db.commit()
    db.refresh(communication)
    return serialize_communication(db, communication, membership.user_id)


@router.post("/{communication_id}/pin", response_model=CommunicationRead)
def pin_project_communication(project_id: UUID, communication_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_communication_manager(membership)
    communication = get_communication_or_404(db, project_id, communication_id)
    set_pinned(communication, True)
    db.commit()
    db.refresh(communication)
    return serialize_communication(db, communication, membership.user_id)


@router.post("/{communication_id}/unpin", response_model=CommunicationRead)
def unpin_project_communication(project_id: UUID, communication_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_communication_manager(membership)
    communication = get_communication_or_404(db, project_id, communication_id)
    set_pinned(communication, False)
    db.commit()
    db.refresh(communication)
    return serialize_communication(db, communication, membership.user_id)


@router.post("/{communication_id}/archive", response_model=CommunicationRead)
def archive_project_communication(project_id: UUID, communication_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_communication_manager(membership)
    communication = get_communication_or_404(db, project_id, communication_id)
    archive_communication(communication)
    write_audit_log(db, "communication.archived", actor_user_id=membership.user_id, project_id=project_id, metadata={"communication_id": str(communication.id)})
    db.commit()
    db.refresh(communication)
    return serialize_communication(db, communication, membership.user_id)


@router.post("/{communication_id}/read", response_model=CommunicationRead)
def mark_project_communication_read(project_id: UUID, communication_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    communication = get_communication_or_404(db, project_id, communication_id, membership.user_id)
    mark_communication_read(db, communication, membership.user_id)
    db.commit()
    db.refresh(communication)
    return serialize_communication(db, communication, membership.user_id)
