# Ellenor Events Coordination System (EECS)

Production-ready MVP scaffold for a multi-tenant event coordination platform for weddings and introduction ceremonies in African contexts, with Uganda-first assumptions.

## Core Principles

- Email/password authentication through Supabase Auth for the MVP, with email-based notifications by default.
- Roles are project-scoped in `project_members`, never on `users`.
- Participants are not users; guests, family members, and vendors can exist without accounts.
- Every tenant query is scoped by `project_id`.
- Budget access is enforced server-side through role and visibility mode checks.
- WhatsApp-first communication with email fallback.
- MVP stores media URLs only; no internal file storage.

## Monorepo Structure

```text
backend/     FastAPI API, RBAC, SQLAlchemy models, Pydantic contracts
frontend/    Next.js starter client/staff portal UI
supabase/    Postgres schema and RLS-ready constraints
docs/        System design, API spec, UI wireframes
.github/     CI and uptime workflows
```

## Open in VS Code

```bash
code /Users/Angella/Desktop/ellenor-events
```

## Backend Quick Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs: <http://127.0.0.1:8000/docs>

## Frontend Quick Start

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:3000>

## MVP Defaults To Confirm

- WhatsApp strategy: manual link-based messages first, Cloud API later.
- Payments: contribution tracking only, mobile money later.
- Budget editing: owner/partner edit; committee chair can propose changes later.
- Linked events: separate project records with linked views.
- RSVP: optional in MVP, tracked where provided.


## Supabase Local/Hosted Schema

Apply migrations in order from `supabase/migrations/`, then load `supabase/seed.sql` for demo wedding/introduction data.

```bash
psql "$DATABASE_URL" -f supabase/migrations/202607030001_initial_schema.sql
psql "$DATABASE_URL" -f supabase/migrations/202607030002_rls_policies.sql
psql "$DATABASE_URL" -f supabase/seed.sql
```


## Authentication Strategy

Authentication uses Supabase Auth. The backend accepts verified Supabase bearer tokens, maps token subjects to global `users`, and validates project membership before returning private data.

Do not rely on `X-User-Id` in production. It is disabled by default and only available if `ALLOW_DEV_AUTH_HEADERS=true` for local debugging.


## Deployment

Deployment is configured for Supabase + Render + Vercel. See `docs/deployment-guide.md` for the full production checklist.

- Backend: `render.yaml` + `backend/Dockerfile`
- Frontend: `frontend/vercel.json`
- Monitoring: `.github/workflows/uptime.yml` with `PRODUCTION_API_HEALTH_URL` repository variable


## Contributor Guides

- Contributor onboarding: `CONTRIBUTING.md`
- Backend setup/testing: `backend/README.md`
- Frontend setup/testing: `frontend/README.md`
- Supabase migrations/seed data: `supabase/README.md`
- Full QA and deployment runbook: `docs/qa-deployment-runbook.md`
- Remote Supabase configuration: `docs/remote-supabase.md`
- Deployment checklist: `docs/deployment-guide.md`
- Security checklist: `docs/security-checklist.md`
