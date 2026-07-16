grant usage on schema public to authenticated;

grant select, insert, update, delete on table
  public.users,
  public.projects,
  public.project_members,
  public.project_links,
  public.participants,
  public.vendors,
  public.invites,
  public.meetings,
  public.meeting_rsvp,
  public.tasks,
  public.budgets,
  public.contributions,
  public.testimonials,
  public.project_settings,
  public.budget_line_items,
  public.budget_proposals,
  public.staff_members,
  public.notification_preferences,
  public.notifications
to authenticated;

create or replace function public.write_audit_log(
  actor_user_id uuid,
  project_id uuid,
  action text,
  metadata jsonb default '{}'::jsonb
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  audit_id uuid;
begin
  insert into public.audit_logs (actor_user_id, project_id, action, metadata)
  values (actor_user_id, project_id, action, coalesce(metadata, '{}'::jsonb))
  returning id into audit_id;

  return audit_id;
end;
$$;

revoke all on function public.write_audit_log(uuid, uuid, text, jsonb) from public;
grant execute on function public.write_audit_log(uuid, uuid, text, jsonb) to authenticated;
