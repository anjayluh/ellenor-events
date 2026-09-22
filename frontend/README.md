# Frontend README

Next.js App Router frontend for Ellenor Events Coordination System.

## Responsibilities

- Client portal shell and dashboard.
- Login screen for Supabase email/password auth.
- Meeting, budget, committee, vendor, invite, and staff portal screens.
- API helper and local session persistence.
- Smoke checks for route and wiring assumptions.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Environment

Local development defaults to `http://127.0.0.1:8000` when `NEXT_PUBLIC_API_BASE_URL` is not set. Create `.env.local` only when overriding the backend URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

For Vercel Services, leave `NEXT_PUBLIC_API_BASE_URL` unset so browser requests use same-origin paths such as `/projects` and `/auth/login`.

## Checks

```bash
npm run lint
npm run typecheck
npm run smoke
npm run build
```

## Important Files

- `app/`: routes and pages.
- `components/`: reusable portal components.
- `lib/api.ts`: bearer-aware API helpers.
- `lib/session.ts`: browser session persistence.
- `scripts/smoke-test.mjs`: route/app-shell smoke checks.
- Root `../vercel.json`: Vercel Services deployment config.

## Deployment

Deploy from the repository root using Vercel Services. See `docs/deployment-guide.md`.
