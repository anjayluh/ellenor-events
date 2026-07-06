# Frontend README

Next.js App Router frontend for Ellenor Events Coordination System.

## Responsibilities

- Client portal shell and dashboard.
- Login screen for passwordless auth.
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

Create `.env.local` when calling a real backend:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Production value should be the Render backend base URL.

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
- `lib/demo-data.ts`: client portal demo data.
- `lib/staff-demo.ts`: staff dashboard demo data.
- `scripts/smoke-test.mjs`: route/app-shell smoke checks.
- `vercel.json`: Vercel deployment config.

## Deployment

Import the repo in Vercel with root directory `frontend`, set `NEXT_PUBLIC_API_BASE_URL`, and deploy. See `docs/deployment-guide.md`.
