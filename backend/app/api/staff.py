from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
def staff_dashboard():
    return {
        "active_projects": 0,
        "risk_alerts": [],
        "rsvp_summary": {"pending": 0, "accepted": 0, "declined": 0},
    }


@router.get("/projects")
def staff_projects():
    return []


@router.get("/analytics")
def staff_analytics():
    return {"message": "Analytics module is planned after MVP usage data exists."}
