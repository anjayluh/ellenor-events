from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_project_membership
from app.core.config import settings
from app.db.session import get_db
from app.models.document import ProjectDocument
from app.schemas.document import DocumentCategory, DocumentMetadataUpdate, DocumentSignedUrl, DocumentSummary, ProjectDocumentRead
from app.services.document_storage import DocumentStorageError, storage_client
from app.services.project_document_service import (
    apply_metadata_update,
    document_summary,
    list_documents,
    project_document_or_404,
    require_document_manager,
    require_document_viewer,
    validate_file,
)

router = APIRouter()


def serialize(document: ProjectDocument) -> ProjectDocumentRead:
    return ProjectDocumentRead.model_validate(document)


@router.get("", response_model=list[ProjectDocumentRead])
def get_documents(
    project_id: UUID,
    include_archived: bool = False,
    search: str | None = None,
    category: str | None = None,
    uploader_id: UUID | None = None,
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_document_viewer(membership)
    return [serialize(document) for document in list_documents(db, project_id, include_archived=include_archived, search=search, category=category, uploader_id=uploader_id)]


@router.get("/summary", response_model=DocumentSummary)
def get_document_summary(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_viewer(membership)
    return document_summary(db, project_id)


@router.post("", response_model=ProjectDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    category: DocumentCategory = Form(DocumentCategory.OTHER),
    description: str | None = Form(default=None),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_document_manager(membership)
    content = await file.read(settings.document_max_file_size_bytes + 1)
    safe_name, mime_type = validate_file(file.filename, file.content_type, content, settings.document_max_file_size_bytes)
    document = ProjectDocument(
        id=uuid4(),
        project_id=project_id,
        uploaded_by_user_id=membership.user_id,
        original_filename=(file.filename or safe_name)[:255],
        storage_path=f"projects/{project_id}/documents/{{document_id}}/{safe_name}",
        mime_type=mime_type,
        file_size_bytes=len(content),
        category=category.value,
        description=description.strip() if description and description.strip() else None,
    )
    document.storage_path = document.storage_path.format(document_id=document.id)
    try:
        storage_client.upload(document.storage_path, content, mime_type)
    except DocumentStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    db.add(document)
    try:
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        try:
            storage_client.delete(document.storage_path)
        except DocumentStorageError:
            pass
        raise
    return serialize(document)


@router.get("/{document_id}", response_model=ProjectDocumentRead)
def get_document(project_id: UUID, document_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_viewer(membership)
    return serialize(project_document_or_404(db, project_id, document_id))


@router.get("/{document_id}/url", response_model=DocumentSignedUrl)
def get_document_url(project_id: UUID, document_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_viewer(membership)
    document = project_document_or_404(db, project_id, document_id)
    try:
        url = storage_client.sign(document.storage_path, settings.document_signed_url_expire_seconds)
    except DocumentStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return DocumentSignedUrl(url=url, expires_in=settings.document_signed_url_expire_seconds)


@router.patch("/{document_id}", response_model=ProjectDocumentRead)
def update_document(project_id: UUID, document_id: UUID, payload: DocumentMetadataUpdate, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_manager(membership)
    document = project_document_or_404(db, project_id, document_id)
    apply_metadata_update(document, payload)
    db.commit()
    db.refresh(document)
    return serialize(document)


@router.post("/{document_id}/archive", response_model=ProjectDocumentRead)
def archive_document(project_id: UUID, document_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_manager(membership)
    document = project_document_or_404(db, project_id, document_id)
    document.is_archived = True
    document.archived_at = datetime.now(timezone.utc)
    document.updated_at = document.archived_at
    db.commit()
    db.refresh(document)
    return serialize(document)


@router.post("/{document_id}/restore", response_model=ProjectDocumentRead)
def restore_document(project_id: UUID, document_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_manager(membership)
    document = project_document_or_404(db, project_id, document_id)
    document.is_archived = False
    document.archived_at = None
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return serialize(document)


@router.delete("/{document_id}")
def delete_document(project_id: UUID, document_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_document_manager(membership)
    document = project_document_or_404(db, project_id, document_id)
    document.is_archived = True
    document.archived_at = datetime.now(timezone.utc)
    document.updated_at = document.archived_at
    db.commit()
    return {"status": "archived"}
