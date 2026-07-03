alter table projects
  add constraint projects_status_check check (status in ('active','archived','completed','cancelled'));

create table project_settings (
  project_id uuid primary key references projects(id) on delete cascade,
  whatsapp_first boolean not null default true,
  email_fallback boolean not null default true,
  rsvp_required boolean not null default false,
  budget_editing_mode text not null default 'owners_only' check (budget_editing_mode in ('owners_only','chair_can_propose','chair_can_edit')),
  vendor_mode text not null default 'directory' check (vendor_mode in ('directory','marketplace_later')),
  updated_at timestamptz default now()
);

insert into project_settings (project_id)
select id from projects
on conflict (project_id) do nothing;

create index idx_project_settings_project on project_settings(project_id);

alter table project_settings enable row level security;

create policy project_settings_select_members on project_settings
  for select using (public.is_project_member(project_id));

create policy project_settings_mutate_admins on project_settings
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));
