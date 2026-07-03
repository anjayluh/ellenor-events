from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import MEMBER_DELETE_ROLES, PROJECT_ADMIN_ROLES, ProjectRole, require_role
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.services.audit_service import write_audit_log
from app.services.rbac_service import ensure_not_last_owner_change, get_project_member_or_404

router = APIRouter()


@router.get("", response_model=list[MemberRead])
def list_members(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.post("", response_model=MemberRead)
def add_member(project_id: UUID, payload: MemberCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    member = ProjectMember(project_id=project_id, **payload.model_dump(mode="json"))
    db.add(member)
    write_audit_log(db, "project_member.added", actor_user_id=membership.user_id, project_id=project_id, metadata={"user_id": str(payload.user_id), "role": payload.role.value})
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(project_id: UUID, member_id: UUID, payload: MemberUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    member = get_project_member_or_404(db, project_id, member_id)
    next_role = payload.role if payload.role is not None else ProjectRole(member.role)
    ensure_not_last_owner_change(db, member, next_role=next_role)

    for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(member, field, value)
    write_audit_log(db, "project_member.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"member_id": str(member_id)})
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}")
def remove_member(project_id: UUID, member_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), MEMBER_DELETE_ROLES)
    member = get_project_member_or_404(db, project_id, member_id)
    ensure_not_last_owner_change(db, member)
    db.delete(member)
    write_audit_log(db, "project_member.removed", actor_user_id=membership.user_id, project_id=project_id, metadata={"member_id": str(member_id)})
    db.commit()
    return {"status": "removed"}
