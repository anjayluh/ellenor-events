create extension if not exists pgcrypto;

create table users (
  id uuid primary key default gen_random_uuid(),
  name text,
  phone text unique,
  email text unique,
  created_at timestamptz default now(),
  check (phone is not null or email is not null)
);

create table staff_members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  role text not null default 'SUPPORT_AGENT' check (role in ('PLATFORM_ADMIN','OPERATIONS_MANAGER','SUPPORT_AGENT','STAFF_VIEWER')),
  status text not null default 'active' check (status in ('active','inactive')),
  created_at timestamptz default now(),
  unique(user_id)
);

create table auth_challenges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  contact text not null,
  channel text not null check (channel in ('phone','email')),
  purpose text not null default 'login',
  code_hash text not null,
  status text not null default 'pending' check (status in ('pending','verified','expired','cancelled')),
  request_ip text,
  expires_at timestamptz not null,
  requested_at timestamptz default now(),
  verified_at timestamptz
);


create table projects (
  id uuid primary key default gen_random_uuid(),
  type text not null check (type in ('wedding','introduction','linked')),
  title text not null,
  owner_user_id uuid not null references users(id),
  partner_user_id uuid references users(id),
  event_date date,
  status text not null default 'active',
  created_at timestamptz default now(),
  check (status in ('active','archived','completed','cancelled'))
);

create table project_settings (
  project_id uuid primary key references projects(id) on delete cascade,
  whatsapp_first boolean not null default true,
  email_fallback boolean not null default true,
  rsvp_required boolean not null default false,
  budget_editing_mode text not null default 'owners_only' check (budget_editing_mode in ('owners_only','chair_can_propose','chair_can_edit')),
  vendor_mode text not null default 'directory' check (vendor_mode in ('directory','marketplace_later')),
  updated_at timestamptz default now()
);

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references users(id),
  project_id uuid references projects(id),
  action text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);

create table project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER','GUEST_VIEWER')),
  permissions_level text,
  budget_visibility_mode text not null default 'NO_ACCESS' check (budget_visibility_mode in ('FULL_ACCESS','SUMMARY_ACCESS','CONTRIBUTION_ONLY','NO_ACCESS')),
  created_at timestamptz default now(),
  unique(project_id, user_id)
);

create table project_links (
  id uuid primary key default gen_random_uuid(),
  primary_project_id uuid not null references projects(id) on delete cascade,
  linked_project_id uuid not null references projects(id) on delete cascade,
  relationship_type text not null default 'linked_ceremony' check (relationship_type in ('linked_ceremony','shared_committee','same_couple')),
  shared_committee boolean not null default false,
  shared_budget boolean not null default false,
  notes text,
  created_at timestamptz default now(),
  check (primary_project_id <> linked_project_id),
  unique(primary_project_id, linked_project_id)
);

create table participants (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  name text not null,
  contact text,
  role_type text not null,
  linked_user_id uuid references users(id)
);

create table vendors (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  name text not null,
  category text not null,
  contact text,
  status text not null default 'shortlisted' check (status in ('shortlisted','contacted','confirmed','declined','completed')),
  notes text,
  external_url text,
  created_at timestamptz default now()
);

create table notification_preferences (
  project_id uuid primary key references projects(id) on delete cascade,
  whatsapp_enabled boolean not null default true,
  email_fallback_enabled boolean not null default true,
  meeting_updates boolean not null default true,
  invite_updates boolean not null default true,
  budget_updates boolean not null default false,
  updated_at timestamptz default now()
);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  recipient_user_id uuid references users(id),
  recipient_contact text,
  channel text not null default 'whatsapp' check (channel in ('whatsapp','email')),
  provider text not null default 'manual_whatsapp',
  subject text,
  body text not null,
  status text not null default 'prepared' check (status in ('prepared','sent','failed','retry_scheduled')),
  provider_payload jsonb not null default '{}'::jsonb,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  last_error text,
  next_retry_at timestamptz,
  prepared_at timestamptz default now(),
  sent_at timestamptz,
  created_at timestamptz default now()
);

