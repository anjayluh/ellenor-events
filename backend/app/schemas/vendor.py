from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VendorCreate(BaseModel):
    name: str
    category: str
    contact: str | None = None
    status: str = "shortlisted"
    notes: str | None = None
    external_url: str | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    contact: str | None = None
    status: str | None = None
    notes: str | None = None
    external_url: str | None = None


class VendorRead(VendorCreate):
    id: UUID
    project_id: UUID

    model_config = ConfigDict(from_attributes=True)
