from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter()


@router.get("", response_model=list[ProjectRead])
def list_projects(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    )


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    project = Project(**payload.model_dump(), owner_user_id=current_user.id)
    db.add(project)
    db.flush()
    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role="OWNER",
            permissions_level="admin",
            budget_visibility_mode="FULL_ACCESS",
        )
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.id == project_id).one()
