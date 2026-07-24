alter table public.staff_members drop constraint if exists staff_members_role_check;
alter table public.staff_members
  add column if not exists permissions jsonb not null default '{"permissions": []}'::jsonb,
  add constraint staff_members_role_check check (role in ('SUPER_ADMIN','PLATFORM_ADMIN','OPERATIONS_MANAGER','SUPPORT_AGENT','STAFF_VIEWER'));

alter table public.project_members
  add column if not exists permissions jsonb not null default '{"permissions": []}'::jsonb;

alter table public.invites
  add column if not exists permissions jsonb not null default '{"permissions": []}'::jsonb,
  add column if not exists budget_visibility_mode text not null default 'NO_ACCESS' check (budget_visibility_mode in ('FULL_ACCESS','SUMMARY_ACCESS','CONTRIBUTION_ONLY','NO_ACCESS'));

alter table public.vendors drop constraint if exists vendors_status_check;
alter table public.vendors
  add constraint vendors_status_check check (status in ('shortlisted','quote_requested','preferred','booked','rejected','contacted','confirmed','declined','completed'));

alter table public.budget_line_items
  add column if not exists item_name text,
  add column if not exists unit_cost numeric(12, 2) not null default 0,
  add column if not exists quantity numeric(12, 2) not null default 1,
  add column if not exists total_cost numeric(12, 2) not null default 0,
  add column if not exists deposited_amount numeric(12, 2) not null default 0,
  add column if not exists balance numeric(12, 2) not null default 0,
  add column if not exists next_deposit_date date,
  add column if not exists payment_details text;

update public.budget_line_items
set
  item_name = coalesce(item_name, description),
  unit_cost = case when coalesce(unit_cost, 0) = 0 then coalesce(estimated_amount, 0) else unit_cost end,
  total_cost = case when coalesce(total_cost, 0) = 0 then coalesce(estimated_amount, 0) else total_cost end,
  deposited_amount = case when coalesce(deposited_amount, 0) = 0 then coalesce(actual_amount, 0) else deposited_amount end,
  balance = case when coalesce(balance, 0) = 0 then greatest(coalesce(estimated_amount, 0) - coalesce(actual_amount, 0), 0) else balance end;

create table if not exists public.guest_invites (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  guest_name text not null,
  email text,
  phone text,
  invitation_card_url text,
  token text unique not null,
  status text not null default 'draft' check (status in ('draft','sent','responded','cancelled')),
  attendance_status text not null default 'pending' check (attendance_status in ('pending','accepted','declined','cancelled','confirmed','rejected')),
  sent_count integer not null default 0,
  last_sent_at timestamptz,
  responded_at timestamptz,
  notes text,
  created_at timestamptz default now(),
  check (email is not null or phone is not null)
);

create table if not exists public.vendor_profiles (
  user_id uuid primary key references public.users(id) on delete cascade,
  business_name text not null,
  category text not null,
  contact_email text,
  contact_phone text,
  location text,
  bio text,
  payment_details text,
  status text not null default 'active' check (status in ('active','hidden','suspended')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.vendor_portfolio_items (
  id uuid primary key default gen_random_uuid(),
  vendor_user_id uuid not null references public.vendor_profiles(user_id) on delete cascade,
  title text not null,
  image_url text not null,
  description text,
  created_at timestamptz default now()
);

create table if not exists public.vendor_bookings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  vendor_user_id uuid not null references public.vendor_profiles(user_id) on delete cascade,
  requested_by uuid not null references public.users(id),
  status text not null default 'requested' check (status in ('requested','meeting_requested','meeting_scheduled','booked','declined','completed','cancelled')),
  meeting_requested_at timestamptz,
  meeting_notes text,
  quoted_amount numeric(12, 2) not null default 0,
  agreed_amount numeric(12, 2) not null default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(project_id, vendor_user_id)
);

create table if not exists public.vendor_payments (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null references public.vendor_bookings(id) on delete cascade,
  amount numeric(12, 2) not null default 0,
  received_at date,
  payment_method text,
  payment_reference text,
  notes text,
  created_at timestamptz default now(),
  check (amount >= 0)
);

create index if not exists idx_guest_invites_project on public.guest_invites(project_id);
create index if not exists idx_guest_invites_token on public.guest_invites(token);
create index if not exists idx_guest_invites_attendance on public.guest_invites(project_id, attendance_status);
create index if not exists idx_vendor_profiles_category_status on public.vendor_profiles(category, status);
create index if not exists idx_vendor_portfolio_vendor on public.vendor_portfolio_items(vendor_user_id);
create index if not exists idx_vendor_bookings_project on public.vendor_bookings(project_id);
create index if not exists idx_vendor_bookings_vendor on public.vendor_bookings(vendor_user_id);
create index if not exists idx_vendor_payments_booking on public.vendor_payments(booking_id);

alter table public.guest_invites enable row level security;
alter table public.vendor_profiles enable row level security;
alter table public.vendor_portfolio_items enable row level security;
alter table public.vendor_bookings enable row level security;
alter table public.vendor_payments enable row level security;

create or replace function public.is_platform_admin(required_permission text default null)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1
    from public.staff_members sm
    where sm.user_id = auth.uid()
      and sm.status = 'active'
      and (
        sm.role = 'SUPER_ADMIN'
        or required_permission is null
        or (sm.permissions -> 'permissions') ? required_permission
      )
  );
