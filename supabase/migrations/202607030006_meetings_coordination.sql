alter table meetings
  add column notes text,
  add column decisions_log text,
  add column status text not null default 'scheduled' check (status in ('scheduled','completed','cancelled')),
  add column updated_at timestamptz;

alter table meeting_rsvp
  add column responded_at timestamptz default now();

alter table meeting_rsvp
  add constraint meeting_rsvp_status_check check (status in ('accepted','declined','tentative'));

create unique index if not exists idx_meeting_rsvp_unique_user on meeting_rsvp(meeting_id, user_id);
