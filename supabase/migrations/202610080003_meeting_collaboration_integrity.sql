alter table public.tasks drop constraint if exists fk_tasks_meeting_project;
alter table public.tasks
  add constraint fk_tasks_meeting_project
  foreign key (meeting_id, project_id) references public.meetings(id, project_id) on delete restrict;

alter table public.meeting_agenda_items drop constraint if exists fk_meeting_agenda_owner_member;
alter table public.meeting_agenda_items
  add constraint fk_meeting_agenda_owner_user
  foreign key (owner_user_id) references public.users(id) on delete set null;
