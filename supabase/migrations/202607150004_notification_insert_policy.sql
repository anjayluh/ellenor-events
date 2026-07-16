create policy notifications_insert_committee on public.notifications
  for insert
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));
