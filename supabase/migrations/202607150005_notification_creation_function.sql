drop policy if exists notifications_insert_committee on public.notifications;

create or replace function public.create_notification(
  project_id uuid,
  recipient_user_id uuid,
  recipient_contact text,
  channel text,
  provider text,
  subject text,
  body text,
  provider_payload jsonb,
  max_attempts integer default 3
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  notification_id uuid;
begin
  if not public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']) then
    raise insufficient_privilege using message = 'Insufficient project permissions to create notifications';
  end if;

  insert into public.notifications (
    project_id,
    recipient_user_id,
    recipient_contact,
    channel,
    provider,
    subject,
    body,
    provider_payload,
    max_attempts
  )
  values (
    project_id,
    recipient_user_id,
    recipient_contact,
    channel,
    provider,
    subject,
    body,
    coalesce(provider_payload, '{}'::jsonb),
    coalesce(max_attempts, 3)
  )
  returning id into notification_id;

  return notification_id;
end;
$$;

revoke all on function public.create_notification(uuid, uuid, text, text, text, text, text, jsonb, integer) from public;
grant execute on function public.create_notification(uuid, uuid, text, text, text, text, text, jsonb, integer) to authenticated;
