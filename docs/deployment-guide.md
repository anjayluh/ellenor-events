# Deployment Guide

This guide prepares Ellenor Events Coordination System for Supabase plus Vercel Services. The repository contains two deployable services in one GitHub repository: `frontend/` for Next.js and `backend/` for FastAPI. For end-to-end QA, account setup, sample inputs, and phase-by-phase checks, see `docs/qa-deployment-runbook.md`.

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

## 2. Vercel Services

The root `vercel.json` defines two Vercel Services:

| Service | Root | Framework | Entrypoint |
| --- | --- | --- | --- |
| `frontend` | `frontend/` | Next.js | Detected from `frontend/package.json` |
| `backend` | `backend/` | FastAPI | `app.main:app` |

Top-level rewrites route backend API paths to the `backend` service and all other paths to the `frontend` service. Browser API calls are same-origin by default in production, so `NEXT_PUBLIC_API_BASE_URL` should be left unset unless intentionally pointing at a separate backend.

## 3. Vercel Dashboard Settings

1. Import the GitHub repository once as a Vercel project.
2. Set the Framework Preset to `Services`.
3. Keep the project root at the repository root. Do not set the Root Directory to `frontend/` or `backend/`.
4. Use Node.js `20.19.0` or another compatible Node 20 runtime for the frontend service.
5. Add the environment variables below to Production and Preview unless noted otherwise.
6. Deploy after the environment variables are present.

## 4. Required Vercel Environment Variables

| Key | Environments | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | Production, Preview | Set to `production` for production and `preview` or `staging` for previews. |
| `DATABASE_POOLER_URL` | Production, Preview | Preferred Supabase pooled Postgres URL for serverless connections. |
| `DATABASE_URL` | Production, Preview | Supabase direct Postgres URL fallback if the pooler URL is unavailable. |
| `POSTGRES_PRISMA_URL` / `POSTGRES_URL` / `POSTGRES_URL_NON_POOLING` / `SUPABASE_DB_URL` | Production, Preview | Optional deployment-provider aliases. The backend accepts these only as fallbacks when `DATABASE_POOLER_URL` or an explicit `DATABASE_URL` is not configured. |
| `AUTH_PROVIDER` | Production, Preview | Use `supabase`. |
| `SUPABASE_URL` | Production, Preview | Supabase project URL used for Auth and JWT verification. |
| `SUPABASE_ANON_KEY` | Production, Preview | Supabase public anon key used by backend auth flows. |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production, Preview | Optional public aliases. The backend accepts these as fallbacks only when `SUPABASE_URL` / `SUPABASE_ANON_KEY` are not configured. |
| `SUPABASE_SERVICE_ROLE_KEY` | Production, Preview | Server-only Supabase service key for admin auth operations such as password reset confirmation. |
| `SUPABASE_JWT_SECRET` | Production, Preview | Supabase JWT secret for HS256 token verification fallback. |
| `JWT_SECRET` | Production, Preview | Local signing fallback; use the Supabase JWT secret or another strong secret. |
| `JWT_ALGORITHM` | Production, Preview | Use `HS256` unless the auth strategy changes. |
| `FRONTEND_URL` | Production, Preview | Canonical Vercel deployment URL for links and CORS allow-listing. |
| `CORS_ORIGINS` | Production, Preview | Comma-separated production and preview frontend origins, if cross-origin access is needed. |
| `EMAIL_PROVIDER` | Production, Preview | Use `resend` when email notifications are enabled. |
| `RESEND_API_KEY` | Production, Preview | Required only when sending email through Resend. |
| `RESEND_FROM_EMAIL` | Production, Preview | Verified sender identity, for example `Ellenor Events <noreply@your-domain.com>`. |
| `WHATSAPP_MODE` | Production, Preview | Use `manual_links` unless WhatsApp Cloud API sending is enabled. |
| `WHATSAPP_CLOUD_API_TOKEN` | Production, Preview | Optional until WhatsApp Cloud API sending is enabled. |
| `WHATSAPP_PHONE_NUMBER_ID` | Production, Preview | Optional until WhatsApp Cloud API sending is enabled. |
| `NOTIFICATION_MAX_ATTEMPTS` | Production, Preview | Notification retry limit. |
| `PAYMENT_PROVIDER` | Production, Preview | Use `mock` only for controlled preview/QA without real money. Use `flutterwave` when Flutterwave credentials are ready. |
| `FLUTTERWAVE_SECRET_KEY` | Production, Preview | Required only when `PAYMENT_PROVIDER=flutterwave`; keep server-only. |
| `FLUTTERWAVE_PUBLIC_KEY` | Production, Preview | Flutterwave public key, used for provider setup/reference. |
| `FLUTTERWAVE_WEBHOOK_SECRET` | Production, Preview | Required to verify Flutterwave webhook authenticity. |
| `FLUTTERWAVE_BASE_URL` | Production, Preview | Usually `https://api.flutterwave.com/v3`. |
| `BILLING_CHECKOUT_REDIRECT_URL` | Production, Preview | Frontend return URL after provider checkout, for example `<FRONTEND_URL>/billing`. |
| `NEXT_PUBLIC_API_BASE_URL` | Usually unset | Leave unset for Vercel Services same-origin routing. Set only if intentionally calling a separate backend origin. |

