create extension if not exists pgcrypto;

create table users (
  id uuid primary key default gen_random_uuid(),
  name text,
  phone text unique,
  email text unique,
  created_at timestamptz default now(),
  check (phone is not null or email is not null)
);

create table customer_accounts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  status text not null default 'ACTIVE' check (status in ('LEAD','ACTIVE','SUSPENDED','CANCELLED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table customer_account_members (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references customer_accounts(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null default 'MEMBER' check (role in ('OWNER','MEMBER')),
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE')),
  created_at timestamptz not null default now(),
  unique(customer_account_id, user_id)
);

create table account_entitlements (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references customer_accounts(id) on delete cascade,
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

create table entitlement_definitions (
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

create table package_plans (
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

create table package_prices (
  id uuid primary key default gen_random_uuid(),
  package_plan_id uuid not null references package_plans(id) on delete cascade,
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

create table package_entitlement_grants (
  id uuid primary key default gen_random_uuid(),
  package_plan_id uuid not null references package_plans(id) on delete cascade,
  entitlement_key text not null references entitlement_definitions(key),
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

create table billing_customers (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references customer_accounts(id) on delete cascade,
  provider text not null default 'flutterwave',
  provider_customer_id text,
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique(customer_account_id),
  unique(provider, provider_customer_id)
);

create table customer_subscriptions (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references customer_accounts(id) on delete cascade,
  package_plan_id uuid not null references package_plans(id),
  package_price_id uuid references package_prices(id),
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

create table payment_transactions (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references customer_accounts(id) on delete cascade,
  subscription_id uuid references customer_subscriptions(id) on delete set null,
  package_price_id uuid references package_prices(id),
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

create table payment_events (
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

create table marketing_access_tokens (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  package_plan_id uuid not null references package_plans(id),
  package_price_id uuid references package_prices(id),
  duration_days integer not null check (duration_days > 0),
  starts_at timestamptz,
  expires_at timestamptz,
  max_redemptions integer check (max_redemptions is null or max_redemptions > 0),
  redemption_count integer not null default 0 check (redemption_count >= 0),
  assigned_email text,
  assigned_user_id uuid references users(id),
  status text not null default 'ACTIVE' check (status in ('ACTIVE','INACTIVE','EXPIRED')),
  internal_notes text,
  created_by uuid references users(id),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  check (expires_at is null or starts_at is null or expires_at > starts_at),
  constraint ck_marketing_access_token_redemption_max check (max_redemptions is null or redemption_count <= max_redemptions)
);

create table marketing_access_token_redemptions (
  id uuid primary key default gen_random_uuid(),
  access_token_id uuid not null references marketing_access_tokens(id) on delete cascade,
  customer_account_id uuid not null references customer_accounts(id) on delete cascade,
  user_id uuid not null references users(id),
  subscription_id uuid not null references customer_subscriptions(id) on delete cascade,
  redeemed_at timestamptz not null default now(),
  unique(access_token_id, customer_account_id),
  unique(access_token_id, user_id)
);

create table staff_members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  role text not null default 'SUPPORT_AGENT' check (role in ('SUPER_ADMIN','PLATFORM_ADMIN','OPERATIONS_MANAGER','SUPPORT_AGENT','STAFF_VIEWER')),
  permissions jsonb not null default '{"permissions": []}'::jsonb,
  status text not null default 'active' check (status in ('active','inactive')),
  created_at timestamptz default now(),
  unique(user_id)
);

create table auth_challenges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  contact text not null,
  channel text not null check (channel in ('phone','email')),
  purpose text not null default 'login',
  code_hash text not null,
  status text not null default 'pending' check (status in ('pending','verified','expired','cancelled')),
  request_ip text,
  expires_at timestamptz not null,
  requested_at timestamptz default now(),
  verified_at timestamptz
);


create table projects (
  id uuid primary key default gen_random_uuid(),
  customer_account_id uuid not null references customer_accounts(id),
  type text not null check (type in ('wedding','introduction','linked')),
  title text not null,
  owner_user_id uuid not null references users(id),
  partner_user_id uuid references users(id),
  event_date date,
  status text not null default 'active',
  created_at timestamptz default now(),
  check (status in ('active','archived','completed','cancelled'))
);

create table project_settings (
  project_id uuid primary key references projects(id) on delete cascade,
  whatsapp_first boolean not null default false,
  email_fallback boolean not null default true,
  rsvp_required boolean not null default false,
  budget_editing_mode text not null default 'owners_only' check (budget_editing_mode in ('owners_only','chair_can_propose','chair_can_edit')),
  vendor_mode text not null default 'directory' check (vendor_mode in ('directory','marketplace_later')),
  updated_at timestamptz default now()
);

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references users(id),
  project_id uuid references projects(id),
  action text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);

create table project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER','GUEST_VIEWER')),
  permissions_level text,
  permissions jsonb not null default '{"permissions": []}'::jsonb,
  budget_visibility_mode text not null default 'NO_ACCESS' check (budget_visibility_mode in ('FULL_ACCESS','SUMMARY_ACCESS','CONTRIBUTION_ONLY','NO_ACCESS')),
  created_at timestamptz default now(),
  unique(project_id, user_id)
);

create table project_links (
  id uuid primary key default gen_random_uuid(),
  primary_project_id uuid not null references projects(id) on delete cascade,
  linked_project_id uuid not null references projects(id) on delete cascade,
  relationship_type text not null default 'linked_ceremony' check (relationship_type in ('linked_ceremony','shared_committee','same_couple')),
  shared_committee boolean not null default false,
  shared_budget boolean not null default false,
  notes text,
  created_at timestamptz default now(),
  check (primary_project_id <> linked_project_id),
  unique(primary_project_id, linked_project_id)
);

create table participants (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  name text not null,
  contact text,
  role_type text not null,
  linked_user_id uuid references users(id)
);

create table vendors (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  name text not null,
  category text not null,
  contact text,
  status text not null default 'shortlisted' check (status in ('shortlisted','quote_requested','preferred','booked','rejected','contacted','confirmed','declined','completed')),
  notes text,
  external_url text,
  created_at timestamptz default now()
);

create table notification_preferences (
  project_id uuid primary key references projects(id) on delete cascade,
  whatsapp_enabled boolean not null default false,
  email_fallback_enabled boolean not null default true,
  meeting_updates boolean not null default true,
  invite_updates boolean not null default true,
  budget_updates boolean not null default false,
  updated_at timestamptz default now()
);

create table notifications (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  recipient_user_id uuid references users(id),
  recipient_contact text,
  channel text not null default 'email' check (channel in ('whatsapp','email')),
  provider text not null default 'resend',
  subject text,
  body text not null,
  status text not null default 'prepared' check (status in ('prepared','sent','failed','retry_scheduled')),
  provider_payload jsonb not null default '{}'::jsonb,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  last_error text,
  next_retry_at timestamptz,
  prepared_at timestamptz default now(),
  sent_at timestamptz,
  created_at timestamptz default now()
);

create table invites (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  contact text not null,
  role_assigned text not null check (role_assigned in ('OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER','GUEST_VIEWER')),
  permissions jsonb not null default '{"permissions": []}'::jsonb,
  budget_visibility_mode text not null default 'NO_ACCESS' check (budget_visibility_mode in ('FULL_ACCESS','SUMMARY_ACCESS','CONTRIBUTION_ONLY','NO_ACCESS')),
  token text unique not null,
  status text not null default 'pending' check (status in ('pending','accepted','expired','cancelled')),
  delivery_channel text not null default 'email' check (delivery_channel in ('whatsapp','email')),
  sent_count integer not null default 1,
  opened_count integer not null default 0,
  accepted_user_id uuid references users(id),
  expires_at timestamptz not null,
  last_sent_at timestamptz,
  opened_at timestamptz,
  accepted_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz default now()
);

create table guest_invites (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
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
  check (email is not null or phone is not null),
  constraint ck_project_guests_rsvp_attendee_count check (rsvp_attendee_count >= 0)
);


create table project_guests (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  first_name text not null,
  last_name text,
  display_name text not null,
  email text,
  phone text,
  category text,
  group_name text,
  notes text,
  invitation_card_url text,
  invitation_status text not null default 'NOT_SENT' check (invitation_status in ('NOT_SENT','SENT','OPENED','RESPONDED')),
  rsvp_status text not null default 'PENDING' check (rsvp_status in ('PENDING','ATTENDING','NOT_ATTENDING')),
  rsvp_responded_at timestamptz,
  rsvp_attendee_count integer not null default 1,
  rsvp_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  check (email is not null or phone is not null)
);

create table project_guest_invitations (
  id uuid primary key default gen_random_uuid(),
  project_guest_id uuid not null references project_guests(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  recipient_email text not null,
  recipient_name text not null,
  token text not null unique,
  status text not null default 'SENT' check (status in ('SENT','OPENED','RESPONDED','FAILED','CANCELLED')),
  sent_at timestamptz,
  opened_at timestamptz,
  responded_at timestamptz,
  notification_id uuid,
  provider_reference text,
  created_at timestamptz not null default now(),
  check (recipient_email <> '')
);

create table vendor_profiles (
  user_id uuid primary key references users(id) on delete cascade,
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

create table vendor_portfolio_items (
  id uuid primary key default gen_random_uuid(),
  vendor_user_id uuid not null references vendor_profiles(user_id) on delete cascade,
  title text not null,
  image_url text not null,
  description text,
  created_at timestamptz default now()
);

create table vendor_bookings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  vendor_user_id uuid not null references vendor_profiles(user_id) on delete cascade,
  requested_by uuid not null references users(id),
  status text not null default 'requested' check (status in ('requested','meeting_requested','meeting_scheduled','booked','declined','completed','cancelled')),
  meeting_requested_at timestamptz,
  meeting_notes text,
  quoted_amount numeric(12, 2) not null default 0,
  agreed_amount numeric(12, 2) not null default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(project_id, vendor_user_id)
);

create table vendor_payments (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null references vendor_bookings(id) on delete cascade,
  amount numeric(12, 2) not null default 0,
  received_at date,
  payment_method text,
  payment_reference text,
  notes text,
  created_at timestamptz default now(),
  check (amount >= 0)
);

create table meetings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  type text not null,
  title text not null,
  agenda text,
  notes text,
  decisions_log text,
  status text not null default 'scheduled' check (status in ('scheduled','completed','cancelled')),
  scheduled_time timestamptz not null,
  created_by uuid not null references users(id),
  updated_at timestamptz,
  created_at timestamptz default now()
);

create table meeting_rsvp (
  id uuid primary key default gen_random_uuid(),
  meeting_id uuid not null references meetings(id) on delete cascade,
  user_id uuid not null references users(id),
  status text not null check (status in ('accepted','declined','tentative')),
  comment text,
  responded_at timestamptz default now(),
  unique(meeting_id, user_id)
);

create table tasks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  title text not null,
  assigned_to uuid references users(id),
  status text not null default 'todo',
  due_date date
);

create table budgets (
  project_id uuid primary key references projects(id) on delete cascade,
  total numeric(12, 2) not null default 0,
  spent numeric(12, 2) not null default 0,
  check (total >= 0 and spent >= 0)
);

create table budget_line_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  category text not null,
  description text not null,
  item_name text,
  unit_cost numeric(12, 2) not null default 0,
  quantity numeric(12, 2) not null default 1,
  total_cost numeric(12, 2) not null default 0,
  deposited_amount numeric(12, 2) not null default 0,
  balance numeric(12, 2) not null default 0,
  next_deposit_date date,
  payment_details text,
  estimated_amount numeric(12, 2) not null default 0,
  actual_amount numeric(12, 2) not null default 0,
  status text not null default 'planned' check (status in ('planned','approved','paid','cancelled')),
  created_at timestamptz default now(),
  check (estimated_amount >= 0 and actual_amount >= 0 and unit_cost >= 0 and quantity >= 0 and total_cost >= 0 and deposited_amount >= 0 and balance >= 0)
);

create table budget_proposals (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  proposed_by uuid not null references users(id),
  title text not null,
  description text,
  amount numeric(12, 2) not null default 0,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  reviewed_by uuid references users(id),
  reviewed_at timestamptz,
  created_at timestamptz default now(),
  check (amount >= 0)
);

create table contributions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  contributor text not null,
  pledged numeric(12, 2) not null default 0,
  paid numeric(12, 2) not null default 0,
  status text not null default 'pledged',
  check (pledged >= 0 and paid >= 0)
);

create table testimonials (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  type text not null,
  url text not null,
  caption text
);

create index idx_staff_members_user_status on staff_members(user_id, status);
create index idx_customer_account_members_user on customer_account_members(user_id, status);
create index idx_customer_account_members_account on customer_account_members(customer_account_id, status);
create unique index uq_customer_account_one_active_owner on customer_account_members(customer_account_id) where role = 'OWNER' and status = 'ACTIVE';
create index idx_account_entitlements_account_key on account_entitlements(customer_account_id, key, status);
create unique index uq_account_entitlements_subscription_key on account_entitlements(customer_account_id, key, (metadata->>'subscription_id')) where metadata ? 'subscription_id';
create index idx_entitlement_definitions_status on entitlement_definitions(status);
create index idx_package_plans_public_status on package_plans(is_public, status, display_order);
create index idx_package_prices_plan_status on package_prices(package_plan_id, status, starts_at, ends_at);
create index idx_package_entitlement_grants_plan on package_entitlement_grants(package_plan_id);
create index idx_package_entitlement_grants_key on package_entitlement_grants(entitlement_key);
create index idx_billing_customers_account on billing_customers(customer_account_id, status);
create index idx_customer_subscriptions_account_status on customer_subscriptions(customer_account_id, status);
create index idx_customer_subscriptions_period_end on customer_subscriptions(current_period_end);
create index idx_payment_transactions_account_status on payment_transactions(customer_account_id, status);
create index idx_payment_transactions_subscription on payment_transactions(subscription_id);
create index idx_payment_events_reference on payment_events(provider, provider_reference);
create index idx_marketing_access_tokens_code_status on marketing_access_tokens(code, status);
create index idx_marketing_token_redemptions_account on marketing_access_token_redemptions(customer_account_id);
create index idx_auth_challenges_contact_status on auth_challenges(contact, status, requested_at);
create index idx_audit_logs_actor_action on audit_logs(actor_user_id, action, created_at);
create index idx_audit_logs_project_action on audit_logs(project_id, action, created_at);
create index idx_project_settings_project on project_settings(project_id);
create index idx_projects_customer_account on projects(customer_account_id);
create index idx_project_members_project_user on project_members(project_id, user_id);
create index idx_project_links_primary on project_links(primary_project_id);
create index idx_project_links_linked on project_links(linked_project_id);
create index idx_participants_project on participants(project_id);
create index idx_vendors_project on vendors(project_id);
create index idx_notifications_project_status on notifications(project_id, status);
create index idx_notifications_next_retry on notifications(next_retry_at) where next_retry_at is not null;
create index idx_invites_project on invites(project_id);
create index idx_guest_invites_project on guest_invites(project_id);
create index idx_guest_invites_token on guest_invites(token);
create index idx_guest_invites_attendance on guest_invites(project_id, attendance_status);

create index idx_project_guests_project on project_guests(project_id);
create index idx_project_guests_invitation_status on project_guests(project_id, invitation_status);
create index idx_project_guests_rsvp_status on project_guests(project_id, rsvp_status);
create index idx_project_guests_email on project_guests(project_id, lower(email)) where email is not null;
create index idx_project_guests_category_group on project_guests(project_id, category, group_name);
create index idx_project_guest_invitations_guest on project_guest_invitations(project_guest_id);
create index idx_project_guest_invitations_project on project_guest_invitations(project_id, status);
create index idx_project_guest_invitations_token on project_guest_invitations(token);
create index idx_vendor_profiles_category_status on vendor_profiles(category, status);
create index idx_vendor_portfolio_vendor on vendor_portfolio_items(vendor_user_id);
create index idx_vendor_bookings_project on vendor_bookings(project_id);
create index idx_vendor_bookings_vendor on vendor_bookings(vendor_user_id);
create index idx_vendor_payments_booking on vendor_payments(booking_id);
create index idx_meetings_project_time on meetings(project_id, scheduled_time);
create index idx_tasks_project on tasks(project_id);
create index idx_budget_line_items_project on budget_line_items(project_id);
create index idx_budget_proposals_project on budget_proposals(project_id);
create index idx_contributions_project on contributions(project_id);
create index idx_testimonials_project on testimonials(project_id);

comment on table public.users is 'Application profile table mapped to Supabase Auth. Password hashes live only in auth.users, never in public.users.';

create or replace function public.sync_auth_user_profile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, name, phone, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'name', new.raw_user_meta_data ->> 'full_name'),
    new.phone,
    new.email
  )
  on conflict (id) do update
  set
    name = coalesce(public.users.name, excluded.name),
    phone = coalesce(public.users.phone, excluded.phone),
    email = coalesce(public.users.email, excluded.email);

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert or update on auth.users
  for each row execute function public.sync_auth_user_profile();

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
  order by
    case
      when upper(coalesce(ae.metadata->>'source', '')) = 'PAID' then 1
      when upper(coalesce(ae.metadata->>'source', '')) = 'MARKETING' then 2
      when coalesce((ae.metadata->>'compatibility')::boolean, false) = true then 9
      else 5
    end,
    ae.created_at asc,
    ae.id asc
  limit 1;

  if entitlement_id is null then
    raise insufficient_privilege using message = 'No active events entitlement is available for this customer account';
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


alter table project_guests enable row level security;
alter table project_guest_invitations enable row level security;

create policy project_guests_select_planning_team on project_guests
  for select
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy project_guests_mutate_guest_managers on project_guests
  for all
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));

create policy project_guest_invitations_select_planning_team on project_guest_invitations
  for select
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));

create policy project_guest_invitations_mutate_guest_managers on project_guest_invitations
  for all
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']));
