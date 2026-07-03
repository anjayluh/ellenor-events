alter table users enable row level security;
alter table projects enable row level security;
alter table project_members enable row level security;
alter table project_links enable row level security;
alter table participants enable row level security;
alter table vendors enable row level security;
alter table invites enable row level security;
alter table meetings enable row level security;
alter table meeting_rsvp enable row level security;
alter table tasks enable row level security;
alter table budgets enable row level security;
alter table contributions enable row level security;
alter table testimonials enable row level security;

create or replace function public.is_project_member(target_project_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1
    from project_members pm
    where pm.project_id = target_project_id
      and pm.user_id = auth.uid()
  );
$$;

create or replace function public.has_project_role(target_project_id uuid, allowed_roles text[])
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1
    from project_members pm
    where pm.project_id = target_project_id
      and pm.user_id = auth.uid()
      and pm.role = any(allowed_roles)
  );
$$;

create or replace function public.shares_project_with_user(target_user_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select target_user_id = auth.uid()
    or exists (
      select 1
      from project_members mine
      join project_members theirs on theirs.project_id = mine.project_id
      where mine.user_id = auth.uid()
        and theirs.user_id = target_user_id
    );
$$;

create policy users_select_related on users
  for select using (public.shares_project_with_user(id));

create policy users_insert_self on users
  for insert with check (id = auth.uid());

create policy users_update_self on users
  for update using (id = auth.uid()) with check (id = auth.uid());

create policy projects_select_members on projects
  for select using (public.is_project_member(id));

create policy projects_insert_owner on projects
  for insert with check (owner_user_id = auth.uid());

create policy projects_update_admins on projects
  for update using (public.has_project_role(id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy project_members_select_members on project_members
  for select using (public.is_project_member(project_id));

create policy project_members_insert_admins on project_members
  for insert with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy project_members_update_admins on project_members
  for update using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy project_members_delete_owners_partners on project_members
  for delete using (public.has_project_role(project_id, array['OWNER','PARTNER']));

create policy project_links_select_members on project_links
  for select using (public.is_project_member(primary_project_id) or public.is_project_member(linked_project_id));

create policy project_links_mutate_admins on project_links
  for all using (
    public.has_project_role(primary_project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR'])
    and public.has_project_role(linked_project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR'])
  ) with check (
    public.has_project_role(primary_project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR'])
    and public.has_project_role(linked_project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR'])
  );

create policy participants_select_members on participants
  for select using (public.is_project_member(project_id));

create policy participants_mutate_admins on participants
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy vendors_select_members on vendors
  for select using (public.is_project_member(project_id));

create policy vendors_mutate_admins on vendors
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy invites_select_admins on invites
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy invites_mutate_admins on invites
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy meetings_select_members on meetings
  for select using (public.is_project_member(project_id));

create policy meetings_mutate_committee on meetings
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy meeting_rsvp_select_project_members on meeting_rsvp
  for select using (
    exists (
      select 1 from meetings m
      where m.id = meeting_rsvp.meeting_id
        and public.is_project_member(m.project_id)
    )
  );

create policy meeting_rsvp_insert_self on meeting_rsvp
  for insert with check (
    user_id = auth.uid()
    and exists (
      select 1 from meetings m
      where m.id = meeting_rsvp.meeting_id
        and public.is_project_member(m.project_id)
    )
  );

create policy meeting_rsvp_update_self on meeting_rsvp
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy tasks_select_members on tasks
  for select using (public.is_project_member(project_id));

create policy tasks_mutate_committee on tasks
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy budgets_select_members on budgets
  for select using (public.is_project_member(project_id));

create policy budgets_mutate_owners_partners on budgets
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER']));

create policy contributions_select_members on contributions
  for select using (public.is_project_member(project_id));

create policy contributions_mutate_committee on contributions
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy testimonials_select_members on testimonials
  for select using (public.is_project_member(project_id));

create policy testimonials_mutate_admins on testimonials
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));
