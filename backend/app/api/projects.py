from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_role
from app.core.permissions import PROJECT_ADMIN_ROLES, PROJECT_OWNER_ROLES, require_role
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_settings import ProjectSettings
from app.schemas.project import ProjectCreate, ProjectRead, ProjectSettingsRead, ProjectSettingsUpdate, ProjectUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_or_create_settings(db: Session, project_id: UUID) -> ProjectSettings:
    settings = db.query(ProjectSettings).filter(ProjectSettings.project_id == project_id).first()
    if settings:
        return settings
    settings = ProjectSettings(project_id=project_id)
    db.add(settings)
    db.flush()
    return settings


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
    db.add(ProjectSettings(project_id=project.id))
    write_audit_log(db, "project.created", actor_user_id=current_user.id, project_id=project.id)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return get_project_or_404(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: UUID, payload: ProjectUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    project = get_project_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    write_audit_log(db, "project.updated", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/archive", response_model=ProjectRead)
def archive_project(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_OWNER_ROLES)
    project = get_project_or_404(db, project_id)
    project.status = "archived"
    write_audit_log(db, "project.archived", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/restore", response_model=ProjectRead)
def restore_project(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_OWNER_ROLES)
    project = get_project_or_404(db, project_id)
    project.status = "active"
    write_audit_log(db, "project.restored", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/settings", response_model=ProjectSettingsRead)
def get_project_settings(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    return get_or_create_settings(db, project_id)


@router.patch("/{project_id}/settings", response_model=ProjectSettingsRead)
def update_project_settings(project_id: UUID, payload: ProjectSettingsUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_role(membership_role(membership), PROJECT_ADMIN_ROLES)
    settings = get_or_create_settings(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    write_audit_log(db, "project.settings_updated", actor_user_id=membership.user_id, project_id=project_id)
    db.commit()
    db.refresh(settings)
    return settings
