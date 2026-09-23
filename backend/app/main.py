from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import admin, auth, billing, budget, catalog, customer_accounts, guest_invites, invites, meetings, members, notifications, participants, projects, staff, tasks, testimonials, vendor_portal, vendors
from app.core.config import settings
from app.db.session import SessionLocal

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multi-tenant event coordination API for weddings and introduction ceremonies.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
app.include_router(billing.router, prefix="/billing", tags=["billing"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(customer_accounts.router, prefix="/customer-accounts", tags=["customer-accounts"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(members.router, prefix="/projects/{project_id}/members", tags=["members"])
app.include_router(participants.router, prefix="/projects/{project_id}/participants", tags=["participants"])
app.include_router(guest_invites.router, prefix="/projects/{project_id}/guest-invites", tags=["guest-invites"])
app.include_router(guest_invites.public_router, prefix="/guest-invites", tags=["guest-invites"])
app.include_router(tasks.router, prefix="/projects/{project_id}/tasks", tags=["tasks"])
app.include_router(vendors.router, prefix="/projects/{project_id}/vendors", tags=["vendors"])
app.include_router(testimonials.router, prefix="/projects/{project_id}/testimonials", tags=["testimonials"])
app.include_router(meetings.router, prefix="/projects/{project_id}/meetings", tags=["meetings"])
app.include_router(notifications.router, prefix="/projects/{project_id}/notifications", tags=["notifications"])
app.include_router(budget.router, prefix="/projects/{project_id}/budget", tags=["budget"])
app.include_router(invites.router, prefix="/invites", tags=["invites"])
app.include_router(vendor_portal.router, prefix="/vendors", tags=["vendor-portal"])
app.include_router(staff.router, prefix="/staff", tags=["staff"])


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "eecs-api"}


@app.get("/health/readiness", tags=["system"])
def readiness_check():
    database_configured = settings.has_configured_database_url
    database_connected = False
    database_error = None
    if database_configured:
        try:
            with SessionLocal() as db:
                db.execute(text("select 1"))
            database_connected = True
        except SQLAlchemyError:
            database_error = "database_unavailable"

    supabase_auth_configured = settings.uses_remote_supabase_auth
    ready = database_connected and supabase_auth_configured
    payload = {
        "status": "ok" if ready else "degraded",
        "service": "eecs-api",
        "database_configured": database_configured,
        "database_connected": database_connected,
        "database_error": database_error,
        "supabase_auth_configured": supabase_auth_configured,
        "payment_provider": settings.payment_provider,
    }
    if ready:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
