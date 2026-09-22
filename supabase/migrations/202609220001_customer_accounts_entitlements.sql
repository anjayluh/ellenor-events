create table if not exists public.customer_accounts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  status text not null default 'ACTIVE' check (status in ('LEAD','ACTIVE','SUSPENDED','CANCELLED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists public.customer_account_members (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references public.customer_accounts(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  role text not null default 'MEMBER' check (role in ('OWNER','MEMBER')),
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE')),
  created_at timestamptz not null default now(),
  unique(customer_account_id, user_id)
);

create unique index if not exists uq_customer_account_one_active_owner
  on public.customer_account_members(customer_account_id)
  where role = 'OWNER' and status = 'ACTIVE';

create table if not exists public.account_entitlements (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references public.customer_accounts(id) on delete cascade,
  key text not null,
  quantity integer,
  used_quantity integer not null default 0,
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE','EXPIRED','CANCELLED')),
  starts_at timestamptz,
  expires_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  check (quantity is null or quantity >= 0),
  check (used_quantity >= 0)
);

create index if not exists idx_customer_account_members_user on public.customer_account_members(user_id, status);
create index if not exists idx_customer_account_members_account on public.customer_account_members(customer_account_id, status);
create index if not exists idx_account_entitlements_account_key on public.account_entitlements(customer_account_id, key, status);

alter table public.projects
  add column if not exists customer_account_id uuid references public.customer_accounts(id);

create index if not exists idx_projects_customer_account on public.projects(customer_account_id);

do $$
declare
  owner_record record;
  account_id uuid;
begin
  for owner_record in
    select distinct p.owner_user_id
    from public.projects p
    where p.customer_account_id is null
  loop
    select cam.customer_account_id
      into account_id
    from public.customer_account_members cam
    join public.customer_accounts ca on ca.id = cam.customer_account_id
    where cam.user_id = owner_record.owner_user_id
      and cam.role = 'OWNER'
      and cam.status = 'ACTIVE'
      and ca.status in ('LEAD','ACTIVE')
    order by ca.created_at asc
    limit 1;

    if account_id is null then
      insert into public.customer_accounts (name, status)
      select coalesce(nullif(u.name, ''), u.email, u.phone, 'Ellenor Events Customer') || ' Account', 'ACTIVE'
      from public.users u
      where u.id = owner_record.owner_user_id
      returning id into account_id;

      insert into public.customer_account_members (customer_account_id, user_id, role, status)
      values (account_id, owner_record.owner_user_id, 'OWNER', 'ACTIVE')
      on conflict (customer_account_id, user_id) do nothing;
    end if;

    update public.projects
    set customer_account_id = account_id
    where owner_user_id = owner_record.owner_user_id
      and customer_account_id is null;
  end loop;
end $$;

insert into public.account_entitlements (customer_account_id, key, quantity, used_quantity, status, starts_at, metadata)
select
  p.customer_account_id,
  'events',
  null,
  count(p.id)::integer,
  'ACTIVE',
  now(),
  '{"source":"migration_backfill","compatibility":true}'::jsonb
from public.projects p
where p.customer_account_id is not null
  and not exists (
    select 1
    from public.account_entitlements ae
    where ae.customer_account_id = p.customer_account_id
      and ae.key = 'events'
  )
group by p.customer_account_id;

alter table public.projects
  alter column customer_account_id set not null;

alter table public.customer_accounts enable row level security;
alter table public.customer_account_members enable row level security;
alter table public.account_entitlements enable row level security;

create or replace function public.is_customer_account_member(target_customer_account_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1
    from public.customer_account_members cam
    where cam.customer_account_id = target_customer_account_id
      and cam.user_id = auth.uid()
      and cam.status = 'ACTIVE'
  );
$$;

drop policy if exists customer_accounts_select_members on public.customer_accounts;
create policy customer_accounts_select_members on public.customer_accounts
  for select using (public.is_customer_account_member(id) or public.is_platform_admin('admin.projects.view'));

drop policy if exists customer_account_members_select_members on public.customer_account_members;
create policy customer_account_members_select_members on public.customer_account_members
  for select using (public.is_customer_account_member(customer_account_id) or public.is_platform_admin('admin.projects.view'));

drop policy if exists account_entitlements_select_members on public.account_entitlements;
create policy account_entitlements_select_members on public.account_entitlements
  for select using (public.is_customer_account_member(customer_account_id) or public.is_platform_admin('admin.projects.view'));

drop policy if exists customer_accounts_platform_admin_mutate on public.customer_accounts;
create policy customer_accounts_platform_admin_mutate on public.customer_accounts
  for all using (public.is_platform_admin('admin.projects.manage'))
  with check (public.is_platform_admin('admin.projects.manage'));

drop policy if exists customer_account_members_platform_admin_mutate on public.customer_account_members;
create policy customer_account_members_platform_admin_mutate on public.customer_account_members
  for all using (public.is_platform_admin('admin.projects.manage'))
  with check (public.is_platform_admin('admin.projects.manage'));

drop policy if exists account_entitlements_platform_admin_mutate on public.account_entitlements;
create policy account_entitlements_platform_admin_mutate on public.account_entitlements
  for all using (public.is_platform_admin('admin.projects.manage'))
  with check (public.is_platform_admin('admin.projects.manage'));

drop policy if exists projects_select_account_members on public.projects;
create policy projects_select_account_members on public.projects
  for select using (public.is_customer_account_member(customer_account_id));

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
  account_id uuid;
  entitlement_id uuid;
  entitlement_quantity integer;
  entitlement_used integer;
begin
  if owner_user_id <> auth.uid() then
    raise insufficient_privilege using message = 'Project owner must match authenticated user';
  end if;

  select cam.customer_account_id
    into account_id
  from public.customer_account_members cam
  join public.customer_accounts ca on ca.id = cam.customer_account_id
  where cam.user_id = owner_user_id
    and cam.role = 'OWNER'
    and cam.status = 'ACTIVE'
    and ca.status in ('LEAD','ACTIVE')
  order by ca.created_at asc
  limit 1;

  if account_id is null then
    insert into public.customer_accounts (name, status)
    select coalesce(nullif(u.name, ''), u.email, u.phone, 'Ellenor Events Customer') || ' Account', 'ACTIVE'
    from public.users u
    where u.id = owner_user_id
    returning id into account_id;

    insert into public.customer_account_members (customer_account_id, user_id, role, status)
    values (account_id, owner_user_id, 'OWNER', 'ACTIVE');
  end if;

  select ae.id, ae.quantity, ae.used_quantity
    into entitlement_id, entitlement_quantity, entitlement_used
  from public.account_entitlements ae
  where ae.customer_account_id = account_id
    and ae.key = 'events'
    and ae.status = 'ACTIVE'
    and (ae.starts_at is null or ae.starts_at <= now())
    and (ae.expires_at is null or ae.expires_at > now())
    and (ae.quantity is null or ae.used_quantity + 1 <= ae.quantity)
  order by ae.created_at asc
  limit 1;

  if entitlement_id is null then
    insert into public.account_entitlements (customer_account_id, key, quantity, used_quantity, status, starts_at, metadata)
    values (account_id, 'events', null, 0, 'ACTIVE', now(), '{"source":"compatibility_foundation","compatibility":true}'::jsonb)
    returning id, quantity, used_quantity into entitlement_id, entitlement_quantity, entitlement_used;
  end if;

  insert into public.projects (customer_account_id, type, title, owner_user_id, partner_user_id, event_date, status)
  values (account_id, project_type, project_title, owner_user_id, partner_user_id, event_date, 'active')
  returning id into project_id;

  insert into public.project_members (project_id, user_id, role, permissions_level, budget_visibility_mode)
  values (project_id, owner_user_id, 'OWNER', 'admin', 'FULL_ACCESS');

  insert into public.project_settings (project_id)
  values (project_id);

  update public.account_entitlements
  set used_quantity = used_quantity + 1,
      updated_at = now()
  where id = entitlement_id;

  return project_id;
end;
$$;

revoke all on function public.create_project_with_owner(text, text, uuid, uuid, date) from public;
grant execute on function public.create_project_with_owner(text, text, uuid, uuid, date) to authenticated;
