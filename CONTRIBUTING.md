# Contributing to Ellenor Events

Project operating roles and engineering skill expectations live in `AGENTS.md`. Read them before making architecture, backend, frontend, database, security, QA, DevOps, or documentation changes.

Welcome. This project is a multi-tenant event coordination platform, so small changes can have tenant-isolation and privacy consequences. Keep work focused, tested, and documented.

## Repository Map

```text
backend/     FastAPI API, SQLAlchemy models, services, tests
frontend/    Next.js App Router UI and smoke checks
supabase/    Versioned SQL migrations and seed data
docs/        Engineering pack, API spec, deployment, QA, security docs
.github/     CI and uptime workflows
```

## Branch and Commit Style

- Work from `main` unless a maintainer asks for a feature branch.
- Keep commits phase- or feature-scoped.
- Use clear commit messages, for example `Complete Phase 12 deployment operations`.
- Do not commit `.env`, build output, `.venv`, `.next`, `node_modules`, or secrets.

## Non-Negotiable Rules

1. Every tenant-owned query must filter by `project_id`.
2. Roles live in `project_members`, never on `users`.
3. Participants/vendors are not users unless explicitly linked.
4. Budget visibility must be enforced by the backend before serialization.
5. Sensitive endpoints require bearer auth.
6. Invite tokens must be secure, expiring, and single-use.
7. Media is URL-only in the MVP.
8. Frontend role checks are UX only; backend RBAC is authority.
9. WhatsApp-first communication remains the MVP default.
10. Secrets live in environment variables only.

## Local Setup

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Required Checks Before PR or Commit

```bash
cd backend && source .venv/bin/activate && pytest
cd ../frontend && npm run lint && npm run typecheck && npm run smoke && npm run build
cd .. && git diff --check
```

## Adding Backend Features

- Add or update SQLAlchemy models in `backend/app/models`.
- Add or update Pydantic contracts in `backend/app/schemas`.
- Keep business rules in `backend/app/services` when possible.
- Keep routers thin and project-scoped in `backend/app/api`.
- Add tests in `backend/tests` for success, denial, and cross-project behavior.
- Add Supabase migrations for database changes.

## Adding Frontend Features

- Add route screens under `frontend/app`.
- Add reusable UI under `frontend/components`.
- Add shared types/API helpers under `frontend/lib`.
- Keep `npm run smoke` updated when routes or app shell assumptions change.

## Documentation Expectations

Update docs when behavior changes:

- `docs/api-spec.md` for endpoint changes.
- `docs/engineering-pack.md` for phase status and review notes.
- `docs/qa-deployment-runbook.md` for QA/deployment changes.
- `docs/security-checklist.md` for new security requirements.
