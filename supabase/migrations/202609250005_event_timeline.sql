create table if not exists public.project_timeline_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null,
  description text,
  category text not null default 'PROGRAM',
  start_at timestamptz not null,
  end_at timestamptz not null,
  location text,
  assignee_user_id uuid references public.users(id),
  created_by_user_id uuid references public.users(id),
  status text not null default 'UPCOMING',
  notes text,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

alter table public.project_timeline_items drop constraint if exists ck_project_timeline_items_category;
alter table public.project_timeline_items
  add constraint ck_project_timeline_items_category check (category in ('PREPARATION','CEREMONY','RECEPTION','FAMILY','PHOTOGRAPHY','VIDEOGRAPHY','CATERING','DECOR','ENTERTAINMENT','TRANSPORT','GUESTS','VENDORS','PROGRAM','BREAK','OTHER'));

alter table public.project_timeline_items drop constraint if exists ck_project_timeline_items_status;
alter table public.project_timeline_items
  add constraint ck_project_timeline_items_status check (status in ('UPCOMING','IN_PROGRESS','COMPLETED','CANCELLED'));

alter table public.project_timeline_items drop constraint if exists ck_project_timeline_items_time_range;
alter table public.project_timeline_items
  add constraint ck_project_timeline_items_time_range check (end_at > start_at);

create or replace function public.set_project_timeline_item_integrity()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  assignee_exists boolean;
begin
  new.category := upper(coalesce(new.category, 'PROGRAM'));
  new.status := upper(coalesce(new.status, 'UPCOMING'));
  new.sort_order := coalesce(new.sort_order, 0);

  if new.end_at <= new.start_at then
    raise exception 'End time must be after start time';
  end if;

  if new.assignee_user_id is not null then
    select exists (
      select 1
      from public.project_members pm
      where pm.project_id = new.project_id
        and pm.user_id = new.assignee_user_id
    ) into assignee_exists;

    if not assignee_exists then
      raise exception 'Timeline assignee must be an event member';
    end if;
  end if;

  if tg_op = 'UPDATE' then
    new.updated_at := now();
  end if;

  return new;
end;
$$;

drop trigger if exists trg_project_timeline_items_integrity on public.project_timeline_items;
create trigger trg_project_timeline_items_integrity
before insert or update
on public.project_timeline_items
for each row
execute function public.set_project_timeline_item_integrity();

create index if not exists idx_project_timeline_items_project_start on public.project_timeline_items(project_id, start_at, sort_order);
create index if not exists idx_project_timeline_items_project_status on public.project_timeline_items(project_id, status);
create index if not exists idx_project_timeline_items_project_category on public.project_timeline_items(project_id, category);
create index if not exists idx_project_timeline_items_project_assignee on public.project_timeline_items(project_id, assignee_user_id) where assignee_user_id is not null;
create index if not exists idx_project_timeline_items_project_range on public.project_timeline_items(project_id, start_at, end_at);

alter table public.project_timeline_items enable row level security;

drop policy if exists project_timeline_items_select_members on public.project_timeline_items;
create policy project_timeline_items_select_members on public.project_timeline_items
  for select
  using (public.is_project_member(project_id));

drop policy if exists project_timeline_items_insert_planners on public.project_timeline_items;
create policy project_timeline_items_insert_planners on public.project_timeline_items
  for insert
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'tasks.manage'));

drop policy if exists project_timeline_items_update_planners on public.project_timeline_items;
create policy project_timeline_items_update_planners on public.project_timeline_items
  for update
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'tasks.manage'))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'tasks.manage'));

drop policy if exists project_timeline_items_delete_planners on public.project_timeline_items;
create policy project_timeline_items_delete_planners on public.project_timeline_items
  for delete
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'tasks.manage'));
