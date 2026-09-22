create table if not exists public.entitlement_definitions (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  name text not null,
  description text not null,
  value_type text not null check (value_type in ('BOOLEAN','QUANTITY','UNLIMITED')),
  scope text not null check (scope in ('ACCOUNT','EVENT')),
  is_usage_tracked boolean not null default false,
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE')),
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists public.package_plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text not null,
  status text not null default 'DRAFT' check (status in ('DRAFT','ACTIVE','INACTIVE','ARCHIVED')),
  is_public boolean not null default false,
  is_add_on boolean not null default false,
  display_order integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists public.package_prices (
  id uuid primary key default gen_random_uuid(),
  package_plan_id uuid not null references public.package_plans(id) on delete cascade,
  currency text not null default 'UGX' check (currency in ('UGX')),
  amount_minor integer not null check (amount_minor >= 0),
  billing_interval text not null default 'ONE_TIME' check (billing_interval in ('ONE_TIME','MONTHLY','YEARLY')),
  status text not null default 'DRAFT' check (status in ('DRAFT','ACTIVE','INACTIVE','ARCHIVED')),
  starts_at timestamptz,
  ends_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  check (ends_at is null or starts_at is null or ends_at > starts_at)
);

create table if not exists public.package_entitlement_grants (
  id uuid primary key default gen_random_uuid(),
  package_plan_id uuid not null references public.package_plans(id) on delete cascade,
  entitlement_key text not null references public.entitlement_definitions(key),
  scope text not null check (scope in ('ACCOUNT','EVENT')),
  value_type text not null check (value_type in ('BOOLEAN','QUANTITY','UNLIMITED')),
  quantity integer,
  duration_days integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique(package_plan_id, entitlement_key),
  check (quantity is null or quantity >= 0),
  check (duration_days is null or duration_days > 0),
  check (
    (value_type = 'QUANTITY' and quantity is not null and quantity > 0)
    or (value_type in ('BOOLEAN','UNLIMITED') and quantity is null)
  )
);

create index if not exists idx_entitlement_definitions_status on public.entitlement_definitions(status);
create index if not exists idx_package_plans_public_status on public.package_plans(is_public, status, display_order);
create index if not exists idx_package_prices_plan_status on public.package_prices(package_plan_id, status, starts_at, ends_at);
create index if not exists idx_package_entitlement_grants_plan on public.package_entitlement_grants(package_plan_id);
create index if not exists idx_package_entitlement_grants_key on public.package_entitlement_grants(entitlement_key);

alter table public.entitlement_definitions enable row level security;
alter table public.package_plans enable row level security;
alter table public.package_prices enable row level security;
alter table public.package_entitlement_grants enable row level security;

drop policy if exists entitlement_definitions_public_active_select on public.entitlement_definitions;
create policy entitlement_definitions_public_active_select on public.entitlement_definitions
  for select using (status = 'ACTIVE' or public.is_platform_admin('admin.catalog.view'));

drop policy if exists entitlement_definitions_admin_mutate on public.entitlement_definitions;
create policy entitlement_definitions_admin_mutate on public.entitlement_definitions
  for all using (public.is_platform_admin('admin.catalog.manage'))
  with check (public.is_platform_admin('admin.catalog.manage'));

drop policy if exists package_plans_public_active_select on public.package_plans;
create policy package_plans_public_active_select on public.package_plans
  for select using ((status = 'ACTIVE' and is_public = true) or public.is_platform_admin('admin.catalog.view'));

drop policy if exists package_plans_admin_mutate on public.package_plans;
create policy package_plans_admin_mutate on public.package_plans
  for all using (public.is_platform_admin('admin.catalog.manage'))
  with check (public.is_platform_admin('admin.catalog.manage'));

drop policy if exists package_prices_public_active_select on public.package_prices;
create policy package_prices_public_active_select on public.package_prices
  for select using (
    (
      status = 'ACTIVE'
      and (starts_at is null or starts_at <= now())
      and (ends_at is null or ends_at > now())
      and exists (
        select 1
        from public.package_plans pp
        where pp.id = package_prices.package_plan_id
          and pp.status = 'ACTIVE'
          and pp.is_public = true
      )
    )
    or public.is_platform_admin('admin.catalog.view')
  );

drop policy if exists package_prices_admin_mutate on public.package_prices;
create policy package_prices_admin_mutate on public.package_prices
  for all using (public.is_platform_admin('admin.catalog.manage'))
  with check (public.is_platform_admin('admin.catalog.manage'));

drop policy if exists package_entitlement_grants_public_select on public.package_entitlement_grants;
create policy package_entitlement_grants_public_select on public.package_entitlement_grants
  for select using (
    exists (
      select 1
      from public.package_plans pp
      where pp.id = package_entitlement_grants.package_plan_id
        and pp.status = 'ACTIVE'
        and pp.is_public = true
    )
    or public.is_platform_admin('admin.catalog.view')
  );

drop policy if exists package_entitlement_grants_admin_mutate on public.package_entitlement_grants;
create policy package_entitlement_grants_admin_mutate on public.package_entitlement_grants
  for all using (public.is_platform_admin('admin.catalog.manage'))
  with check (public.is_platform_admin('admin.catalog.manage'));

insert into public.entitlement_definitions (key, name, description, value_type, scope, is_usage_tracked, status)
values
  ('events', 'Events', 'Number of event workspaces a customer account can create.', 'QUANTITY', 'ACCOUNT', true, 'ACTIVE'),
  ('guests_per_event', 'Guests per event', 'Maximum guest invitations allowed for each event workspace.', 'QUANTITY', 'EVENT', true, 'ACTIVE'),
  ('collaborators_per_event', 'Collaborators per event', 'Maximum account collaborators or committee users allowed for each event workspace.', 'QUANTITY', 'EVENT', true, 'ACTIVE'),
  ('vendors_per_event', 'Vendors per event', 'Maximum vendors that can be managed for each event workspace.', 'QUANTITY', 'EVENT', true, 'ACTIVE'),
  ('budget_management', 'Budget management', 'Access to event budget planning and contribution tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('rsvp_management', 'RSVP management', 'Access to guest invitation and RSVP tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('vendor_management', 'Vendor management', 'Access to vendor planning and booking coordination tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('meeting_management', 'Meeting management', 'Access to meeting coordination tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('task_management', 'Task management', 'Access to task coordination tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE')
on conflict (key) do update
set
  name = excluded.name,
  description = excluded.description,
  value_type = excluded.value_type,
  scope = excluded.scope,
  is_usage_tracked = excluded.is_usage_tracked,
  status = excluded.status,
  updated_at = now();

insert into public.package_plans (code, name, description, status, is_public, is_add_on, display_order, metadata)
values
  ('starter-event', 'Starter Event', 'A focused planning workspace for one ceremony with essential coordination tools.', 'ACTIVE', true, false, 10, '{"provisional": true}'::jsonb),
  ('family-coordination', 'Family Coordination', 'A larger family planning workspace with expanded guest, collaborator, and vendor coordination.', 'ACTIVE', true, false, 20, '{"provisional": true}'::jsonb),
  ('multi-event-planner', 'Multi-Event Planner', 'A broader planning option for customers coordinating multiple event workspaces.', 'ACTIVE', true, false, 30, '{"provisional": true}'::jsonb),
  ('extra-event', 'Extra Event', 'Add one more event workspace when a customer needs additional ceremony capacity.', 'ACTIVE', true, true, 110, '{"provisional": true}'::jsonb),
  ('extra-guests', 'Extra Guests', 'Add more guest invitation capacity per event.', 'ACTIVE', true, true, 120, '{"provisional": true}'::jsonb),
  ('extra-collaborators', 'Extra Collaborators', 'Add more collaborator capacity per event.', 'ACTIVE', true, true, 130, '{"provisional": true}'::jsonb)
on conflict (code) do update
set
  name = excluded.name,
  description = excluded.description,
  status = excluded.status,
  is_public = excluded.is_public,
  is_add_on = excluded.is_add_on,
  display_order = excluded.display_order,
  metadata = excluded.metadata,
  updated_at = now();

with package_grants(package_code, entitlement_key, scope, value_type, quantity, duration_days, metadata) as (
  values
    ('starter-event', 'events', 'ACCOUNT', 'QUANTITY', 1, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'guests_per_event', 'EVENT', 'QUANTITY', 150, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'collaborators_per_event', 'EVENT', 'QUANTITY', 6, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'vendors_per_event', 'EVENT', 'QUANTITY', 5, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'budget_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'rsvp_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'meeting_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('starter-event', 'task_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'events', 'ACCOUNT', 'QUANTITY', 1, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'guests_per_event', 'EVENT', 'QUANTITY', 400, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'collaborators_per_event', 'EVENT', 'QUANTITY', 20, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'vendors_per_event', 'EVENT', 'QUANTITY', 20, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'budget_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'rsvp_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'vendor_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'meeting_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('family-coordination', 'task_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'events', 'ACCOUNT', 'QUANTITY', 3, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'guests_per_event', 'EVENT', 'QUANTITY', 600, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'collaborators_per_event', 'EVENT', 'QUANTITY', 35, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'vendors_per_event', 'EVENT', 'QUANTITY', 30, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'budget_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'rsvp_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'vendor_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'meeting_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('multi-event-planner', 'task_management', 'ACCOUNT', 'BOOLEAN', null, null::integer, '{"provisional": true}'::jsonb),
    ('extra-event', 'events', 'ACCOUNT', 'QUANTITY', 1, null::integer, '{"provisional": true, "add_on": true}'::jsonb),
    ('extra-guests', 'guests_per_event', 'EVENT', 'QUANTITY', 100, null::integer, '{"provisional": true, "add_on": true}'::jsonb),
    ('extra-collaborators', 'collaborators_per_event', 'EVENT', 'QUANTITY', 5, null::integer, '{"provisional": true, "add_on": true}'::jsonb)
)
insert into public.package_entitlement_grants (package_plan_id, entitlement_key, scope, value_type, quantity, duration_days, metadata)
select pp.id, pg.entitlement_key, pg.scope, pg.value_type, pg.quantity, pg.duration_days, pg.metadata
from package_grants pg
join public.package_plans pp on pp.code = pg.package_code
on conflict (package_plan_id, entitlement_key) do update
set
  scope = excluded.scope,
  value_type = excluded.value_type,
  quantity = excluded.quantity,
  duration_days = excluded.duration_days,
  metadata = excluded.metadata,
  updated_at = now();
