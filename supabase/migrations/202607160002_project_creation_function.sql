create or replace function public.create_project_with_owner(
  project_type text,
  project_title text,
  owner_user_id uuid,
  partner_user_id uuid default null,
  event_date date default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  project_id uuid;
begin
  if owner_user_id <> auth.uid() then
    raise insufficient_privilege using message = 'Project owner must match authenticated user';
  end if;

  insert into public.projects (type, title, owner_user_id, partner_user_id, event_date, status)
  values (project_type, project_title, owner_user_id, partner_user_id, event_date, 'active')
  returning id into project_id;

  insert into public.project_members (project_id, user_id, role, permissions_level, budget_visibility_mode)
  values (project_id, owner_user_id, 'OWNER', 'admin', 'FULL_ACCESS');

  insert into public.project_settings (project_id)
  values (project_id);

  return project_id;
end;
$$;

revoke all on function public.create_project_with_owner(text, text, uuid, uuid, date) from public;
grant execute on function public.create_project_with_owner(text, text, uuid, uuid, date) to authenticated;
