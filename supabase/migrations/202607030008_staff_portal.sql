create table staff_members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  role text not null default 'SUPPORT_AGENT' check (role in ('PLATFORM_ADMIN','OPERATIONS_MANAGER','SUPPORT_AGENT','STAFF_VIEWER')),
  status text not null default 'active' check (status in ('active','inactive')),
  created_at timestamptz default now(),
  unique(user_id)
);

create index idx_staff_members_user_status on staff_members(user_id, status);

alter table staff_members enable row level security;

create policy staff_members_self_read on staff_members
  for select using (user_id = auth.uid());

create policy staff_members_service_only_mutate on staff_members
  for all using (false) with check (false);
