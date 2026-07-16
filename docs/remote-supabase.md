# Remote Supabase Configuration

The project is configured to use the remote Supabase project as the database and authentication provider. Do not use local Supabase for this project unless a maintainer explicitly creates a separate local-only task.

## Secret Handling

- Keep `.env.local` untracked. It is ignored by `.gitignore` through `.env.*`.
- Do not commit Supabase keys, database URLs, JWT secrets, or service-role credentials.
- Rotate any key that was pasted into chat, logs, screenshots, or shared documents.

Required local/deployment variables:

```env
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
DATABASE_POOLER_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_JWT_SECRET=<jwt-secret>
AUTH_PROVIDER=supabase
ENVIRONMENT=production
TESTER_EMAIL=<confirmed-qa-user-email>
TESTER_PASSWORD=<confirmed-qa-user-password>
```

The backend normalizes `postgresql://` to `postgresql+psycopg://` internally for SQLAlchemy. Use `DATABASE_POOLER_URL` for local QA when direct Supabase Postgres is unreachable over IPv6.

## Migration Status

Remote migrations were applied with Supabase CLI using `supabase db push --db-url <DATABASE_URL>`. The remote migration history contains these project migrations:

- `202607030001_initial_schema.sql`
- `202607030002_rls_policies.sql`
- `202607030003_auth_hardening.sql`
- `202607030004_project_rbac_core.sql`
- `202607030005_invite_onboarding.sql`
- `202607030006_meetings_coordination.sql`
- `202607030007_budget_contributions.sql`
- `202607030008_staff_portal.sql`
- `202607030009_notifications.sql`
- `202607140001_supabase_auth_profiles.sql`
- `202607150001_email_auth_and_notifications.sql`
- `202607150002_email_defaults_hardening.sql`
- `202607150003_authenticated_rls_runtime.sql`
- `202607150004_notification_insert_policy.sql`
- `202607150005_notification_creation_function.sql`

## Auth Mapping

Supabase Auth is the source of authenticated identities. `public.users` is the application profile table. Migration `202607140001_supabase_auth_profiles.sql` adds a trigger on `auth.users` so Supabase users are synced into `public.users` with the same UUID.

The backend accepts Supabase JWTs by validating HMAC signatures with `SUPABASE_JWT_SECRET`. For production, it also checks the issuer is `<SUPABASE_URL>/auth/v1`.

For SQLAlchemy requests, the backend sets these PostgreSQL request claims before tenant-scoped queries:

- `request.jwt.claim.sub`
- `request.jwt.claim.role`

Protected requests also assume the `authenticated` database role and reset it when the request session closes. This keeps database helper functions such as `public.is_project_member()` and `public.has_project_role()` aligned with Supabase JWT identity context instead of relying on the pooler’s privileged `postgres` role.

Service-only writes use narrow security-definer functions:

- `public.write_audit_log(...)`
- `public.create_notification(...)`

These functions validate project role context before writing service tables that are otherwise protected by RLS.

## Verification Performed

- Supabase CLI dry run listed all migrations in order.
- Supabase CLI successfully applied all migrations to the remote database.
- Seed data loaded successfully with `psql`.
- Remote database counts were verified for users, projects, project members, notification preferences, migration history, helper functions, and the auth sync trigger.
- Supabase REST anon access to `projects` returned zero rows, confirming project data is not exposed anonymously.
- Backend database connectivity was verified against the remote Supabase Postgres database.
- FastAPI Supabase Auth integration path was verified with mocked Auth responses.

Live `/auth/login` now uses Supabase email/password. To test end-to-end, create or confirm the tester account in Supabase Auth and provide the tester password through `.env.local` or the dashboard. If login returns `Email address is not confirmed`, confirm the tester email in Supabase Auth before rerunning QA.

## Useful Commands

Dry-run migrations:

```bash
supabase db push --db-url "$DATABASE_URL" --dry-run
```

Apply migrations:

```bash
supabase db push --db-url "$DATABASE_URL" --yes
```

Apply migrations through the pooler:

```bash
supabase db push --db-url "$DATABASE_POOLER_URL" --yes
```

Load seed data:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/seed.sql
```

Verify core counts:

```bash
psql "$DATABASE_URL" -c "select count(*) from public.projects;"
```