Do not add `.env.local`, `backend/.env`, or any local secret files to Git.

For Vercel deployments, configure one server-side database URL for the backend service. Prefer `DATABASE_POOLER_URL`; if Vercel or Supabase integration exposes a different Postgres variable name, the backend also recognizes `POSTGRES_PRISMA_URL`, `POSTGRES_URL`, `POSTGRES_URL_NON_POOLING`, and `SUPABASE_DB_URL` as non-public fallbacks.

## 5. Billing Provider Setup

Use `PAYMENT_PROVIDER=mock` for controlled QA before the Flutterwave account is ready. The mock provider still uses the normal checkout, webhook, payment verification, subscription, entitlement, and event-access flow; it must not be used when `ENVIRONMENT=production`.

To activate Flutterwave later:

1. Create the Ellenor Events Flutterwave account.
2. Obtain Flutterwave test credentials first, then live credentials only when ready.
3. Set the backend webhook URL to `/billing/webhooks/flutterwave`.
4. Configure the Flutterwave webhook secret and set `FLUTTERWAVE_WEBHOOK_SECRET`.
5. Set `BILLING_CHECKOUT_REDIRECT_URL` to the deployed billing page.
6. Set `PAYMENT_PROVIDER=flutterwave`.
7. Deploy or restart the backend.
8. Run a controlled test transaction and verify subscription/entitlement activation.
9. Switch to live credentials only after the controlled test succeeds.

## 6. CORS

With Vercel Services, frontend requests use the same deployment origin and are routed internally to the backend service. Keep `FRONTEND_URL` set to the canonical app URL and use `CORS_ORIGINS` for any additional preview/custom domains that need direct browser access to backend routes.

Local development still uses `http://localhost:3000` for the frontend and `http://127.0.0.1:8000` for the backend.

## 7. Operations

- GitHub Actions `CI` runs backend tests and frontend lint/typecheck/smoke/build.
- GitHub Actions `Uptime` pings the production health endpoint every 30 minutes when repository variable `PRODUCTION_API_HEALTH_URL` is configured.
- Use Supabase logs as the MVP audit/operations fallback before adding a dedicated analytics product.
- Keep production secrets in Vercel environment variables and Supabase settings only.

## 8. Release Smoke Test

Run these checks after each production deploy:

```bash
curl --fail "$PRODUCTION_APP_URL/health"
cd frontend && npm run smoke
```

Then manually verify:

- Email/password login succeeds for a confirmed Supabase user.
- Project list loads for an authenticated user.
- Admin navigation appears only for Ellenor Events admin users.
- Invite link opens and accepted invites cannot be reused.
- Budget visibility differs correctly for full, summary, contribution-only, and no-access members.
