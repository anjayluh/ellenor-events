# QA and Deployment Runbook

This runbook tells a new contributor or project owner how to set up accounts, run the app, test every implemented phase, deploy the MVP, and find sample inputs already committed in the codebase.

## 1. Accounts and Sites to Create

| Purpose | Site | Required For | Notes |
| --- | --- | --- | --- |
| Source control and CI | https://github.com | Repository, GitHub Actions, repository variables | Repo: `anjayluh/ellenor-events`. Add collaborators with least privilege. |
| Database and Auth | https://supabase.com | Postgres, RLS, hosted auth, logs | Create one project for production and one optional project for staging/QA. |
| Backend hosting | https://render.com | FastAPI Docker web service | Use the root `render.yaml` Blueprint. |
| Frontend hosting | https://vercel.com | Next.js frontend | Import the repo with root directory `frontend`. |
| Email fallback | https://resend.com | Email invite/notification fallback | Needs API key and verified sending domain before production email. |
| WhatsApp sending later | https://developers.facebook.com | WhatsApp Cloud API | Manual WhatsApp links work without this; Cloud API requires a Meta app and phone number ID. |
| Domain/DNS optional | Your DNS provider | Custom frontend/API/email domains | Needed for branded URLs and verified email sender domain. |
| Error/analytics optional | Supabase logs first, PostHog later | MVP observability | Phase 12 uses Supabase logs fallback and GitHub uptime checks. |

## 2. Local Development Setup

### Prerequisites

- Python 3.12+; the current local machine has Python 3.13 working with tests.
- Node.js `20.19.0`; `.node-version` pins this version.
- npm.
- PostgreSQL/Supabase URL when testing against a real database.
- VS Code or another IDE.

### Clone and Open

```bash
git clone https://github.com/anjayluh/ellenor-events.git
cd ellenor-events
code .
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Useful local URLs:

- API health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: http://localhost:3000

## 3. Environment Variables

### Backend

Copy `backend/.env.example` to `backend/.env` for local development.

| Variable | Local Example | Production Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Use `production` in Render. |
| `DATABASE_URL` | `postgresql+psycopg://...` | Use Supabase pooled Postgres URL. |
| `JWT_SECRET` | local secret | Use Supabase JWT secret or a strong production signing secret. |
| `FRONTEND_URL` | `http://localhost:3000` | Canonical Vercel production URL. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated production and preview frontend origins. |
| `ALLOW_DEV_AUTH_HEADERS` | `false` | Keep `false` in production. |
| `RESEND_API_KEY` | blank locally | Required for real email fallback. |
| `RESEND_FROM_EMAIL` | demo sender | Must be a verified sender in Resend. |
| `WHATSAPP_MODE` | `manual_links` | Keep manual for MVP unless Cloud API is enabled. |
| `WHATSAPP_CLOUD_API_TOKEN` | blank locally | Required only for Cloud API direct sending. |
| `WHATSAPP_PHONE_NUMBER_ID` | blank locally | Required only for Cloud API direct sending. |

### Frontend

Set in Vercel and optional local `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Production value should be the Render API base URL, for example `https://ellenor-events-api.onrender.com`.

## 4. Database Setup

### Hosted Supabase

1. Create a Supabase project.
2. Copy the Postgres connection string.
3. Convert it to SQLAlchemy format by using `postgresql+psycopg://`.
4. Apply migrations in order:

```bash
for file in supabase/migrations/*.sql; do
  psql "$DATABASE_URL" -f "$file"
done
```

5. Load demo seed data only for development/staging, not production pilots:

```bash
psql "$DATABASE_URL" -f supabase/seed.sql
```

6. Confirm RLS policies are enabled for project-owned tables.

### Sample Seed Records

Defined in `supabase/seed.sql`:

