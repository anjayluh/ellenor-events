alter table public.tasks
  add column if not exists description text,
  add column if not exists priority text not null default 'MEDIUM',
  add column if not exists category text not null default 'GENERAL',
  add column if not exists created_by_user_id uuid references public.users(id),
  add column if not exists completed_at timestamptz,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz;

alter table public.tasks
  alter column assigned_to drop not null;

update public.tasks
set status = case lower(status)
  when 'todo' then 'TODO'
  when 'to_do' then 'TODO'
  when 'in_progress' then 'IN_PROGRESS'
  when 'done' then 'DONE'
  else upper(status)
end;

update public.tasks
set completed_at = coalesce(completed_at, now())
where status = 'DONE' and completed_at is null;

alter table public.tasks drop constraint if exists ck_tasks_status;
alter table public.tasks
  add constraint ck_tasks_status check (status in ('TODO','IN_PROGRESS','DONE'));

alter table public.tasks drop constraint if exists ck_tasks_priority;
alter table public.tasks
  add constraint ck_tasks_priority check (priority in ('LOW','MEDIUM','HIGH','URGENT'));

alter table public.tasks drop constraint if exists ck_tasks_category;
alter table public.tasks
  add constraint ck_tasks_category check (category in ('GENERAL','PROGRAM','FINANCE','GUESTS','VENDORS','LOGISTICS','VENUE','DECOR','COMMUNICATION','FAMILY','COMMITTEE'));

alter table public.tasks drop constraint if exists fk_tasks_assigned_member;

create or replace function public.set_task_timestamps()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.status = 'DONE' and old.status is distinct from 'DONE' then
    new.completed_at := coalesce(new.completed_at, now());
  elsif new.status <> 'DONE' then
    new.completed_at := null;
  end if;
  new.updated_at := now();
  return new;
end;
$$;

do $$
begin
  if not exists (
    select 1 from pg_trigger where tgname = 'trg_tasks_set_timestamps' and tgrelid = 'public.tasks'::regclass
  ) then
    create trigger trg_tasks_set_timestamps
    before update of status, title, description, priority, category, assigned_to, due_date
    on public.tasks
    for each row
    execute function public.set_task_timestamps();
  end if;
end $$;

create index if not exists idx_tasks_project_status on public.tasks(project_id, status);
create index if not exists idx_tasks_project_priority on public.tasks(project_id, priority);
create index if not exists idx_tasks_project_category on public.tasks(project_id, category);
create index if not exists idx_tasks_project_assignee on public.tasks(project_id, assigned_to);
create index if not exists idx_tasks_project_due_date on public.tasks(project_id, due_date);

alter table public.tasks enable row level security;

drop policy if exists tasks_select_members on public.tasks;
create policy tasks_select_members on public.tasks
  for select
  using (public.is_project_member(project_id));

drop policy if exists tasks_mutate_committee on public.tasks;
drop policy if exists tasks_insert_managers on public.tasks;
drop policy if exists tasks_update_managers_or_assignee on public.tasks;
drop policy if exists tasks_delete_managers on public.tasks;
create policy tasks_insert_managers on public.tasks
  for insert
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy tasks_update_managers_or_assignee on public.tasks
  for update
  using (
    public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER'])
    or assigned_to = auth.uid()
  )
  with check (
    public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER'])
    or assigned_to = auth.uid()
  );

create policy tasks_delete_managers on public.tasks
  for delete
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));
