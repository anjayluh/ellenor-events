alter table public.project_guests
  add column if not exists rsvp_attendee_count integer not null default 1,
  add column if not exists rsvp_note text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'ck_project_guests_rsvp_attendee_count'
      and conrelid = 'public.project_guests'::regclass
  ) then
    alter table public.project_guests
      add constraint ck_project_guests_rsvp_attendee_count check (rsvp_attendee_count >= 0);
  end if;
end $$;
