drop policy if exists customer_subscriptions_customer_checkout_insert on public.customer_subscriptions;
drop policy if exists payment_transactions_customer_checkout_insert on public.payment_transactions;

create unique index if not exists uq_account_entitlements_subscription_key
  on public.account_entitlements (customer_account_id, key, (metadata->>'subscription_id'))
  where metadata ? 'subscription_id';

alter table public.marketing_access_tokens
  drop constraint if exists ck_marketing_access_token_redemption_max;

alter table public.marketing_access_tokens
  add constraint ck_marketing_access_token_redemption_max
  check (max_redemptions is null or redemption_count <= max_redemptions);

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

revoke all on function public.create_project_with_owner(text, text, uuid, uuid, date) from public;
grant execute on function public.create_project_with_owner(text, text, uuid, uuid, date) to authenticated;
