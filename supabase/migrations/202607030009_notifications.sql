create table notification_preferences (
  project_id uuid primary key references projects(id) on delete cascade,
  whatsapp_enabled boolean not null default true,
  email_fallback_enabled boolean not null default true,
  meeting_updates boolean not null default true,
  invite_updates boolean not null default true,
  budget_updates boolean not null default false,
  updated_at timestamptz default now()
);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  recipient_user_id uuid references users(id),
  recipient_contact text,
  channel text not null default 'whatsapp' check (channel in ('whatsapp','email')),
  provider text not null default 'manual_whatsapp',
  subject text,
  body text not null,
  status text not null default 'prepared' check (status in ('prepared','sent','failed','retry_scheduled')),
  provider_payload jsonb not null default '{}'::jsonb,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  last_error text,
  next_retry_at timestamptz,
  prepared_at timestamptz default now(),
  sent_at timestamptz,
  created_at timestamptz default now()
);

insert into notification_preferences (project_id)
select id from projects
on conflict (project_id) do nothing;

create index idx_notifications_project_status on notifications(project_id, status);
create index idx_notifications_next_retry on notifications(next_retry_at) where next_retry_at is not null;

alter table notification_preferences enable row level security;
alter table notifications enable row level security;

create policy notification_preferences_select_admins on notification_preferences
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy notification_preferences_mutate_admins on notification_preferences
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy notifications_select_admins on notifications
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy notifications_mutate_admins on notifications
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));