| Record | Value |
| --- | --- |
| Owner user | `Amina Owner`, `+256700000101`, `amina@example.com` |
| Partner user | `David Partner`, `+256700000102`, `david@example.com` |
| Chair user | `Grace Chair`, `+256700000103`, `grace@example.com` |
| Viewer user | `Sarah Viewer`, `+256700000104`, `sarah@example.com` |
| Introduction project | `10000000-0000-0000-0000-000000000001` |
| Wedding project | `10000000-0000-0000-0000-000000000002` |
| Owner role | `OWNER`, `FULL_ACCESS` |
| Chair role | `COMMITTEE_CHAIR`, `SUMMARY_ACCESS` |
| Family viewer role | `FAMILY_VIEWER`, `CONTRIBUTION_ONLY` |

Frontend views must use authenticated API responses only; the old demo fixture files were removed.

## 5. Running Automated QA

Run from a clean checkout before opening a PR or deploying.

### Backend Unit and API Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Current expected result: all backend tests pass.

Coverage areas:

- JWT/token security.
- Auth denial for missing/tampered tokens.
- Project scoping and cross-project denial.
- Member role transitions and last-owner lockout.
- Invite token open/accept/reuse/expiry handling.
- Meeting creation/list/RSVP flow.
- Budget visibility shaping.
- Operations/staff metrics.
- Notification payload and retry service behavior.
- CORS origin parsing.

### Frontend Checks

```bash
cd frontend
npm run lint
npm run typecheck
npm run smoke
npm run build
```

`npm run smoke` checks core route files, portal navigation labels, API bearer support, API base URL wiring, and browser session persistence helpers.

### Config Checks

```bash
python3 -m json.tool frontend/vercel.json >/tmp/vercel-json-ok.txt
ruby -e 'require "yaml"; YAML.load_file("render.yaml"); YAML.load_file(".github/workflows/uptime.yml")'
git diff --check
```

## 6. Manual QA by Phase

Use seeded IDs and API docs at `/docs` for exact schema examples. For protected endpoints, authenticate first and send `Authorization: Bearer <token>`.

### Phase 1 — Architecture and Domain Schema

- Apply every migration in `supabase/migrations/` to a blank database.
- Confirm core tables exist: `users`, `projects`, `project_members`, `participants`, `vendors`, `invites`, `meetings`, `budgets`, `contributions`, `staff_members`, `notifications`.
- Confirm linked ceremonies exist in `project_links` for the seeded introduction/wedding pair.
- Confirm RLS policies exist for project-owned tables.

### Phase 2 — Authentication and User Identity

Sample login request:

```json
{
  "email": "anjayluh.wakabi@gmail.com",
  "password": "<tester-password>"
}
```

Expected QA:

- `POST /auth/login` signs in with Supabase Auth email/password.
- `POST /auth/register` creates an email/password account when signup is enabled.
- Missing/tampered bearer tokens return `401`.
- `X-User-Id` remains disabled unless `ALLOW_DEV_AUTH_HEADERS=true` locally.

### Phase 3 — Project, Membership, and RBAC

Sample project create:

```json
{
  "type": "wedding",
  "title": "QA Wedding - Test Couple",
  "event_date": "2026-12-12"
}
```

Expected QA:

- Creating a project creates an `OWNER` membership.
- `GET /projects` only returns projects where the user is a member.
- Non-members get `403` for another project.
- Demoting/removing the last owner returns `409`.

### Phase 4 — Invites and WhatsApp-First Onboarding

Sample invite create:

```json
{
  "project_id": "10000000-0000-0000-0000-000000000002",
  "contact": "+256700123456",
  "role_assigned": "COMMITTEE_MEMBER",
  "delivery_channel": "email"
}
```

Expected QA:

- Response includes an invite link and WhatsApp URL for manual sending.
- `GET /invites/{token}` increments opened count.
- `POST /invites/accept` creates/links a user and membership.
- Reusing an accepted token returns `409`.
- Expired/cancelled invites return `410`.

### Phase 5 — Meeting Coordination

Sample meeting create:

```json
{
  "type": "committee",
  "title": "Supplier Payment Review",
  "agenda": "Confirm catering deposit and decor balance",
  "scheduled_time": "2026-08-01T09:00:00+03:00"
}
```

Expected QA:

- Owner/partner/chair/member can create meetings.
- Members can list project meetings.
- RSVP upsert records current user status.
- Meeting changes prepare notification records.

### Phase 6 — Budget and Contributions

Sample budget update:

