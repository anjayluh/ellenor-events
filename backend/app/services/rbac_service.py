from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import ProjectRole
from app.models.project_member import ProjectMember


def count_project_owners(db: Session, project_id: UUID) -> int:
    return (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.role == ProjectRole.OWNER.value)
        .count()
    )


def ensure_not_last_owner_change(db: Session, member: ProjectMember, next_role: ProjectRole | None = None) -> None:
    is_owner_now = member.role == ProjectRole.OWNER.value
    remains_owner = next_role == ProjectRole.OWNER if next_role else False
    if is_owner_now and not remains_owner and count_project_owners(db, member.project_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove or demote the last project owner",
        )


def get_project_member_or_404(db: Session, project_id: UUID, member_id: UUID) -> ProjectMember:
    member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found")
    return member
