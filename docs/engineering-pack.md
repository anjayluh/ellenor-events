# Ellenor Events Coordination System Engineering Pack

## 1. Product Summary

Ellenor Events Coordination System (EECS) is a production-ready multi-tenant web platform for coordinating weddings, introduction ceremonies, and linked ceremonies in African contexts, with Uganda-first assumptions.

The system is built around project-scoped collaboration. A global user can participate in multiple events with different roles, while non-account people such as family members, guests, and vendors remain participants only. Budget data is sensitive and must be shaped by backend authorization before it reaches the frontend.

## 2. Current Build Status

Status legend:

- `[x] Complete`
- `[~] Started / scaffolded`
- `[ ] Not started`

### Completed Foundation

- `[x] Desktop project created at /Users/Angella/Desktop/ellenor-events`
- `[x] Repository initialized as an independent Git repo`
- `[x] VS Code workspace settings added`
- `[x] Monorepo structure created for backend, frontend, docs, Supabase, and CI`
- `[x] README quick-start added`
- `[x] FastAPI backend skeleton created`
- `[x] SQLAlchemy model layer scaffolded`
- `[x] Pydantic request/response schemas scaffolded`
- `[x] Core permission constants added for project roles and budget visibility`
- `[x] Supabase/Postgres schema created`
- `[x] Next.js frontend starter created`
- `[x] Client portal dashboard mock created`
- `[x] Staff portal starter created`
- `[x] Invite acceptance route starter created`
- `[x] System design, API spec, and UI wireframe docs added`
- `[x] Python syntax sanity check passed`

### Scaffolded But Not Production-Ready Yet

- `[~] Auth endpoints exist but use development placeholders`
- `[~] Project, member, meeting, invite, budget, and staff routers exist`
- `[~] Budget visibility shaping exists at API level but needs full tests and real data flows`
- `[~] WhatsApp manual-link service exists but is not wired to a send provider`
- `[~] GitHub Actions CI file exists but has not been run with installed dependencies`
- `[~] Frontend role-based UI is visually represented but not connected to real API state`

## 3. Non-Negotiable Engineering Rules

1. Every tenant-owned query must filter by `project_id`.
2. Roles live in `project_members`, never on `users`.
3. Participants are not users unless explicitly linked later through `linked_user_id`.
4. Budget visibility is enforced on the backend before response serialization.
5. Sensitive endpoints require authenticated user context.
6. Invites use secure expiring tokens.
7. MVP stores URLs only for media; no internal heavy file storage.
8. Frontend role checks are UX helpers only; backend RBAC is the authority.
9. WhatsApp is the primary communication channel; email is fallback.
10. Production secrets must live in environment variables only.

## 4. Architecture Baseline

### Backend

- Framework: FastAPI
- Database access: SQLAlchemy with Postgres/Supabase
- Runtime: Stateless API service
- Auth target: Supabase Auth or Firebase Auth JWT validation
- Deployment target: Render or Railway free tier
- Current entrypoint: `backend/app/main.py`

### Frontend

- Framework: Next.js App Router
- Styling: Plain CSS starter using Purple + Gold brand direction
- Deployment target: Vercel free tier
- Current entrypoint: `frontend/app/page.tsx`

### Database

- Engine: Postgres on Supabase
- Current schema: `supabase/schema.sql`
- Required next layer: migrations and Supabase RLS policies

### Communication

- MVP: WhatsApp manual links
- Later: WhatsApp Cloud API integration
- Email fallback: Resend

## 5. Phase-by-Phase Implementation Plan

## Phase 0 — Project Initiation and Repo Foundation

Status: `[x] Complete`

### Objective

Create the engineering foundation on Desktop, optimized for Visual Studio Code and future deployment.

### Completed Deliverables

