# API Spec

## Authentication

- `POST /auth/login` requests phone OTP or email magic link.
- `POST /auth/verify-otp` exchanges a verification code for a bearer token and returns the global user.

### Auth Notes

- Production target is Supabase Auth.
- API clients must send `Authorization: Bearer <token>` for protected endpoints.
- `X-User-Id` is not a production auth mechanism and is disabled unless explicitly enabled for local development.

## Projects

- `GET /projects` lists projects for the authenticated user.
- `POST /projects` creates a project and owner membership.
- `GET /projects/{project_id}` returns one tenant-scoped project.

## Members

- `GET /projects/{project_id}/members` lists members.
- `POST /projects/{project_id}/members` adds a user to a project. Requires project admin role.

## Meetings

- `GET /projects/{project_id}/meetings` lists project meetings.
- `POST /projects/{project_id}/meetings` creates a meeting for committee-capable roles.
- `GET /projects/{project_id}/meetings/{meeting_id}` reads one meeting.
- `PATCH /projects/{project_id}/meetings/{meeting_id}` updates meeting agenda, notes, decisions, status, or time.
- `DELETE /projects/{project_id}/meetings/{meeting_id}` deletes a meeting for owner/partner/chair roles.
- `POST /projects/{project_id}/meetings/{meeting_id}/rsvp` upserts RSVP status.

## Tasks

- `GET /projects/{project_id}/tasks` lists project-scoped tasks, optionally filtered by assignee.
- `POST /projects/{project_id}/tasks` creates an assignable task for committee-capable roles.
- `PATCH /projects/{project_id}/tasks/{task_id}` updates task title, assignee, status, or due date.
- `DELETE /projects/{project_id}/tasks/{task_id}` removes a task.

## Vendors

- `GET /projects/{project_id}/vendors` lists first-class vendor directory records.
- `POST /projects/{project_id}/vendors` creates a vendor without requiring a user account.
- `PATCH /projects/{project_id}/vendors/{vendor_id}` updates vendor status, contact, notes, and external URL.
- `DELETE /projects/{project_id}/vendors/{vendor_id}` removes a vendor.

## Testimonials

- `GET /projects/{project_id}/testimonials` lists URL-only media/testimonial records.
- `POST /projects/{project_id}/testimonials` stores a URL and caption only.
- `PATCH /projects/{project_id}/testimonials/{testimonial_id}` updates URL metadata.
- `DELETE /projects/{project_id}/testimonials/{testimonial_id}` removes a testimonial.

## Budget

- `GET /projects/{project_id}/budget` returns a visibility-shaped budget object.
- `PATCH /projects/{project_id}/budget` updates totals. Requires owner or partner role.
- `GET /projects/{project_id}/budget/line-items` lists full-access line items.
- `POST/PATCH/DELETE /projects/{project_id}/budget/line-items` manages detailed budget items for owners/partners.
- `GET/POST/PATCH/DELETE /projects/{project_id}/budget/contributions` tracks pledged and paid contributions.
- `GET/POST /projects/{project_id}/budget/proposals` supports committee chair budget proposals.
- `PATCH /projects/{project_id}/budget/proposals/{proposal_id}/review` approves or rejects proposals for owners/partners.
- `GET /projects/{project_id}/budget/export` returns an owner/partner export payload.

## Invites

- `POST /invites` creates a secure expiring invite.
- `GET /invites/{token}` reads and records an opened invite.
- `POST /invites/accept` accepts an invite token and creates/links project membership.
- `POST /invites/{invite_id}/resend` renews and resends a pending/cancelled/expired invite.
- `POST /invites/{invite_id}/cancel` cancels an unused invite.
- `GET /invites/projects/{project_id}/analytics` summarizes invite status, sent count, and opened count.

## Staff

- `GET /staff/dashboard`
- `GET /staff/projects`
- `GET /staff/analytics`
