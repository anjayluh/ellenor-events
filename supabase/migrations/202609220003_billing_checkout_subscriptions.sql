create table if not exists public.billing_customers (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references public.customer_accounts(id) on delete cascade,
  provider text not null default 'flutterwave',
  provider_customer_id text,
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique(customer_account_id),
  unique(provider, provider_customer_id)
);

create table if not exists public.customer_subscriptions (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references public.customer_accounts(id) on delete cascade,
  package_plan_id uuid not null references public.package_plans(id),
  package_price_id uuid references public.package_prices(id),
  status text not null default 'INCOMPLETE' check (status in ('INCOMPLETE','ACTIVE','PAST_DUE','CANCELLED','EXPIRED','FAILED')),
  access_source text not null default 'PAID' check (access_source in ('PAID','MARKETING')),
  currency text not null default 'UGX' check (currency in ('UGX')),
  amount_minor integer not null default 0 check (amount_minor >= 0),
  billing_interval text not null default 'MONTHLY' check (billing_interval in ('ONE_TIME','MONTHLY','YEARLY')),
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  cancelled_at timestamptz,
  started_at timestamptz,
  ended_at timestamptz,
  provider text not null default 'flutterwave',
  provider_subscription_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique(provider, provider_subscription_id)
);

create table if not exists public.payment_transactions (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references public.customer_accounts(id) on delete cascade,
  subscription_id uuid references public.customer_subscriptions(id) on delete set null,
  package_price_id uuid references public.package_prices(id),
  amount_minor integer not null check (amount_minor >= 0),
  currency text not null default 'UGX' check (currency in ('UGX')),
  provider text not null default 'flutterwave',
  provider_transaction_id text,
  provider_reference text not null,
  status text not null default 'INITIATED' check (status in ('INITIATED','PENDING','SUCCESSFUL','FAILED','CANCELLED','REFUNDED')),
  checkout_url text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique(provider, provider_reference),
  unique(provider, provider_transaction_id)
);

create table if not exists public.payment_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null default 'flutterwave',
  provider_event_id text not null,
  event_type text not null,
  provider_reference text,
  provider_transaction_id text,
  signature_valid boolean not null default false,
  status text not null default 'RECEIVED' check (status in ('RECEIVED','PROCESSED','IGNORED','FAILED')),
  payload jsonb not null default '{}'::jsonb,
  error text,
  processed_at timestamptz,
  created_at timestamptz not null default now(),
  unique(provider, provider_event_id)
);

create table if not exists public.marketing_access_tokens (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  package_plan_id uuid not null references public.package_plans(id),
  package_price_id uuid references public.package_prices(id),
  duration_days integer not null check (duration_days > 0),
  starts_at timestamptz,
  expires_at timestamptz,
  max_redemptions integer check (max_redemptions is null or max_redemptions > 0),
  redemption_count integer not null default 0 check (redemption_count >= 0),
  assigned_email text,
  assigned_user_id uuid references public.users(id),
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE','EXPIRED')),
  internal_notes text,
  created_by uuid references public.users(id),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  check (expires_at is null or starts_at is null or expires_at > starts_at)
);

create table if not exists public.marketing_access_token_redemptions (
  id uuid primary key default gen_random_uuid(),
  access_token_id uuid not null references public.marketing_access_tokens(id) on delete cascade,
  customer_account_id uuid not null references public.customer_accounts(id) on delete cascade,
  user_id uuid not null references public.users(id),
  subscription_id uuid not null references public.customer_subscriptions(id) on delete cascade,
  redeemed_at timestamptz not null default now(),
  unique(access_token_id, customer_account_id),
  unique(access_token_id, user_id)
);

create index if not exists idx_billing_customers_account on public.billing_customers(customer_account_id, status);
create index if not exists idx_customer_subscriptions_account_status on public.customer_subscriptions(customer_account_id, status);
create index if not exists idx_customer_subscriptions_period_end on public.customer_subscriptions(current_period_end);
create index if not exists idx_payment_transactions_account_status on public.payment_transactions(customer_account_id, status);
create index if not exists idx_payment_transactions_subscription on public.payment_transactions(subscription_id);
create index if not exists idx_payment_events_reference on public.payment_events(provider, provider_reference);
create index if not exists idx_marketing_access_tokens_code_status on public.marketing_access_tokens(code, status);
create index if not exists idx_marketing_token_redemptions_account on public.marketing_access_token_redemptions(customer_account_id);

