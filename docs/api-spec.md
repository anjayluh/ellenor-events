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
- `POST /projects/{project_id}/meetings` creates a meeting.
- `POST /projects/{project_id}/meetings/{meeting_id}/rsvp` records RSVP status.

## Budget

- `GET /projects/{project_id}/budget` returns a visibility-shaped budget object.
- `PATCH /projects/{project_id}/budget` updates totals. Requires owner or partner role.

## Invites

- `POST /invites` creates a secure expiring invite.
- `POST /invites/accept` accepts an invite token.

## Staff

- `GET /staff/dashboard`
- `GET /staff/projects`
- `GET /staff/analytics`
