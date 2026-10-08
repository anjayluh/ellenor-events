from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Integer, func, or_
from sqlalchemy.orm import Session

from app.api.dependencies import membership_role
from app.core.permissions import DOCUMENTS_MANAGE_PERMISSION, PROJECT_ADMIN_ROLES, ProjectRole, require_permission
from app.models.document import ProjectDocument
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.document import DocumentCategory, DocumentMetadataUpdate, DocumentSummary

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "image/jpeg",
    "image/png",
    "image/webp",
}
DOCUMENT_VIEW_ROLES = {ProjectRole.OWNER, ProjectRole.PARTNER, ProjectRole.COMMITTEE_CHAIR, ProjectRole.COMMITTEE_MEMBER, ProjectRole.FAMILY_VIEWER}


def require_document_viewer(membership: ProjectMember) -> None:
    if membership_role(membership) not in DOCUMENT_VIEW_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Documents are not available for this project role")


def require_document_manager(membership: ProjectMember) -> None:
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, DOCUMENTS_MANAGE_PERMISSION)


def project_document_or_404(db: Session, project_id: UUID, document_id: UUID) -> ProjectDocument:
    document = db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id, ProjectDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def safe_filename(filename: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return name[:180] or "document"


def validate_file(filename: str | None, mime_type: str | None, content: bytes, max_size: int) -> tuple[str, str]:
    if not filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A filename is required")
    if not mime_type or mime_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="This file type is not supported")
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded file is empty")
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The file exceeds the configured size limit")
    return safe_filename(filename), mime_type.lower()


def list_documents(db: Session, project_id: UUID, *, include_archived: bool, search: str | None, category: str | None, uploader_id: UUID | None) -> list[ProjectDocument]:
    query = db.query(ProjectDocument).filter(ProjectDocument.project_id == project_id)
    if not include_archived:
        query = query.filter(ProjectDocument.is_archived.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(ProjectDocument.original_filename.ilike(pattern), ProjectDocument.description.ilike(pattern)))
    if category:
        try:
            normalized_category = DocumentCategory(category.strip().upper())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported document category") from exc
        query = query.filter(ProjectDocument.category == normalized_category.value)
    if uploader_id:
        query = query.filter(ProjectDocument.uploaded_by_user_id == uploader_id)
    return query.order_by(ProjectDocument.created_at.desc()).all()


def document_summary(db: Session, project_id: UUID) -> DocumentSummary:
    total, archived, size = db.query(
        func.count(ProjectDocument.id),
        func.sum(func.cast(ProjectDocument.is_archived, Integer)),
        func.coalesce(func.sum(ProjectDocument.file_size_bytes), 0),
    ).filter(ProjectDocument.project_id == project_id).one()
    total_count = int(total or 0)
    archived_count = int(archived or 0)
    return DocumentSummary(project_id=project_id, total=total_count, active=total_count - archived_count, archived=archived_count, total_size_bytes=int(size or 0))


def apply_metadata_update(document: ProjectDocument, payload: DocumentMetadataUpdate) -> ProjectDocument:
    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates and updates["category"] is not None:
        updates["category"] = str(updates["category"])
    if "description" in updates and updates["description"] is not None:
        updates["description"] = updates["description"].strip() or None
    for field, value in updates.items():
        setattr(document, field, value)
    document.updated_at = datetime.now(timezone.utc)
    return document
