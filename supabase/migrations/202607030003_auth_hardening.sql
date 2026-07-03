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

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references users(id),
  project_id uuid references projects(id),
  action text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);

create index idx_auth_challenges_contact_status on auth_challenges(contact, status, requested_at);
create index idx_audit_logs_actor_action on audit_logs(actor_user_id, action, created_at);
create index idx_audit_logs_project_action on audit_logs(project_id, action, created_at);

alter table auth_challenges enable row level security;
alter table audit_logs enable row level security;

create policy auth_challenges_service_only on auth_challenges
  for all using (false) with check (false);

create policy audit_logs_service_only on audit_logs
  for all using (false) with check (false);
