# Ellenor Events User Flow Coverage

This matrix translates the current product scope into user journeys for review.

| Status | Meaning |
| --- | --- |
| Covered | Implemented in backend and reachable in frontend. |
| Backend covered | API exists and is tested, but frontend UX is partial. |
| Partial | Core path exists, but important UX or operational steps remain. |
| Not covered | Known product need not yet implemented. |

## Public and Authentication

| Flow | Primary users | Business value | Status |
| --- | --- | --- | --- |
| Public visitor sees marketing pages without private event data | Anonymous visitors | Builds trust while protecting event details | Covered |
| User creates account with email/password | Couples, planners, committee leads | Starts identity setup through Supabase Auth | Partial: email confirmation is required |
| Existing user signs in and lands in workspace | All authenticated users | Avoids dead-end login UX | Covered |
| User sees validation rules before submit | All users | Reduces failed submissions | Covered for login, onboarding, meeting, budget, task, and vendor forms |
| User signs out | All authenticated users | Clears local session safely | Covered |

## Event Owner and Partner

| Flow | Primary users | Business value | Status |
| --- | --- | --- | --- |
| Create first event workspace | Couple, planner, family lead | Solves empty account dead end and creates tenancy | Covered |
| Manage multiple event workspaces | Couples, planners, family leads | Supports coordinating more than one wedding, introduction, or linked ceremony at the same time | Covered |
| Switch active event for feature pages | Multi-event users | Keeps budgets, meetings, committees, vendors, and invites scoped to the selected event | Covered |
| View event dashboard and role | Owner, partner | Understand event context and access level | Covered |
| Update budget totals | Owner, partner | Track financial plan and spend | Covered |
| Add meetings | Owner, partner | Coordinate planning touchpoints | Covered |
| Add committee tasks | Owner, partner | Assign and track work | Covered |
| Add vendor options | Owner, partner | Build shortlist for service providers | Covered |
| Invite members by email and role | Owner, partner, committee chair | Onboard collaborators into the correct event workspace | Covered |
| Resend or cancel pending invites | Owner, partner, committee chair | Manage invite mistakes and reminders safely | Covered |
| Archive or restore event | Owner, partner | Close inactive events without deleting history | Backend covered |
| Manage project settings | Owner, partner, committee chair | Configure RSVP, vendor, and notification behavior | Backend covered |

## Committee

| Flow | Primary users | Business value | Status |
| --- | --- | --- | --- |
| Committee chair sees summary budget | Committee chair | Guides decisions without exposing sensitive details | Covered |
| Committee member/chair creates meetings | Committee team | Keeps cross-family coordination structured | Covered |
| Committee member/chair creates tasks | Committee team | Tracks work before ceremonies | Covered |
| Committee member/chair adds vendors | Committee team | Builds options for owner approval | Covered |
| Committee member RSVPs to meetings | Committee team | Confirms attendance and accountability | Covered |
| Committee chair creates budget proposal | Committee chair | Requests budget changes without direct owner edits | Backend covered |

## Family and Guest

| Flow | Primary users | Business value | Status |
| --- | --- | --- | --- |
| Family viewer sees contribution-only budget | Family members | Shares contribution progress without exposing full budget | Covered |
| Guest viewer sees meetings but not budget | Guests | Keeps guests informed without sensitive data exposure | Covered |
| Invited person previews invite | Invite recipients | Confirms event invitation before accepting | Covered |
| Invited person accepts invite with email or phone | Invite recipients | Creates membership from token | Covered |
| Invite reuse, expiry, and cancellation protection | Invite recipients and owners | Prevents unauthorized membership reuse | Backend covered |

## Staff and Operations

| Flow | Primary users | Business value | Status |
| --- | --- | --- | --- |
| Staff user accesses internal dashboard | Platform admin/support | Monitors event health and risk | Covered |
| Non-staff user is blocked from staff portal | All non-staff users | Protects internal operations | Covered |
| Staff sees project health and risk alerts | Platform admin/support | Identifies stuck or risky events | Covered |
| Staff performs support actions | Platform admin/support | Resolves customer issues | Not covered beyond dashboard visibility |

## Notifications and Deployment

| Flow | Primary users | Business value | Status |
| --- | --- | --- | --- |
| Email-first invite notification is prepared | Owners, invitees | Free-tier-friendly notification path | Covered |
| Notification preferences are read/updated | Project admins | Configure notification behavior | Backend covered |
| Outbound email delivery via provider | Invitees/members | Sends real email outside the app | Partial: payloads are prepared; provider worker is not implemented |
| Supabase migrations apply remotely | DevOps/contributors | Keeps remote database in sync | Covered |
| Frontend/backend deploy to free-tier services | DevOps/contributors | Enables QA/staging/production rollout | Covered in docs |

## Priority Gaps To Confirm

1. Frontend invite analytics.
2. Frontend member management: add, update, remove roles with last-owner protection.
3. Budget line items, contributions, and proposal screens.
4. Staff support actions beyond dashboard visibility.
5. Real outbound email worker/provider integration.
6. RSVP summaries and meeting attendance reporting.
7. Vendor-specific login and work acceptance flow.
