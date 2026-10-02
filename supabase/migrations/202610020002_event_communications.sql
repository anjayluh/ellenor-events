create table if not exists public.project_communications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  author_user_id uuid not null references public.users(id),
  title text not null,
  body text not null,
  communication_type text not null default 'UPDATE',
  priority text not null default 'NORMAL',
  audience_mode text not null default 'ALL_MEMBERS',
  is_pinned boolean not null default false,
  is_archived boolean not null default false,
  published_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  archived_at timestamptz,
  constraint uq_project_communications_id_project unique (id, project_id),
  constraint ck_project_communications_title check (length(trim(title)) between 3 and 180),
  constraint ck_project_communications_body check (length(trim(body)) between 1 and 10000),
  constraint ck_project_communications_type check (communication_type in ('ANNOUNCEMENT','UPDATE','REMINDER','PLANNING_NOTE')),
  constraint ck_project_communications_priority check (priority in ('NORMAL','IMPORTANT','URGENT')),
  constraint ck_project_communications_audience check (audience_mode in ('ALL_MEMBERS','SELECTED_MEMBERS'))
);

create table if not exists public.project_communication_recipients (
  id uuid primary key default gen_random_uuid(),
  communication_id uuid not null references public.project_communications(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  recipient_user_id uuid not null references public.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint uq_project_communication_recipient unique (communication_id, recipient_user_id),
  constraint fk_project_communication_recipient_communication foreign key (communication_id, project_id)
    references public.project_communications(id, project_id) on delete cascade,
  constraint fk_project_communication_recipient_membership foreign key (project_id, recipient_user_id)
    references public.project_members(project_id, user_id) on delete cascade
);

create table if not exists public.project_communication_reads (
  id uuid primary key default gen_random_uuid(),
  communication_id uuid not null references public.project_communications(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  read_at timestamptz not null default now(),
  constraint uq_project_communication_read unique (communication_id, user_id),
  constraint fk_project_communication_read_communication foreign key (communication_id, project_id)
    references public.project_communications(id, project_id) on delete cascade,
  constraint fk_project_communication_read_membership foreign key (project_id, user_id)
    references public.project_members(project_id, user_id) on delete cascade
);

create index if not exists idx_project_communications_project_created on public.project_communications(project_id, created_at desc);
create index if not exists idx_project_communications_project_active on public.project_communications(project_id, is_archived, is_pinned);
create index if not exists idx_project_communications_project_type on public.project_communications(project_id, communication_type);
create index if not exists idx_project_communication_recipients_project_user on public.project_communication_recipients(project_id, recipient_user_id);
create index if not exists idx_project_communication_reads_project_user on public.project_communication_reads(project_id, user_id);

create or replace function public.can_manage_project_communications(target_project_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select public.has_project_role(target_project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR'])
    or public.has_project_permission(target_project_id, 'communications.manage');
$$;

create or replace function public.can_view_project_communication(target_communication_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
stable
as $$
declare
  target_project_id uuid;
  target_type text;
  target_audience text;
  member_role text;
begin
  select pc.project_id, pc.communication_type, pc.audience_mode
    into target_project_id, target_type, target_audience
  from public.project_communications pc
  where pc.id = target_communication_id;

  if target_project_id is null then
    return false;
  end if;

  select pm.role into member_role
  from public.project_members pm
  where pm.project_id = target_project_id and pm.user_id = auth.uid();

  if member_role is null then
    return false;
  end if;

  if target_type = 'PLANNING_NOTE' and member_role not in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER') then
    return false;
  end if;

  if target_audience = 'ALL_MEMBERS' then
    return member_role <> 'GUEST_VIEWER';
  end if;

  return exists (
    select 1
    from public.project_communication_recipients pcr
    where pcr.communication_id = target_communication_id
      and pcr.recipient_user_id = auth.uid()
  );
end;
$$;

create or replace function public.prevent_communication_author_change()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if tg_op = 'UPDATE' and new.author_user_id is distinct from old.author_user_id then
    raise exception 'Communication authorship cannot be changed';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_prevent_communication_author_change on public.project_communications;
create trigger trg_prevent_communication_author_change
before update on public.project_communications
for each row execute function public.prevent_communication_author_change();

alter table public.project_communications enable row level security;
alter table public.project_communication_recipients enable row level security;
alter table public.project_communication_reads enable row level security;

drop policy if exists project_communications_select_visible on public.project_communications;
create policy project_communications_select_visible on public.project_communications
  for select using (public.can_view_project_communication(id));

drop policy if exists project_communications_insert_managers on public.project_communications;
create policy project_communications_insert_managers on public.project_communications
  for insert with check (public.can_manage_project_communications(project_id) and author_user_id = auth.uid());

drop policy if exists project_communications_update_managers on public.project_communications;
create policy project_communications_update_managers on public.project_communications
  for update
  using (public.can_manage_project_communications(project_id) and not is_archived)
  with check (public.can_manage_project_communications(project_id));

drop policy if exists project_communication_recipients_select_visible on public.project_communication_recipients;
create policy project_communication_recipients_select_visible on public.project_communication_recipients
  for select using (public.can_view_project_communication(communication_id));

drop policy if exists project_communication_recipients_insert_managers on public.project_communication_recipients;
create policy project_communication_recipients_insert_managers on public.project_communication_recipients
  for insert with check (
    public.can_manage_project_communications(project_id)
    and exists (select 1 from public.project_communications pc where pc.id = communication_id and pc.project_id = project_communication_recipients.project_id)
    and exists (
      select 1 from public.project_members pm
      where pm.project_id = project_communication_recipients.project_id
        and pm.user_id = project_communication_recipients.recipient_user_id
        and pm.role <> 'GUEST_VIEWER'
    )
  );

drop policy if exists project_communication_reads_select_own on public.project_communication_reads;
create policy project_communication_reads_select_own on public.project_communication_reads
  for select using (user_id = auth.uid() and public.can_view_project_communication(communication_id));

drop policy if exists project_communication_reads_insert_own on public.project_communication_reads;
create policy project_communication_reads_insert_own on public.project_communication_reads
  for insert with check (user_id = auth.uid() and public.can_view_project_communication(communication_id));

drop policy if exists project_communication_reads_update_own on public.project_communication_reads;
create policy project_communication_reads_update_own on public.project_communication_reads
  for update using (user_id = auth.uid() and public.can_view_project_communication(communication_id))
  with check (user_id = auth.uid() and public.can_view_project_communication(communication_id));