alter table public.billing_customers enable row level security;
alter table public.customer_subscriptions enable row level security;
alter table public.payment_transactions enable row level security;
alter table public.payment_events enable row level security;
alter table public.marketing_access_tokens enable row level security;
alter table public.marketing_access_token_redemptions enable row level security;

drop policy if exists billing_customers_select_members_admins on public.billing_customers;
create policy billing_customers_select_members_admins on public.billing_customers
  for select using (public.is_customer_account_member(customer_account_id) or public.is_platform_admin('admin.billing.view'));

drop policy if exists billing_customers_admin_mutate on public.billing_customers;
create policy billing_customers_admin_mutate on public.billing_customers
  for all using (public.is_platform_admin('admin.billing.manage'))
  with check (public.is_platform_admin('admin.billing.manage'));

drop policy if exists customer_subscriptions_select_members_admins on public.customer_subscriptions;
create policy customer_subscriptions_select_members_admins on public.customer_subscriptions
  for select using (public.is_customer_account_member(customer_account_id) or public.is_platform_admin('admin.billing.view'));

drop policy if exists customer_subscriptions_customer_checkout_insert on public.customer_subscriptions;
create policy customer_subscriptions_customer_checkout_insert on public.customer_subscriptions
  for insert with check (
    public.is_customer_account_member(customer_account_id)
    and status = 'INCOMPLETE'
    and access_source = 'PAID'
  );

drop policy if exists customer_subscriptions_admin_mutate on public.customer_subscriptions;
create policy customer_subscriptions_admin_mutate on public.customer_subscriptions
  for all using (public.is_platform_admin('admin.billing.manage'))
  with check (public.is_platform_admin('admin.billing.manage'));

drop policy if exists payment_transactions_select_members_admins on public.payment_transactions;
create policy payment_transactions_select_members_admins on public.payment_transactions
  for select using (public.is_customer_account_member(customer_account_id) or public.is_platform_admin('admin.billing.view'));

drop policy if exists payment_transactions_customer_checkout_insert on public.payment_transactions;
create policy payment_transactions_customer_checkout_insert on public.payment_transactions
  for insert with check (
    public.is_customer_account_member(customer_account_id)
    and status = 'INITIATED'
  );

drop policy if exists payment_transactions_admin_mutate on public.payment_transactions;
create policy payment_transactions_admin_mutate on public.payment_transactions
  for all using (public.is_platform_admin('admin.billing.manage'))
  with check (public.is_platform_admin('admin.billing.manage'));

drop policy if exists payment_events_admin_select on public.payment_events;
create policy payment_events_admin_select on public.payment_events
  for select using (public.is_platform_admin('admin.billing.view'));

drop policy if exists payment_events_admin_mutate on public.payment_events;
create policy payment_events_admin_mutate on public.payment_events
  for all using (public.is_platform_admin('admin.billing.manage'))
  with check (public.is_platform_admin('admin.billing.manage'));

drop policy if exists marketing_access_tokens_admin_select on public.marketing_access_tokens;
create policy marketing_access_tokens_admin_select on public.marketing_access_tokens
  for select using (public.is_platform_admin('admin.billing.view'));

drop policy if exists marketing_access_tokens_admin_mutate on public.marketing_access_tokens;
create policy marketing_access_tokens_admin_mutate on public.marketing_access_tokens
  for all using (public.is_platform_admin('admin.billing.manage'))
  with check (public.is_platform_admin('admin.billing.manage'));

drop policy if exists marketing_token_redemptions_select_members_admins on public.marketing_access_token_redemptions;
create policy marketing_token_redemptions_select_members_admins on public.marketing_access_token_redemptions
  for select using (public.is_customer_account_member(customer_account_id) or public.is_platform_admin('admin.billing.view'));

drop policy if exists marketing_token_redemptions_admin_mutate on public.marketing_access_token_redemptions;
create policy marketing_token_redemptions_admin_mutate on public.marketing_access_token_redemptions
  for all using (public.is_platform_admin('admin.billing.manage'))
  with check (public.is_platform_admin('admin.billing.manage'));

