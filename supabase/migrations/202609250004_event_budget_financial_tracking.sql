create table if not exists public.project_budget_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  category text not null,
  description text,
  vendor_id uuid references public.vendors(id) on delete set null,
  planned_amount numeric(12,2) not null default 0,
  committed_amount numeric(12,2) not null default 0,
  paid_amount numeric(12,2) not null default 0,
  currency text not null default 'UGX',
  due_date date,
  status text not null default 'PLANNED',
  notes text,
  created_by_user_id uuid references public.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_status;
alter table public.project_budget_items
  add constraint ck_project_budget_items_status check (status in ('PLANNED','QUOTED','COMMITTED','PARTIALLY_PAID','PAID','CANCELLED'));

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_currency;
alter table public.project_budget_items
  add constraint ck_project_budget_items_currency check (char_length(currency) = 3 and currency = upper(currency));

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_amounts_non_negative;
alter table public.project_budget_items
  add constraint ck_project_budget_items_amounts_non_negative check (planned_amount >= 0 and committed_amount >= 0 and paid_amount >= 0);

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_paid_not_over_committed;
alter table public.project_budget_items
  add constraint ck_project_budget_items_paid_not_over_committed check (paid_amount <= committed_amount);

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_status_amount_consistency;
alter table public.project_budget_items
  add constraint ck_project_budget_items_status_amount_consistency check (
    (status not in ('PLANNED','QUOTED') or paid_amount = 0)
    and (status <> 'PARTIALLY_PAID' or (paid_amount > 0 and paid_amount < committed_amount))
    and (status <> 'PAID' or (committed_amount > 0 and paid_amount = committed_amount))
  );

create or replace function public.set_project_budget_item_integrity()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  vendor_project_id uuid;
begin
  new.currency := upper(coalesce(new.currency, 'UGX'));
  new.status := upper(coalesce(new.status, 'PLANNED'));
  new.planned_amount := coalesce(new.planned_amount, 0);
  new.committed_amount := coalesce(new.committed_amount, 0);
  new.paid_amount := coalesce(new.paid_amount, 0);

  if new.vendor_id is not null then
    select v.project_id into vendor_project_id
    from public.vendors v
    where v.id = new.vendor_id;

    if vendor_project_id is null or vendor_project_id <> new.project_id then
      raise exception 'Budget vendor must belong to this event';
    end if;
  end if;

  if tg_op = 'UPDATE' then
    new.updated_at := now();
  end if;

  return new;
end;
$$;

drop trigger if exists trg_project_budget_items_integrity on public.project_budget_items;
create trigger trg_project_budget_items_integrity
before insert or update
on public.project_budget_items
for each row
execute function public.set_project_budget_item_integrity();

create index if not exists idx_project_budget_items_project on public.project_budget_items(project_id);
create index if not exists idx_project_budget_items_project_status on public.project_budget_items(project_id, status);
create index if not exists idx_project_budget_items_project_category on public.project_budget_items(project_id, category);
create index if not exists idx_project_budget_items_project_due_date on public.project_budget_items(project_id, due_date) where due_date is not null;
create index if not exists idx_project_budget_items_vendor on public.project_budget_items(vendor_id) where vendor_id is not null;
create index if not exists idx_project_budget_items_created_by on public.project_budget_items(created_by_user_id) where created_by_user_id is not null;

create or replace function public.has_project_permission(target_project_id uuid, required_permission text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.project_members pm
    where pm.project_id = target_project_id
      and pm.user_id = auth.uid()
      and (
        pm.role in ('OWNER','PARTNER')
        or coalesce(pm.permissions->'permissions', '[]'::jsonb) ? required_permission
      )
  );
$$;

alter table public.project_budget_items enable row level security;

drop policy if exists project_budget_items_select_members on public.project_budget_items;
create policy project_budget_items_select_members on public.project_budget_items
  for select
  using (public.is_project_member(project_id));

drop policy if exists project_budget_items_insert_budget_managers on public.project_budget_items;
create policy project_budget_items_insert_budget_managers on public.project_budget_items
  for insert
  with check (public.has_project_permission(project_id, 'budget.edit'));

drop policy if exists project_budget_items_update_budget_managers on public.project_budget_items;
create policy project_budget_items_update_budget_managers on public.project_budget_items
  for update
  using (public.has_project_permission(project_id, 'budget.edit'))
  with check (public.has_project_permission(project_id, 'budget.edit'));

drop policy if exists project_budget_items_delete_budget_managers on public.project_budget_items;
create policy project_budget_items_delete_budget_managers on public.project_budget_items
  for delete
  using (public.has_project_permission(project_id, 'budget.edit'));