```json
{
  "total": 42000000,
  "spent": 7500000
}
```

Sample contribution:

```json
{
  "contributor": "Committee friends",
  "pledged": 12000000,
  "paid": 4500000,
  "status": "partial"
}
```

Expected QA:

- `FULL_ACCESS` sees total, spent, remaining, line items, and contributions.
- `SUMMARY_ACCESS` sees totals/progress but not spend, remaining, line items, or contribution rows.
- `CONTRIBUTION_ONLY` sees contribution progress only.
- `NO_ACCESS` receives `403`.
- Cross-project budget reads return `403`.

### Phase 7 — Operations Modules

Expected QA:

- Project-scoped task CRUD is role-gated.
- Vendor directory records do not require vendor user accounts.
- Testimonials store URL metadata only, not uploaded media blobs.
- Project queries remain scoped by `project_id`.

### Phase 8 — Client Portal

Expected QA:

- Frontend homepage shows only public product information until login.
- Login page signs in with Supabase email/password and disables submit until valid.
- Budget page loads live backend-shaped visibility data for the signed-in member.
- Invite route at `/invite/[token]` renders the acceptance path.

### Phase 9 — Staff Portal

Expected QA:

- Staff dashboard renders operational counts and risk alerts.
- Staff endpoints require active `staff_members` authorization.
- Non-staff authenticated project users cannot access staff endpoints.
- Seeded platform admin exists in `supabase/seed.sql`.

### Phase 10 — Notifications

Expected QA:

- Invite create/resend creates notification history records.
- Meeting create/update queues project notifications.
- Preferences endpoint reads and updates project notification settings.
- Retry endpoint increments attempts and respects max attempt tracking.
- Manual WhatsApp links remain the primary MVP path.

### Phase 11 — Testing, QA, and Security Hardening

Expected QA:

- Backend tests pass locally and in CI.
- Frontend lint/typecheck/smoke/build pass locally and in CI.
- Security checklist in `docs/security-checklist.md` is reviewed before deployment.
- Secrets are never committed; only examples are committed.

### Phase 12 — Deployment and Operations

Expected QA:

- Render Blueprint validates and creates the backend service.
- Vercel builds the `frontend` project with `NEXT_PUBLIC_API_BASE_URL` set.
- `GET /health` succeeds on the public backend URL.
- GitHub `Uptime` workflow succeeds after `PRODUCTION_API_HEALTH_URL` is set.
- Production frontend origin is allowed through `FRONTEND_URL`/`CORS_ORIGINS`.

## 7. Deployment Steps

### Step 1 — Push Code

```bash
git status
git push origin main
```

### Step 2 — Supabase

```bash
supabase login
supabase link
supabase db push
```

If using demo data in staging:

```bash
supabase db push --include-seed
```

### Step 3 — Render Backend

1. Open Render.
2. Create a Blueprint from the GitHub repo.
3. Confirm `render.yaml` detects `ellenor-events-api`.
4. Enter all `sync: false` environment variables.
5. Deploy.
6. Confirm `https://<render-service>/health` returns JSON with `status: ok`.

### Step 4 — Vercel Frontend

1. Import the GitHub repo.
2. Set root directory to `frontend`.
3. Set `NEXT_PUBLIC_API_BASE_URL` to the Render backend base URL.
4. Deploy.
5. Open the Vercel app and walk through login, project list, invite, meetings, and budget pages.

### Step 5 — GitHub Uptime

1. In GitHub, open repository settings.
2. Add repository variable `PRODUCTION_API_HEALTH_URL`.
3. Value should be the full health endpoint URL, for example `https://ellenor-events-api.onrender.com/health`.
4. Run `.github/workflows/uptime.yml` manually once.

## 8. Release Exit Criteria

Do not call the deployment ready until all are true:

- Backend tests pass.
- Frontend lint/typecheck/smoke/build pass.
- Supabase migrations are applied in order.
- Production backend health endpoint is public.
- Production frontend can call production backend.
- Auth token flow works in production settings.
- Invite tokens cannot be reused.
- Budget visibility checks pass for all visibility modes.
- No real secrets are committed.
- `docs/security-checklist.md` is reviewed.