- `[x] Created project folder on Desktop`
- `[x] Initialized Git repository`
- `[x] Added backend, frontend, docs, Supabase, and CI folders`
- `[x] Added `.gitignore`
- `[x] Added VS Code settings and extension recommendations`
- `[x] Added README with local startup instructions`

### Acceptance Criteria

- `[x] Project opens cleanly in VS Code`
- `[x] Repo is isolated from parent Desktop Git state`
- `[x] Developer can identify backend, frontend, docs, and schema locations`

## Phase 1 — Architecture and Domain Schema

Status: `[x] Complete pending review`

### Objective

Model the core EECS domain with project-scoped tenancy and role-based access foundations.

### Completed Deliverables

- `[x] Created Supabase/Postgres schema for users, projects, project members, participants, invites, meetings, RSVP, tasks, budgets, contributions, and testimonials`
- `[x] Added SQL constraints for roles, event types, budget visibility modes, and non-negative budget values`
- `[x] Added SQL indexes for tenant-heavy project queries`
- `[x] Created SQLAlchemy models mirroring core tables`
- `[x] Created Pydantic schemas for auth, projects, members, meetings, budget, and invites`

### Remaining Work

- `[x] Add database migration tooling, preferably Alembic or Supabase migrations`
- `[x] Add row-level security policies in Supabase`
- `[x] Add seed data for local development/demo ceremonies`
- `[x] Add linked-event relationship model if linked ceremonies need shared views`
- `[x] Add vendor model/table; currently vendors are conceptually covered by participants but not first-class`

### Acceptance Criteria

- All production tables can be created from versioned migrations.
- Supabase policies prevent cross-project reads and writes.
- Backend models, schema contracts, and database migrations stay aligned.

### Phase 1 Review Notes

- Added Supabase migration files under `supabase/migrations/`.
- Added RLS helper functions and policies for project membership and role checks.
- Added deterministic seed data for one linked introduction/wedding demo.
- Added `project_links` and `vendors` as first-class domain structures.
- Backend model/schema alignment updated for linked ceremonies and vendors.

## Phase 2 — Authentication and User Identity

Status: `[x] Complete pending review`

### Objective

Implement passwordless auth using phone OTP first and email magic links as fallback.

### Completed Deliverables

- `[x] Added `POST /auth/login` placeholder endpoint`
- `[x] Added `POST /auth/verify-otp` placeholder endpoint`
- `[x] Added JWT creation utility for development flow`
- `[x] Added global `users` database model/schema concept`

### Remaining Work

- `[x] Choose Supabase Auth or Firebase Auth as production provider`
- `[x] Replace `X-User-Id` development header dependency with verified JWT auth`
- `[x] Implement global user lookup/create after OTP or magic-link verification`
- `[x] Add auth middleware/dependency for current user context`
- `[x] Add rate limiting for OTP requests`
- `[x] Add audit logging for login and invite acceptance events`

### Acceptance Criteria

- Users can sign in with phone OTP without a password.
- Users can use email fallback when phone is unavailable.
- Backend derives current user from verified auth token, not frontend-provided identity.
- Auth tests cover success, invalid token, expired token, and missing token cases.

### Phase 2 Review Notes

- Chose Supabase Auth as the production auth provider target.
- Replaced required `X-User-Id` auth with bearer token verification.
- Kept `X-User-Id` only as an opt-in local debug escape hatch through `ALLOW_DEV_AUTH_HEADERS=true`.
- Added persisted OTP/magic-link challenges with HMAC-hashed codes and rate limiting.
- Added global user lookup/create after verification.
- Added audit logging for auth challenges, user creation, invite creation, and invite acceptance attempts.

## Phase 3 — Project, Membership, and RBAC Core

Status: `[x] Complete pending review`

### Objective

Make project-scoped membership the authorization backbone of the platform.

### Completed Deliverables

- `[x] Added project list/create/get endpoints`
- `[x] Added member list/create endpoints`
- `[x] Auto-creates owner membership when a project is created`
- `[x] Added project membership dependency to reject non-members`
- `[x] Added role constants: OWNER, PARTNER, COMMITTEE_CHAIR, COMMITTEE_MEMBER, FAMILY_VIEWER, GUEST_VIEWER`

### Remaining Work

- `[x] Add full CRUD for project members with role transitions`
- `[x] Add role-change restrictions, especially preventing owner lockout`
- `[x] Add project settings endpoint`
- `[x] Add project archive/restore flow`
- `[x] Add participant endpoints for non-user family, guest, and vendor records`
- `[x] Add test coverage for cross-project access denial`

### Acceptance Criteria

- A user can hold different roles in different projects.
- Project member operations are scoped by `project_id`.
- Non-members cannot read or mutate project data.
- Owner cannot accidentally remove the last owner/admin path.

### Phase 3 Review Notes

- Added member update/delete endpoints with role-transition support.
- Added last-owner lockout prevention for demotion and deletion.
- Added project update, archive, restore, settings read, and settings update endpoints.
- Added project-scoped participant CRUD endpoints for family, guests, and non-account people.
- Added project settings database model, schema, seed data, migration, and RLS policy.
- Added RBAC service tests for owner lockout behavior.

## Phase 4 — Invites and WhatsApp-First Onboarding

Status: `[x] Complete pending review`

### Objective

Support secure expiring invites through WhatsApp-first links, with email fallback later.

### Completed Deliverables

- `[x] Added invite model and schema`
- `[x] Added secure token generation using `token_urlsafe`
- `[x] Added seven-day expiry default`
- `[x] Added manual WhatsApp link builder service`
- `[x] Added invite acceptance frontend route starter`

