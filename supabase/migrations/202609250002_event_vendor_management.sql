alter table public.vendors
  add column if not exists contact_name text,
  add column if not exists phone text,
  add column if not exists email text,
  add column if not exists agreed_amount numeric(12,2) not null default 0,
  add column if not exists amount_paid numeric(12,2) not null default 0,
  add column if not exists balance_amount numeric(12,2) not null default 0,
  add column if not exists payment_status text not null default 'not_applicable',
  add column if not exists updated_at timestamptz;

update public.vendors
set
  agreed_amount = coalesce(agreed_amount, 0),
  amount_paid = coalesce(amount_paid, 0),
  balance_amount = greatest(coalesce(agreed_amount, 0) - coalesce(amount_paid, 0), 0),
  payment_status = case
    when coalesce(agreed_amount, 0) = 0 then 'not_applicable'
    when coalesce(amount_paid, 0) = 0 then 'unpaid'
    when coalesce(amount_paid, 0) < coalesce(agreed_amount, 0) then 'partially_paid'
    else 'paid'
  end;

alter table public.vendors drop constraint if exists vendors_status_check;
alter table public.vendors drop constraint if exists ck_vendors_status;
alter table public.vendors
  add constraint ck_vendors_status check (status in ('shortlisted','contacted','confirmed','declined','cancelled','quote_requested','preferred','booked','rejected','completed'));

alter table public.vendors drop constraint if exists ck_vendors_payment_status;
alter table public.vendors
  add constraint ck_vendors_payment_status check (payment_status in ('not_applicable','unpaid','partially_paid','paid'));

alter table public.vendors drop constraint if exists ck_vendors_amounts_non_negative;
alter table public.vendors
  add constraint ck_vendors_amounts_non_negative check (agreed_amount >= 0 and amount_paid >= 0 and balance_amount >= 0);

alter table public.vendors drop constraint if exists ck_vendors_amount_paid_not_over_agreed;
alter table public.vendors
  add constraint ck_vendors_amount_paid_not_over_agreed check (amount_paid <= agreed_amount);

create or replace function public.set_vendor_financials()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.agreed_amount := coalesce(new.agreed_amount, 0);
  new.amount_paid := coalesce(new.amount_paid, 0);

  if new.agreed_amount < 0 or new.amount_paid < 0 then
    raise exception 'Vendor amounts cannot be negative';
  end if;

  if new.amount_paid > new.agreed_amount then
    raise exception 'Amount paid cannot exceed agreed amount';
  end if;

  new.balance_amount := new.agreed_amount - new.amount_paid;
  new.payment_status := case
    when new.agreed_amount = 0 then 'not_applicable'
    when new.amount_paid = 0 then 'unpaid'
    when new.amount_paid < new.agreed_amount then 'partially_paid'
    else 'paid'
  end;
  new.updated_at := coalesce(new.updated_at, now());
  return new;
end;
$$;

do $$
begin
  if not exists (
    select 1
    from pg_trigger
    where tgname = 'trg_vendors_set_financials'
      and tgrelid = 'public.vendors'::regclass
  ) then
    create trigger trg_vendors_set_financials
    before insert or update of agreed_amount, amount_paid
    on public.vendors
    for each row
    execute function public.set_vendor_financials();
  end if;
end $$;

create index if not exists idx_vendors_project_status on public.vendors(project_id, status);
create index if not exists idx_vendors_project_payment_status on public.vendors(project_id, payment_status);
create index if not exists idx_vendors_project_category on public.vendors(project_id, category);
create index if not exists idx_vendors_project_email on public.vendors(project_id, email) where email is not null;

alter table public.vendors enable row level security;

drop policy if exists vendors_select_members on public.vendors;
create policy vendors_select_members on public.vendors
  for select
  using (public.is_project_member(project_id));

drop policy if exists vendors_mutate_admins on public.vendors;
create policy vendors_mutate_admins on public.vendors
  for all
  using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER']));
