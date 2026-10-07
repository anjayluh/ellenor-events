alter table public.project_communications
  add column if not exists expires_at timestamptz;

create index if not exists idx_project_communications_project_expires
  on public.project_communications(project_id, expires_at);

create or replace function public.can_view_project_communication(target_communication_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public
stable
as $$
declare
  target_project_id uuid;
  target_author_user_id uuid;
  target_type text;
  target_audience text;
  target_expires_at timestamptz;
  member_role text;
begin
  select pc.project_id, pc.author_user_id, pc.communication_type, pc.audience_mode, pc.expires_at
    into target_project_id, target_author_user_id, target_type, target_audience, target_expires_at
  from public.project_communications pc
  where pc.id = target_communication_id;

  if target_project_id is null then
    return false;
  end if;

  select pm.role into member_role
  from public.project_members pm
  where pm.project_id = target_project_id and pm.user_id = auth.uid();

  if member_role is null then
    return false;
  end if;

  if target_author_user_id = auth.uid()
    or public.can_manage_project_communications(target_project_id) then
    return true;
  end if;

  if target_expires_at is not null and target_expires_at <= now() then
    return false;
  end if;

  if target_type = 'PLANNING_NOTE' and member_role not in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER') then
    return false;
  end if;

  if target_audience = 'ALL_MEMBERS' then
    return member_role <> 'GUEST_VIEWER';
  end if;

  return exists (
    select 1
    from public.project_communication_recipients pcr
    where pcr.communication_id = target_communication_id
      and pcr.recipient_user_id = auth.uid()
  );
end;
$$;

drop policy if exists project_communications_update_managers on public.project_communications;
create policy project_communications_update_managers on public.project_communications
  for update
  using (public.can_manage_project_communications(project_id))
  with check (public.can_manage_project_communications(project_id));

drop policy if exists project_communication_recipients_select_visible on public.project_communication_recipients;
create policy project_communication_recipients_select_visible on public.project_communication_recipients
  for select using (
    (public.can_manage_project_communications(project_id) and public.can_view_project_communication(communication_id))
    or (recipient_user_id = auth.uid() and public.can_view_project_communication(communication_id))
  );

drop policy if exists project_communication_reads_select_own on public.project_communication_reads;
create policy project_communication_reads_select_own on public.project_communication_reads
  for select using (
    (user_id = auth.uid() and public.can_view_project_communication(communication_id))
    or (public.can_manage_project_communications(project_id) and public.can_view_project_communication(communication_id))
  );

drop policy if exists project_communication_reads_delete_own on public.project_communication_reads;
create policy project_communication_reads_delete_own on public.project_communication_reads
  for delete using (user_id = auth.uid() and public.can_view_project_communication(communication_id));
