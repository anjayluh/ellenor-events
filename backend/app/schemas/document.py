from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentCategory(StrEnum):
    INVITATION = "INVITATION"
    CONTRACT = "CONTRACT"
    QUOTATION = "QUOTATION"
    INVOICE = "INVOICE"
    RECEIPT = "RECEIPT"
    VENUE = "VENUE"
    PLANNING = "PLANNING"
    FAMILY = "FAMILY"
    COMMITTEE = "COMMITTEE"
    OTHER = "OTHER"


class DocumentMetadataUpdate(BaseModel):
    category: DocumentCategory | None = None
    description: str | None = Field(default=None, max_length=500)


class ProjectDocumentRead(BaseModel):
    id: UUID
    project_id: UUID
    uploaded_by_user_id: UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    category: DocumentCategory
    description: str | None = None
    is_archived: bool
    archived_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentSignedUrl(BaseModel):
    url: str
    expires_in: int


class DocumentSummary(BaseModel):
    project_id: UUID
    total: int
    active: int
    archived: int
    total_size_bytes: int