$$;

drop policy if exists users_select_platform_admins on public.users;
create policy users_select_platform_admins on public.users
  for select using (public.is_platform_admin('admin.users.view'));

drop policy if exists users_insert_platform_admins on public.users;
create policy users_insert_platform_admins on public.users
  for insert with check (public.is_platform_admin('admin.users.manage') or public.is_platform_admin('admin.permissions.manage'));

drop policy if exists users_update_platform_admins on public.users;
create policy users_update_platform_admins on public.users
  for update using (public.is_platform_admin('admin.users.manage'))
  with check (public.is_platform_admin('admin.users.manage'));

drop policy if exists staff_members_select_platform_admins on public.staff_members;
create policy staff_members_select_platform_admins on public.staff_members
  for select using (public.is_platform_admin('admin.permissions.manage') or public.is_platform_admin('admin.users.view'));

drop policy if exists staff_members_mutate_permission_admins on public.staff_members;
create policy staff_members_mutate_permission_admins on public.staff_members
  for all using (public.is_platform_admin('admin.permissions.manage'))
  with check (public.is_platform_admin('admin.permissions.manage'));

drop policy if exists guest_invites_select_admins on public.guest_invites;
create policy guest_invites_select_admins on public.guest_invites
  for select using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

drop policy if exists guest_invites_mutate_admins on public.guest_invites;
create policy guest_invites_mutate_admins on public.guest_invites
  for all using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

drop policy if exists guest_invites_public_token_select on public.guest_invites;
create policy guest_invites_public_token_select on public.guest_invites
  for select using (token is not null);

drop policy if exists guest_invites_public_token_update on public.guest_invites;
create policy guest_invites_public_token_update on public.guest_invites
  for update using (token is not null)
  with check (token is not null);

drop policy if exists vendor_profiles_public_read_active on public.vendor_profiles;
create policy vendor_profiles_public_read_active on public.vendor_profiles
  for select using (status = 'active' or user_id = auth.uid());

drop policy if exists vendor_profiles_self_insert on public.vendor_profiles;
create policy vendor_profiles_self_insert on public.vendor_profiles
  for insert with check (user_id = auth.uid());

drop policy if exists vendor_profiles_self_update on public.vendor_profiles;
create policy vendor_profiles_self_update on public.vendor_profiles
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists vendor_portfolio_read_active on public.vendor_portfolio_items;
create policy vendor_portfolio_read_active on public.vendor_portfolio_items
  for select using (
    vendor_user_id = auth.uid()
    or exists (
      select 1 from public.vendor_profiles vp
      where vp.user_id = vendor_portfolio_items.vendor_user_id
        and vp.status = 'active'
    )
  );

drop policy if exists vendor_portfolio_self_mutate on public.vendor_portfolio_items;
create policy vendor_portfolio_self_mutate on public.vendor_portfolio_items
  for all using (vendor_user_id = auth.uid()) with check (vendor_user_id = auth.uid());

drop policy if exists vendor_bookings_select_related on public.vendor_bookings;
create policy vendor_bookings_select_related on public.vendor_bookings
  for select using (vendor_user_id = auth.uid() or public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

drop policy if exists vendor_bookings_project_admin_insert on public.vendor_bookings;
create policy vendor_bookings_project_admin_insert on public.vendor_bookings
  for insert with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

drop policy if exists vendor_bookings_related_update on public.vendor_bookings;
create policy vendor_bookings_related_update on public.vendor_bookings
  for update using (vendor_user_id = auth.uid() or public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (vendor_user_id = auth.uid() or public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

drop policy if exists vendor_payments_select_related on public.vendor_payments;
create policy vendor_payments_select_related on public.vendor_payments
  for select using (
    exists (
      select 1 from public.vendor_bookings vb
      where vb.id = vendor_payments.booking_id
        and (vb.vendor_user_id = auth.uid() or public.has_project_role(vb.project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
    )
  );

drop policy if exists vendor_payments_vendor_insert on public.vendor_payments;
create policy vendor_payments_vendor_insert on public.vendor_payments
  for insert with check (
    exists (
      select 1 from public.vendor_bookings vb
      where vb.id = vendor_payments.booking_id
        and vb.vendor_user_id = auth.uid()
    )
  );

create or replace function public.grant_configured_super_admin()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if lower(coalesce(new.email, '')) = 'anjayluh.wakabi@gmail.com' then
    insert into public.staff_members (user_id, role, status, permissions)
    values (new.id, 'SUPER_ADMIN', 'active', '{"permissions": []}'::jsonb)
    on conflict (user_id) do update
    set role = 'SUPER_ADMIN', status = 'active';
  end if;
  return new;
end;
$$;

drop trigger if exists grant_configured_super_admin_on_user on public.users;
create trigger grant_configured_super_admin_on_user
  after insert or update of email on public.users
  for each row execute function public.grant_configured_super_admin();

insert into public.staff_members (user_id, role, status, permissions)
select id, 'SUPER_ADMIN', 'active', '{"permissions": []}'::jsonb
from public.users
where lower(email) = 'anjayluh.wakabi@gmail.com'
on conflict (user_id) do update
set role = 'SUPER_ADMIN', status = 'active';