insert into public.entitlement_definitions (key, name, description, value_type, scope, is_usage_tracked, status)
values
  ('account_owners', 'Account owners', 'Maximum customer-account owners supported by the package.', 'QUANTITY', 'ACCOUNT', true, 'ACTIVE'),
  ('committee_members_per_event', 'Committee members per event', 'Maximum committee members supported for each event.', 'QUANTITY', 'EVENT', true, 'ACTIVE'),
  ('invitation_emails_per_month', 'Invitation emails per month', 'Monthly invitation email sending capacity.', 'QUANTITY', 'ACCOUNT', true, 'ACTIVE'),
  ('event_management', 'Event management', 'Access to event workspace management tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('committee_management', 'Committee management', 'Access to committee coordination tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('invitations', 'Invitations', 'Access to invitation sending tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('introduction_family_structure', 'Introduction ceremony family structure', 'Access to introduction ceremony family structure tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('documents_notes', 'Documents and notes', 'Access to documents and planning notes tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE'),
  ('payment_deposit_tracking', 'Payment and deposit tracking', 'Access to payment and deposit tracking tools.', 'BOOLEAN', 'ACCOUNT', false, 'ACTIVE')
on conflict (key) do update
set
  name = excluded.name,
  description = excluded.description,
  value_type = excluded.value_type,
  scope = excluded.scope,
  is_usage_tracked = excluded.is_usage_tracked,
  status = excluded.status,
  updated_at = now();

insert into public.package_prices (package_plan_id, currency, amount_minor, billing_interval, status, starts_at)
select pp.id, 'UGX', 30000, 'MONTHLY', 'ACTIVE', now()
from public.package_plans pp
where pp.code = 'starter-event'
  and not exists (
    select 1 from public.package_prices existing
    where existing.package_plan_id = pp.id
      and existing.currency = 'UGX'
      and existing.amount_minor = 30000
      and existing.billing_interval = 'MONTHLY'
  );

insert into public.package_prices (package_plan_id, currency, amount_minor, billing_interval, status, starts_at)
select pp.id, 'UGX', 50000, 'MONTHLY', 'ACTIVE', now()
from public.package_plans pp
where pp.code = 'family-coordination'
  and not exists (
    select 1 from public.package_prices existing
    where existing.package_plan_id = pp.id
      and existing.currency = 'UGX'
      and existing.amount_minor = 50000
      and existing.billing_interval = 'MONTHLY'
  );

with updated_grants(package_code, entitlement_key, scope, value_type, quantity, metadata) as (
  values
    ('starter-event', 'events', 'ACCOUNT', 'QUANTITY', 1, '{"source":"phase3_billing","intended_package":"Event"}'::jsonb),
    ('starter-event', 'account_owners', 'ACCOUNT', 'QUANTITY', 1, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'collaborators_per_event', 'EVENT', 'QUANTITY', 10, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'committee_members_per_event', 'EVENT', 'QUANTITY', 20, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'vendors_per_event', 'EVENT', 'QUANTITY', 20, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'guests_per_event', 'EVENT', 'QUANTITY', 300, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'invitation_emails_per_month', 'ACCOUNT', 'QUANTITY', 500, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'event_management', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'committee_management', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'invitations', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'introduction_family_structure', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'documents_notes', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('starter-event', 'payment_deposit_tracking', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'events', 'ACCOUNT', 'QUANTITY', 1, '{"source":"phase3_billing","intended_package":"Family"}'::jsonb),
    ('family-coordination', 'account_owners', 'ACCOUNT', 'QUANTITY', 2, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'collaborators_per_event', 'EVENT', 'QUANTITY', 25, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'committee_members_per_event', 'EVENT', 'QUANTITY', 50, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'vendors_per_event', 'EVENT', 'QUANTITY', 40, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'guests_per_event', 'EVENT', 'QUANTITY', 500, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'invitation_emails_per_month', 'ACCOUNT', 'QUANTITY', 1000, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'event_management', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'committee_management', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'invitations', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'introduction_family_structure', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'documents_notes', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb),
    ('family-coordination', 'payment_deposit_tracking', 'ACCOUNT', 'BOOLEAN', null, '{"source":"phase3_billing"}'::jsonb)
)
insert into public.package_entitlement_grants (package_plan_id, entitlement_key, scope, value_type, quantity, metadata)
select pp.id, ug.entitlement_key, ug.scope, ug.value_type, ug.quantity, ug.metadata
from updated_grants ug
join public.package_plans pp on pp.code = ug.package_code
on conflict (package_plan_id, entitlement_key) do update
set
  scope = excluded.scope,
  value_type = excluded.value_type,
  quantity = excluded.quantity,
  metadata = excluded.metadata,
  updated_at = now();
