# Backend README

FastAPI service for Ellenor Events Coordination System.

## Responsibilities

- Passwordless auth challenge and token verification.
- Project-scoped RBAC and membership enforcement.
- Invites, meetings, tasks, vendors, testimonials, budgets, contributions, notifications, and staff APIs.
- Backend-side budget visibility shaping.
- Audit logging for sensitive flows.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Environment

Start from `.env.example`. Important values:

- `DATABASE_URL`: SQLAlchemy database URL.
- `JWT_SECRET`: local or production signing secret.
- `FRONTEND_URL`: canonical frontend URL.
- `CORS_ORIGINS`: optional comma-separated extra frontend origins.
- `ALLOW_DEV_AUTH_HEADERS`: keep `false` except intentional local debugging.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Expected current result: `42 passed`.

## API Docs

Run the service and open:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

## Test Structure

- `tests/test_security.py`: token/CORS security.
- `tests/test_api_phase11.py`: API flow and tenant-isolation coverage.
- `tests/test_budget_visibility.py`: budget response shaping.
- `tests/test_invite_service.py`: invite token/service behavior.
- `tests/test_meeting_service.py`: RSVP behavior.
- `tests/test_notification_service.py`: notification payload/retry behavior.
- `tests/test_staff_service.py`: staff portal metrics and authorization.

## Deployment

The backend deploys from `backend/Dockerfile` through the root `render.yaml` Blueprint. See `docs/deployment-guide.md` and `docs/qa-deployment-runbook.md`.