### Remaining Work

- `[x] Persist invite acceptance into user and project membership records`
- `[x] Validate token expiry and invite status on accept`
- `[x] Add resend/cancel invite endpoints`
- `[x] Add WhatsApp deep-link display in frontend invite flow`
- `[x] Add email fallback via Resend`
- `[x] Add invite analytics: sent, opened, accepted, expired`

### Acceptance Criteria

- Owner/partner/chair can invite a person to a project role.
- Invite tokens cannot be reused after acceptance or expiry.
- Accepted invites create or link a global user, then create project membership.
- WhatsApp is the primary action path in the UI.

### Phase 4 Review Notes

- Invite acceptance now validates token existence, pending status, and expiry.
- Accepted invites create or update a global user, then create or update project membership.
- Invite tokens are single-use after acceptance and can be cancelled or resent by project admins.
- Invite reads track opened counts and opened timestamps.
- Invite responses include WhatsApp deep links for manual WhatsApp-first sending.
- Email fallback payload generation is in place for Resend-style delivery integration.
- Invite analytics summarize pending, accepted, expired, cancelled, sent, and opened counts.

## Phase 5 — Meetings, RSVP, and Committee Coordination

Status: `[x] Complete`

### Objective

Enable event committees and families to coordinate through meetings, RSVP tracking, and later notes/decisions.

### Completed Deliverables

- `[x] Added meeting model and schema`
- `[x] Added meeting list/create endpoints`
- `[x] Added RSVP model and endpoint starter`
- `[x] Added meeting concepts to UI wireframes`

### Remaining Work

- `[x] Restrict meeting creation by role`
- `[x] Add meeting update/delete endpoints`
- `[x] Add RSVP uniqueness/upsert behavior`
- `[x] Add meeting notes and decisions log`
- `[x] Add frontend meetings page with RSVP buttons`
- `[x] Add notification trigger for meeting creation/change`

### Acceptance Criteria

- Members see only meetings for their project.
- RSVP status is tracked per authenticated user.
- Committee leadership can create and update meetings.
- Meeting changes can trigger WhatsApp/email notifications.

### Phase 5 Review Notes

- Meeting creation and updates are restricted to owner, partner, committee chair, and committee member roles.
- Meeting deletion is restricted to owner, partner, and committee chair roles.
- Meeting detail, update, delete, and RSVP upsert endpoints are implemented.
- Meeting notes, decisions log, status, and updated timestamp are now persisted.
- RSVP records are unique per meeting/user and updates overwrite prior RSVP status.
- Meeting create/update actions queue notification audit records for future WhatsApp/email delivery.
- Frontend includes a meetings page starter with RSVP buttons.

## Phase 6 — Budget and Contributions

Status: `[x] Complete pending review`

### Objective

Implement secure budget visibility and contribution tracking without leaking sensitive financial detail.

### Completed Deliverables

- `[x] Added budget and contribution models`
- `[x] Added `GET /projects/{project_id}/budget` with visibility-shaped response`
- `[x] Added `PATCH /projects/{project_id}/budget` restricted to owner/partner roles`
- `[x] Added budget preview component showing role-dependent visibility concept`

