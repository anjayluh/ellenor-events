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

create index idx_budget_line_items_project on budget_line_items(project_id);
create index idx_budget_proposals_project on budget_proposals(project_id);

alter table budget_line_items enable row level security;
alter table budget_proposals enable row level security;

create policy budget_line_items_select_members on budget_line_items
  for select using (public.is_project_member(project_id));

create policy budget_line_items_mutate_owners_partners on budget_line_items
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER']));

create policy budget_proposals_select_admins on budget_proposals
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy budget_proposals_insert_admins on budget_proposals
  for insert with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy budget_proposals_update_owners_partners on budget_proposals
  for update using (public.has_project_role(project_id, array['OWNER','PARTNER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER']));
