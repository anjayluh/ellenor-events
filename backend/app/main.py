from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, budget, invites, meetings, members, participants, projects, staff, tasks, testimonials, vendors
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multi-tenant event coordination API for weddings and introduction ceremonies.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(members.router, prefix="/projects/{project_id}/members", tags=["members"])
app.include_router(participants.router, prefix="/projects/{project_id}/participants", tags=["participants"])
app.include_router(tasks.router, prefix="/projects/{project_id}/tasks", tags=["tasks"])
app.include_router(vendors.router, prefix="/projects/{project_id}/vendors", tags=["vendors"])
app.include_router(testimonials.router, prefix="/projects/{project_id}/testimonials", tags=["testimonials"])
app.include_router(meetings.router, prefix="/projects/{project_id}/meetings", tags=["meetings"])
app.include_router(budget.router, prefix="/projects/{project_id}/budget", tags=["budget"])
app.include_router(invites.router, prefix="/invites", tags=["invites"])
app.include_router(staff.router, prefix="/staff", tags=["staff"])


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "eecs-api"}
