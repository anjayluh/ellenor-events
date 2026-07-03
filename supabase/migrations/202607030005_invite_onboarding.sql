alter table invites
  add constraint invites_role_assigned_check check (role_assigned in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER','GUEST_VIEWER')),
  add constraint invites_status_check check (status in ('pending','accepted','expired','cancelled'));

alter table invites
  add column delivery_channel text not null default 'whatsapp' check (delivery_channel in ('whatsapp','email')),
  add column sent_count integer not null default 1,
  add column opened_count integer not null default 0,
  add column accepted_user_id uuid references users(id),
  add column last_sent_at timestamptz,
  add column opened_at timestamptz,
  add column accepted_at timestamptz,
  add column cancelled_at timestamptz;

create index idx_invites_project_status on invites(project_id, status);
create index idx_invites_accepted_user on invites(accepted_user_id);
