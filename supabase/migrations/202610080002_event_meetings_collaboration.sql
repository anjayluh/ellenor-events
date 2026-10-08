alter table public.meetings
  add column if not exists category text not null default 'PLANNING',
  add column if not exists description text,
  add column if not exists location text,
  add column if not exists meeting_link text,
  add column if not exists start_at timestamptz,
  add column if not exists end_at timestamptz,
  add column if not exists timezone text,
  add column if not exists completed_at timestamptz,
  add column if not exists cancelled_at timestamptz,
  add column if not exists updated_by_user_id uuid references public.users(id);

alter table public.meetings drop constraint if exists meetings_status_check;
alter table public.meetings
  add constraint ck_meetings_status_collaboration check (status in ('scheduled','planned','in_progress','completed','cancelled','PLANNED','IN_PROGRESS','COMPLETED','CANCELLED'));
alter table public.meetings
  add constraint ck_meetings_time_range check (end_at is null or start_at is null or end_at >= start_at);
alter table public.meetings
  add constraint ck_meetings_category check (category in ('PLANNING','FAMILY','COMMITTEE','BUDGET','VENDOR','GUESTS','TIMELINE','OTHER'));

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'uq_meetings_id_project') then
    alter table public.meetings add constraint uq_meetings_id_project unique (id, project_id);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'uq_project_documents_id_project') then
    alter table public.project_documents add constraint uq_project_documents_id_project unique (id, project_id);
  end if;
end $$;

alter table public.tasks add column if not exists meeting_id uuid;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'fk_tasks_meeting_project') then
    alter table public.tasks add constraint fk_tasks_meeting_project
      foreign key (meeting_id, project_id) references public.meetings(id, project_id) on delete set null;
  end if;
end $$;

create index if not exists idx_meetings_project_start on public.meetings(project_id, start_at);
create index if not exists idx_meetings_project_status on public.meetings(project_id, status);
create index if not exists idx_tasks_project_meeting on public.tasks(project_id, meeting_id);

create table if not exists public.meeting_participants (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null,
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null,
  attendance_status text not null default 'INVITED',
  responded_at timestamptz,
  created_at timestamptz not null default now(),
  constraint uq_meeting_participant_user unique (meeting_id, user_id),
  constraint fk_meeting_participant_meeting_project foreign key (meeting_id, project_id) references public.meetings(id, project_id) on delete cascade,
  constraint fk_meeting_participant_project_member foreign key (project_id, user_id) references public.project_members(project_id, user_id) on delete cascade,
  constraint ck_meeting_participant_status check (attendance_status in ('INVITED','ACCEPTED','DECLINED','TENTATIVE'))
);

create table if not exists public.meeting_agenda_items (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null,
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null,
  description text,
  sort_order integer not null default 0,
  owner_user_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint fk_meeting_agenda_meeting_project foreign key (meeting_id, project_id) references public.meetings(id, project_id) on delete cascade,
  constraint fk_meeting_agenda_owner_member foreign key (project_id, owner_user_id) references public.project_members(project_id, user_id) on delete set null,
  constraint ck_meeting_agenda_title check (length(trim(title)) between 1 and 180)
);

create table if not exists public.meeting_decisions (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null,
  project_id uuid not null references public.projects(id) on delete cascade,
  decision_text text not null,
  context text,
  recorded_by_user_id uuid not null references public.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint fk_meeting_decision_meeting_project foreign key (meeting_id, project_id) references public.meetings(id, project_id) on delete cascade,
  constraint ck_meeting_decision_text check (length(trim(decision_text)) between 1 and 4000)
);

create table if not exists public.meeting_documents (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null,
  project_id uuid not null references public.projects(id) on delete cascade,
  document_id uuid not null,
  created_at timestamptz not null default now(),
  constraint uq_meeting_document unique (meeting_id, document_id),
  constraint fk_meeting_document_meeting_project foreign key (meeting_id, project_id) references public.meetings(id, project_id) on delete cascade,
  constraint fk_meeting_document_project_document foreign key (document_id, project_id) references public.project_documents(id, project_id) on delete cascade
);

create index if not exists idx_meeting_participants_project_meeting on public.meeting_participants(project_id, meeting_id);
create index if not exists idx_meeting_agenda_project_meeting on public.meeting_agenda_items(project_id, meeting_id, sort_order);
create index if not exists idx_meeting_decisions_project_meeting on public.meeting_decisions(project_id, meeting_id, created_at);
create index if not exists idx_meeting_documents_project_meeting on public.meeting_documents(project_id, meeting_id);

alter table public.meeting_participants enable row level security;
alter table public.meeting_agenda_items enable row level security;
alter table public.meeting_decisions enable row level security;
alter table public.meeting_documents enable row level security;

drop policy if exists meeting_participants_select_members on public.meeting_participants;
create policy meeting_participants_select_members on public.meeting_participants
  for select using (public.is_project_member(project_id));
drop policy if exists meeting_participants_mutate_managers on public.meeting_participants;
create policy meeting_participants_mutate_managers on public.meeting_participants
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'));

drop policy if exists meeting_agenda_select_members on public.meeting_agenda_items;
create policy meeting_agenda_select_members on public.meeting_agenda_items
  for select using (public.is_project_member(project_id));
drop policy if exists meeting_agenda_mutate_managers on public.meeting_agenda_items;
create policy meeting_agenda_mutate_managers on public.meeting_agenda_items
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'));

drop policy if exists meeting_decisions_select_members on public.meeting_decisions;
create policy meeting_decisions_select_members on public.meeting_decisions
  for select using (public.is_project_member(project_id));
drop policy if exists meeting_decisions_mutate_managers on public.meeting_decisions;
create policy meeting_decisions_mutate_managers on public.meeting_decisions
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'));

drop policy if exists meeting_documents_select_members on public.meeting_documents;
create policy meeting_documents_select_members on public.meeting_documents
  for select using (public.is_project_member(project_id));
drop policy if exists meeting_documents_mutate_managers on public.meeting_documents;
create policy meeting_documents_mutate_managers on public.meeting_documents
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) or public.has_project_permission(project_id, 'meetings.manage'));