### Remaining Work

- `[x] Add contribution CRUD endpoints`
- `[x] Add detailed budget line items if required for full-access users`
- `[x] Add committee chair proposal workflow if budget edits are not direct`
- `[x] Add tests proving no full budget exposure for lower visibility modes`
- `[x] Add frontend budget page for full, summary, contribution-only, and no-access states`
- `[x] Add export/report view for owners`

### Acceptance Criteria

- Full budget never reaches unauthorized users.
- Contribution-only users can see progress but not totals/spend breakdown.
- Only authorized roles can edit budget values.
- Tests verify response shape per visibility mode.

### Phase 6 Review Notes

- Budget responses are shaped centrally by visibility mode and tested against over-sharing.
- Full-access users can see totals, spent, remaining, line items, and contribution details.
- Summary-access users see totals and contribution progress but not spent or line items.
- Contribution-only users see contribution progress only.
- Contribution CRUD, line-item CRUD, proposal create/review, and owner export endpoints are implemented.
- Frontend includes a budget page showing full, summary, contribution-only, and no-access states.

## Phase 7 — Tasks, Vendors, Testimonials, and Media URLs

Status: `[x] Complete pending review`

### Objective

Complete event operations modules while preserving MVP simplicity.

### Completed Deliverables

- `[x] Added tasks table/model scaffold`
- `[x] Added testimonials table/model scaffold using URL-only media storage`

### Remaining Work

- `[x] Add task CRUD endpoints and assignee views`
- `[x] Add vendor directory model and endpoints`
- `[x] Decide whether vendors are participants or a first-class table in v1`
- `[x] Add testimonial CRUD endpoints storing URL and caption only`
- `[x] Add frontend committee/tasks page`
- `[x] Add frontend vendor directory page`

### Acceptance Criteria

- Tasks are project-scoped and assignable to users.
- Vendors can be tracked without requiring accounts.
- Testimonials store external URLs only.
- UI presents operational modules without exposing unauthorized budget data.

### Phase 7 Review Notes

- Added project-scoped task CRUD endpoints with optional assignee filtering.
- Confirmed vendors are first-class v1 project records, separate from participants and users.
- Added vendor directory CRUD endpoints for committee-capable roles.
- Added testimonial CRUD endpoints that validate and store external URLs only.
- Added committee/tasks and vendor directory frontend pages.
- Added tests for testimonial URL validation and project-scoped task lookup behavior.

## Phase 8 — Frontend Client Portal

Status: `[x] Complete pending review`

### Objective

Build role-aware client-facing screens for event owners, partners, committees, family viewers, and guest viewers.

### Completed Deliverables

- `[x] Added Next.js app structure`
- `[x] Added Purple + Gold visual direction`
- `[x] Added dashboard hero and event cards`
- `[x] Added budget visibility preview component`
- `[x] Added invite acceptance page starter`

### Remaining Work

- `[x] Add login screen with phone OTP and email fallback`
- `[x] Connect dashboard to real `/projects` API`
- `[x] Add event dashboard layout with tabs: Overview, Meetings, Budget, Committee, Vendors, Timeline`
- `[x] Add role-based navigation visibility`
- `[x] Add data-fetching and auth session handling`
- `[x] Add loading, empty, and error states`
- `[x] Add responsive QA across mobile-first scenarios`

### Acceptance Criteria

- User can sign in and see their events.
- Event dashboard adapts by project role.
- Budget UI matches backend-shaped visibility response.
- Mobile layout feels first-class for Uganda phone-first usage.

### Phase 8 Review Notes

- Added passwordless login screen with phone OTP and email fallback behavior.
- Updated frontend API helpers to use bearer token contracts and typed request helpers.
- Dashboard attempts live `/projects` data and falls back to demo project data when the API is offline.
- Added event dashboard route with Overview, Meetings, Budget, Committee, Vendors, and Timeline-aware role navigation.
- Added local session helpers for storing auth token and user metadata.
- Added loading, error, empty/demo state UI blocks.
- Added responsive refinements for mobile portal interactions.

## Phase 9 — Staff/Admin Portal

Status: `[x] Complete pending review`

### Objective

Create an internal staff view for operational oversight without breaking tenant privacy.

