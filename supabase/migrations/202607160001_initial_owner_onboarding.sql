create policy project_members_insert_initial_owner on public.project_members
  for insert
  with check (
    user_id = auth.uid()
    and role = 'OWNER'
    and budget_visibility_mode = 'FULL_ACCESS'
    and exists (
      select 1
      from public.projects p
      where p.id = project_id
        and p.owner_user_id = auth.uid()
    )
  );
