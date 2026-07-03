create extension if not exists pgcrypto;

create table users (
  id uuid primary key default gen_random_uuid(),
  name text,
  phone text unique,
  email text unique,
  created_at timestamptz default now(),
  check (phone is not null or email is not null)
);

create table projects (
  id uuid primary key default gen_random_uuid(),
  type text not null check (type in ('wedding','introduction','linked')),
  title text not null,
  owner_user_id uuid not null references users(id),
  partner_user_id uuid references users(id),
  event_date date,
  status text not null default 'active',
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

create table invites (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  contact text not null,
  role_assigned text not null,
  token text unique not null,
  status text not null default 'pending',
  expires_at timestamptz not null,
  created_at timestamptz default now()
);

create table meetings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  type text not null,
  title text not null,
  agenda text,
  scheduled_time timestamptz not null,
  created_by uuid not null references users(id),
  created_at timestamptz default now()
);

create table meeting_rsvp (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null references meetings(id) on delete cascade,
  user_id uuid not null references users(id),
  status text not null,
  comment text,
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

create index idx_project_members_project_user on project_members(project_id, user_id);
create index idx_project_links_primary on project_links(primary_project_id);
create index idx_project_links_linked on project_links(linked_project_id);
create index idx_participants_project on participants(project_id);
create index idx_vendors_project on vendors(project_id);
create index idx_invites_project on invites(project_id);
create index idx_meetings_project_time on meetings(project_id, scheduled_time);
create index idx_tasks_project on tasks(project_id);
create index idx_contributions_project on contributions(project_id);
create index idx_testimonials_project on testimonials(project_id);