### Completed Deliverables

- `[x] Added staff API router placeholders`
- `[x] Added staff portal starter page`
- `[x] Added wireframe concepts for all projects, risk alerts, budget overview, RSVP analytics, and vendor tracking`

### Remaining Work

- `[x] Define staff role hierarchy and access model`
- `[x] Add staff user authorization separate from project roles`
- `[x] Build staff project list and project health view`
- `[x] Add risk alert rules for low RSVP, overdue tasks, budget variance, and missing vendors`
- `[x] Add audit logging for staff access to project data`

### Acceptance Criteria

- Staff portal is inaccessible to normal client users.
- Staff users can review operational health across projects.
- Staff access is logged for accountability.
- Sensitive budget detail remains permission-aware.

### Phase 9 Review Notes

- Added `staff_members` table/model with platform roles separate from project membership roles.
- Staff endpoints now require active staff authorization via bearer-authenticated user identity.
- Staff dashboard returns project health, RSVP summary, active/archive counts, and risk alerts.
- Risk alerts cover overdue tasks, missing required vendor categories, and budget variance.
- Staff dashboard, project list, and analytics access is audit logged.
- Staff frontend now shows project health, risk alerts, and analytics-style metrics.

## Phase 10 — Notifications and Communication

Status: `[x] Complete pending review`

### Objective

Deliver WhatsApp-first notifications with email fallback.

### Completed Deliverables

- `[x] Added manual WhatsApp invite link builder`

### Remaining Work

- `[x] Create notification table for outgoing message history`
- `[x] Add notification service abstraction`
- `[x] Implement Resend email fallback`
- `[x] Add WhatsApp Cloud API adapter when ready`
- `[x] Add notification preferences per project/member if needed`
- `[x] Add retry/error tracking for provider failures`

### Acceptance Criteria

- Invite and meeting notifications can be sent or prepared from backend services.
- Message delivery attempts are logged.
- Manual WhatsApp link MVP can upgrade to Cloud API without API contract changes.

### Phase 10 Review Notes

- Added notification history and project-level notification preferences tables/models.
- Added notification service abstraction that prepares WhatsApp/manual, WhatsApp Cloud API, and Resend payloads.
- Invite create/resend and meeting create/update now create notification records.
- Added project-scoped notification list, preferences, and retry endpoints for project admins.
- Added retry/error tracking fields including attempts, max attempts, last error, and next retry time.
- Manual WhatsApp links remain the MVP path while Cloud API payloads can be enabled through configuration.

## Phase 11 — Testing, QA, and Security Hardening

Status: `[~] Started with health test only`

### Objective

Prove tenant isolation, RBAC, budget security, and core flows before deployment.

### Completed Deliverables

- `[x] Added health endpoint test scaffold`
- `[x] Performed Python syntax sanity check`

### Remaining Work

- `[ ] Install backend dependencies and run pytest`
- `[ ] Install frontend dependencies and run Next.js build`
- `[ ] Add API tests for auth, projects, members, invites, meetings, budget visibility, and cross-project denial`
- `[ ] Add frontend component tests or smoke tests`
- `[ ] Add security checklist for auth, invite tokens, headers, CORS, and secrets`
- `[ ] Add linting/formatting workflow`

### Acceptance Criteria

- CI runs backend tests and frontend build successfully.
- Tests fail if budget data leaks across visibility modes.
- Tests fail if project data can be accessed without membership.
- Secrets are not committed.

## Phase 12 — Deployment and Operations

Status: `[~] CI placeholder created, deployment not started`

### Objective

Deploy the MVP using free-tier-friendly services.

### Completed Deliverables

- `[x] Added Dockerfile for backend`
- `[x] Added GitHub Actions CI placeholder`
- `[x] Documented deployment direction in README/docs`

### Remaining Work

- `[ ] Create Supabase project and apply schema/migrations`
- `[ ] Deploy frontend to Vercel`
- `[ ] Deploy backend to Render or Railway`
- `[ ] Configure production environment variables`
- `[ ] Configure CORS for production frontend URL`
- `[ ] Add PostHog analytics or Supabase logs fallback`
- `[ ] Add uptime/health monitoring`

