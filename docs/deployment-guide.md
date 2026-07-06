# Deployment Guide

This guide deploys Ellenor Events Coordination System with free-tier-friendly services: Supabase for Postgres/Auth, Render for the FastAPI backend, and Vercel for the Next.js frontend. For end-to-end QA, account setup, sample inputs, and phase-by-phase checks, see `docs/qa-deployment-runbook.md`.

## 1. Supabase

1. Create a Supabase project.
2. Copy the pooled Postgres connection string and use the SQLAlchemy driver format: `postgresql+psycopg://...`.
3. Apply migrations in order from the repository root:

```bash
for file in supabase/migrations/*.sql; do
  psql "$DATABASE_URL" -f "$file"
done
```

4. Optional demo data for non-production environments:

```bash
psql "$DATABASE_URL" -f supabase/seed.sql
```

5. Confirm RLS is enabled and policies exist for project-owned tables before exposing real data.

## 2. Backend on Render

The root `render.yaml` defines the backend web service from `backend/Dockerfile`. Connect the GitHub repo in Render and create a Blueprint from `render.yaml`.

Required environment variables:

| Key | Notes |
| --- | --- |
| `DATABASE_URL` | Supabase Postgres URL using `postgresql+psycopg://` |
| `JWT_SECRET` | Supabase JWT secret or platform-issued signing secret |
| `ENVIRONMENT` | `production` |
| `FRONTEND_URL` | Canonical Vercel app URL |
| `CORS_ORIGINS` | Comma-separated production and preview frontend URLs |
| `RESEND_API_KEY` | Required when email fallback is enabled |
| `RESEND_FROM_EMAIL` | Verified sender identity |
| `WHATSAPP_CLOUD_API_TOKEN` | Optional until Cloud API sending is enabled |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional until Cloud API sending is enabled |

Health check path: `/health`.

## 3. Frontend on Vercel

1. Import the GitHub repository in Vercel.
2. Set the project root directory to `frontend`.
3. Keep Node.js at `20.19.0` or newer compatible Node 20.
4. Set environment variables:

| Key | Notes |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Render backend URL, for example `https://ellenor-events-api.onrender.com` |

5. Deploy and confirm the frontend can call `GET /health` on the backend.

## 4. CORS

The backend reads `FRONTEND_URL` plus optional comma-separated `CORS_ORIGINS`. Use this for production plus Vercel preview URLs when needed. Example:

```env
FRONTEND_URL=https://ellenor-events.vercel.app
CORS_ORIGINS=https://ellenor-events.vercel.app,https://ellenor-events-git-main.vercel.app
```

## 5. Operations

- GitHub Actions `CI` runs backend tests and frontend lint/typecheck/smoke/build.
- GitHub Actions `Uptime` pings the production health endpoint every 30 minutes when repository variable `PRODUCTION_API_HEALTH_URL` is configured.
- Use Supabase logs as the MVP audit/operations fallback before adding a dedicated analytics product.
- Keep `.env` files local only; production secrets live in Supabase, Render, Vercel, or GitHub repository variables/secrets.

## 6. Release Smoke Test

Run these checks after each production deploy:

```bash
curl --fail "$PRODUCTION_API_BASE_URL/health"
cd frontend && npm run smoke
```

Then manually verify:

- Passwordless login challenge starts successfully.
- Project list loads for an authenticated user.
- Invite link opens and accepted invites cannot be reused.
- Budget visibility differs correctly for full, summary, contribution-only, and no-access members.
