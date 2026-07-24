from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import COMMITTEE_MANAGE_PERMISSION, MEMBER_DELETE_ROLES, PROJECT_ADMIN_ROLES, ProjectRole, normalize_permissions, require_permission
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.services.audit_service import write_audit_log
from app.services.rbac_service import ensure_not_last_owner_change, get_project_member_or_404

router = APIRouter()


def serialize_member(member: ProjectMember) -> MemberRead:
    return MemberRead(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        role=ProjectRole(member.role),
        budget_visibility_mode=member.budget_visibility_mode,
        permissions_level=member.permissions_level,
        permissions=sorted(normalize_permissions(getattr(member, "permissions_json", None))),
    )


@router.get("", response_model=list[MemberRead])
def list_members(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return [serialize_member(member) for member in db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()]


@router.post("", response_model=MemberRead)
def add_member(project_id: UUID, payload: MemberCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, COMMITTEE_MANAGE_PERMISSION)
    payload_data = payload.model_dump(mode="json")
    permissions = payload_data.pop("permissions", [])
    member = ProjectMember(project_id=project_id, **payload_data, permissions_json={"permissions": sorted(normalize_permissions(permissions))})
    db.add(member)
    write_audit_log(db, "project_member.added", actor_user_id=membership.user_id, project_id=project_id, metadata={"user_id": str(payload.user_id), "role": payload.role.value})
    db.commit()
    db.refresh(member)
    return serialize_member(member)


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(project_id: UUID, member_id: UUID, payload: MemberUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, COMMITTEE_MANAGE_PERMISSION)
    member = get_project_member_or_404(db, project_id, member_id)
    next_role = payload.role if payload.role is not None else ProjectRole(member.role)
    ensure_not_last_owner_change(db, member, next_role=next_role)

    updates = payload.model_dump(exclude_unset=True, mode="json")
    if "permissions" in updates:
        member.permissions_json = {"permissions": sorted(normalize_permissions(updates.pop("permissions")))}
    for field, value in updates.items():
        setattr(member, field, value)
    write_audit_log(db, "project_member.updated", actor_user_id=membership.user_id, project_id=project_id, metadata={"member_id": str(member_id)})
    db.commit()
    db.refresh(member)
    return serialize_member(member)


@router.delete("/{member_id}")
def remove_member(project_id: UUID, member_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), MEMBER_DELETE_ROLES, COMMITTEE_MANAGE_PERMISSION)
    member = get_project_member_or_404(db, project_id, member_id)
    ensure_not_last_owner_change(db, member)
    db.delete(member)
    write_audit_log(db, "project_member.removed", actor_user_id=membership.user_id, project_id=project_id, metadata={"member_id": str(member_id)})
    db.commit()
    return {"status": "removed"}