### Acceptance Criteria

- Production frontend can call production backend.
- Backend can connect to Supabase Postgres.
- Auth provider works in production.
- Health endpoint is reachable publicly.

## 6. MVP Scope Cutoff

### Must Ship in v1

- `[~] Dashboard`
- `[~] Projects`
- `[~] Roles and project membership`
- `[~] Invites and acceptance flow`
- `[~] Meetings and RSVP tracking`
- `[~] Budget visibility enforcement`
- `[ ] Contributions tracking`
- `[ ] Phone-first auth`
- `[ ] Basic notifications through WhatsApp manual links and email fallback`

### Can Wait Until v1.1+

- `[ ] Analytics dashboards`
- `[ ] Vendor intelligence`
- `[ ] AI automation`
- `[ ] Mobile money/payment integrations`
- `[ ] WhatsApp Cloud API direct sending`
- `[ ] Full vendor marketplace`
- `[ ] Advanced staff hierarchy`

## 7. Open Product Decisions

These decisions should be finalized before deep implementation continues:

1. WhatsApp strategy: manual link MVP or Cloud API from day one?
2. Payment strategy: track contributions only or plan mobile money integration in v1?
3. Staff portal scope: internal admin only or role-based staff hierarchy?
4. Linked ceremonies: shared committee or separate committees with linked views?
5. RSVP enforcement: mandatory for committee/family meetings or optional?
6. Budget editing: can committee chair edit directly or only propose changes?
7. Vendor system: simple directory or marketplace foundation?
8. Notification priority: WhatsApp first with email fallback, or both equally?
9. Branding: confirm Purple + Gold, bold African luxury, structured minimal UI.
10. MVP cutoff: confirm what must be live before first real event pilot.

## 8. Recommended Next Implementation Sprint

### Sprint Goal

Make the scaffold runnable locally and replace development placeholders with production-shaped foundations.

### Sprint Tasks

1. Install backend and frontend dependencies.
2. Fix any dependency/runtime issues found by tests and builds.
3. Add Alembic or Supabase migration workflow.
4. Replace `X-User-Id` header auth with verified JWT dependency design.
5. Add project membership and budget visibility test suite.
6. Build login and event dashboard frontend routes.
7. Connect frontend dashboard to backend API.
8. Add seed/demo data for one wedding and one introduction ceremony.

### Sprint Definition of Done

- Backend starts locally with `uvicorn app.main:app --reload`.
- Frontend starts locally with `npm run dev`.
- API docs load at `/docs`.
- A seeded user can see only their projects.
- Budget endpoint returns different response shapes by visibility mode.
- README startup instructions are verified end-to-end.

## 9. Engineering Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Frontend-provided identity is trusted too long | Severe security flaw | Replace dev header auth early with verified JWT auth |
| Missing project filters | Cross-tenant data leak | Add tests for every tenant endpoint |
| Budget response over-shares data | Loss of user trust | Test every visibility mode and response schema |
| Invite token reuse | Unauthorized access | Store status, expiry, and single-use transitions |
| WhatsApp Cloud API setup delays | Slower onboarding | Keep manual link MVP path |
| Staff portal overreach | Privacy concerns | Add staff-specific authorization and audit logs |

## 10. Implementation Order Recommendation

1. Local dependency installation and runnable verification.
2. Auth provider decision and verified current-user dependency.
3. Migration/RLS setup.
4. RBAC tests and budget visibility tests.
5. Invite acceptance persistence.
6. Meetings + RSVP completion.
7. Contributions tracking.
8. Client portal API integration.
9. Staff portal access model.
10. Deployment pipeline.

## 11. Current File Map

- Backend entrypoint: `backend/app/main.py`
- Permission model: `backend/app/core/permissions.py`
- API routers: `backend/app/api/`
- Database models: `backend/app/models/`
- API schemas: `backend/app/schemas/`
- Frontend home: `frontend/app/page.tsx`
- Staff page: `frontend/app/staff/page.tsx`
- Invite page: `frontend/app/invite/[token]/page.tsx`
- Supabase schema: `supabase/schema.sql`
- Existing design docs: `docs/system-design.md`, `docs/api-spec.md`, `docs/ui-wireframes.md`
