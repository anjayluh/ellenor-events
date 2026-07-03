from uuid import UUID

from pydantic import BaseModel


class VendorCreate(BaseModel):
    name: str
    category: str
    contact: str | None = None
    status: str = "shortlisted"
    notes: str | None = None
    external_url: str | None = None


class VendorRead(VendorCreate):
    id: UUID
    project_id: UUID
