from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl


class TestimonialCreate(BaseModel):
    type: str
    url: HttpUrl
    caption: str | None = None


class TestimonialUpdate(BaseModel):
    type: str | None = None
    url: HttpUrl | None = None
    caption: str | None = None


class TestimonialRead(BaseModel):
    id: UUID
    project_id: UUID
    type: str
    url: str
    caption: str | None = None

    model_config = ConfigDict(from_attributes=True)
