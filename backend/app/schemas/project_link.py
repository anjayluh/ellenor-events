from uuid import UUID

from pydantic import BaseModel


class ProjectLinkCreate(BaseModel):
    linked_project_id: UUID
    relationship_type: str = "linked_ceremony"
    shared_committee: bool = False
    shared_budget: bool = False
    notes: str | None = None


class ProjectLinkRead(ProjectLinkCreate):
    id: UUID
    primary_project_id: UUID
