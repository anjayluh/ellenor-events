# Security Checklist

Use this checklist before deploying Ellenor Events Coordination System and after any auth, invite, notification, or budget change.

## Authentication

- [x] Protected API routes require bearer tokens by default.
- [x] Development `X-User-Id` auth is gated by `ALLOW_DEV_AUTH_HEADERS` and must stay disabled in production.
- [x] JWTs are signed server-side and reject invalid signatures, missing claims, and expired tokens.
- [ ] Production auth provider keys are configured outside GitHub in deployment secrets.
- [ ] Supabase Auth email/password logs are monitored for abuse and unusual login attempts.

## Tenant Isolation and RBAC

- [x] Anonymous users see only public marketing/login surfaces.
- [x] Staff/admin navigation is not exposed in public navigation.
- [x] Project-owned reads and writes are filtered by `project_id`.
- [x] Non-members receive `403` for project, member, meeting, and budget APIs.
- [x] Project roles live in `project_members`, not global users.
- [x] Last-owner demotion/removal is blocked.
- [x] Supabase RLS policies are applied in production before public traffic.
- [x] Backend SQLAlchemy requests assume the Supabase `authenticated` database role before project-scoped queries.

## Budget Privacy

- [x] Full budget access is required for line-item details.
- [x] Summary access hides spend, remaining, line items, and contribution records.
- [x] Contribution-only access hides budget totals and spend.
- [x] No-access members cannot read budget responses.
- [ ] Real pilot data is reviewed for accidental sensitive notes in descriptions.

## Invites and Notifications

- [x] Invite tokens are generated with secure random values and stored server-side.
- [x] Expired, cancelled, and accepted invites cannot be accepted.
- [x] Invite reuse is rejected.
- [x] Notification payloads are stored as metadata, not provider secrets.
- [ ] Email provider tokens are configured only as environment variables when outbound email delivery is enabled.

## Headers, CORS, and Secrets

- [x] CORS is restricted to the configured frontend origin.
- [x] `.env` files are ignored; only `.env.example` is committed.
- [x] CI runs tests, lint, typecheck, frontend smoke checks, and production build.
- [ ] Production deployments add HSTS and proxy-level security headers.
- [ ] Rotate any token that was ever exposed during manual testing.
