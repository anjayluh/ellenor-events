from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership, membership_role
from app.core.permissions import PROJECT_ADMIN_ROLES, require_role
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.schemas.member import MemberCreate, MemberRead

router = APIRouter()


@router.get("", response_model=list[MemberRead])
def list_members(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.post("", response_model=MemberRead)
def add_member(project_id: UUID, payload: MemberCreate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    member = ProjectMember(project_id=project_id, **payload.model_dump(mode="json"))
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