create table invites (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  contact text not null,
  role_assigned text not null check (role_assigned in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER','GUEST_VIEWER')),
  token text unique not null,
  status text not null default 'pending' check (status in ('pending','accepted','expired','cancelled')),
  delivery_channel text not null default 'whatsapp' check (delivery_channel in ('whatsapp','email')),
  sent_count integer not null default 1,
  opened_count integer not null default 0,
  accepted_user_id uuid references users(id),
  expires_at timestamptz not null,
  last_sent_at timestamptz,
  opened_at timestamptz,
  accepted_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz default now()
);

create table meetings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  type text not null,
  title text not null,
  agenda text,
  notes text,
  decisions_log text,
  status text not null default 'scheduled' check (status in ('scheduled','completed','cancelled')),
  scheduled_time timestamptz not null,
  created_by uuid not null references users(id),
  updated_at timestamptz,
  created_at timestamptz default now()
);

create table meeting_rsvp (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null references meetings(id) on delete cascade,
  user_id uuid not null references users(id),
  status text not null check (status in ('accepted','declined','tentative')),
  comment text,
  responded_at timestamptz default now(),
  unique(meeting_id, user_id)
);

create table tasks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  title text not null,
  assigned_to uuid references users(id),
  status text not null default 'todo',
  due_date date
);

create table budgets (
  project_id uuid primary key references projects(id) on delete cascade,
  total numeric(12, 2) not null default 0,
  spent numeric(12, 2) not null default 0,
  check (total >= 0 and spent >= 0)
);

create table budget_line_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  category text not null,
  description text not null,
  estimated_amount numeric(12, 2) not null default 0,
  actual_amount numeric(12, 2) not null default 0,
  status text not null default 'planned' check (status in ('planned','approved','paid','cancelled')),
  created_at timestamptz default now(),
  check (estimated_amount >= 0 and actual_amount >= 0)
);

create table budget_proposals (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  proposed_by uuid not null references users(id),
  title text not null,
  description text,
  amount numeric(12, 2) not null default 0,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  reviewed_by uuid references users(id),
  reviewed_at timestamptz,
  created_at timestamptz default now(),
  check (amount >= 0)
);

create table contributions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  contributor text not null,
  pledged numeric(12, 2) not null default 0,
  paid numeric(12, 2) not null default 0,
  status text not null default 'pledged',
  check (pledged >= 0 and paid >= 0)
);

create table testimonials (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  type text not null,
  url text not null,
  caption text
);

create index idx_staff_members_user_status on staff_members(user_id, status);
create index idx_auth_challenges_contact_status on auth_challenges(contact, status, requested_at);
create index idx_audit_logs_actor_action on audit_logs(actor_user_id, action, created_at);
create index idx_audit_logs_project_action on audit_logs(project_id, action, created_at);
create index idx_project_settings_project on project_settings(project_id);
create index idx_project_members_project_user on project_members(project_id, user_id);
create index idx_project_links_primary on project_links(primary_project_id);
create index idx_project_links_linked on project_links(linked_project_id);
create index idx_participants_project on participants(project_id);
create index idx_vendors_project on vendors(project_id);
create index idx_notifications_project_status on notifications(project_id, status);
create index idx_notifications_next_retry on notifications(next_retry_at) where next_retry_at is not null;
create index idx_invites_project on invites(project_id);
create index idx_meetings_project_time on meetings(project_id, scheduled_time);
create index idx_tasks_project on tasks(project_id);
create index idx_budget_line_items_project on budget_line_items(project_id);
create index idx_budget_proposals_project on budget_proposals(project_id);
create index idx_contributions_project on contributions(project_id);
create index idx_testimonials_project on testimonials(project_id);
