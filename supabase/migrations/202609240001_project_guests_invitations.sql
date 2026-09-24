create table if not exists public.project_guests (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  first_name text not null,
  last_name text,
  display_name text not null,
  email text,
  phone text,
  category text,
  group_name text,
  notes text,
  invitation_card_url text,
  invitation_status text not null default 'NOT_SENT' check (invitation_status in ('NOT_SENT','SENT','OPENED','RESPONDED')),
  rsvp_status text not null default 'PENDING' check (rsvp_status in ('PENDING','ATTENDING','NOT_ATTENDING')),
  rsvp_responded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  check (email is not null or phone is not null)
);

create table if not exists public.project_guest_invitations (
  id uuid primary key default gen_random_uuid(),
  project_guest_id uuid not null references public.project_guests(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  recipient_email text not null,
  recipient_name text not null,
  token text not null unique,
  status text not null default 'SENT' check (status in ('SENT','OPENED','RESPONDED','FAILED','CANCELLED')),
  sent_at timestamptz,
  opened_at timestamptz,
  responded_at timestamptz,
  notification_id uuid,
  provider_reference text,
  created_at timestamptz not null default now()
);

create index if not exists idx_project_guests_project on public.project_guests(project_id);
create index if not exists idx_project_guests_invitation_status on public.project_guests(project_id, invitation_status);
create index if not exists idx_project_guests_rsvp_status on public.project_guests(project_id, rsvp_status);
create index if not exists idx_project_guests_email on public.project_guests(project_id, email);
create index if not exists idx_project_guests_category_group on public.project_guests(project_id, category, group_name);
create index if not exists idx_project_guest_invitations_guest on public.project_guest_invitations(project_guest_id, created_at desc);
create index if not exists idx_project_guest_invitations_project on public.project_guest_invitations(project_id, created_at desc);
create index if not exists idx_project_guest_invitations_token on public.project_guest_invitations(token);

alter table public.project_guests enable row level security;
alter table public.project_guest_invitations enable row level security;

drop policy if exists project_guests_select_planning_team on public.project_guests;
create policy project_guests_select_planning_team on public.project_guests
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

drop policy if exists project_guests_mutate_guest_managers on public.project_guests;
create policy project_guests_mutate_guest_managers on public.project_guests
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

drop policy if exists project_guest_invitations_select_planning_team on public.project_guest_invitations;
create policy project_guest_invitations_select_planning_team on public.project_guest_invitations
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

drop policy if exists project_guest_invitations_mutate_guest_managers on public.project_guest_invitations;
create policy project_guest_invitations_mutate_guest_managers on public.project_guest_invitations
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));
