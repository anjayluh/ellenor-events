create table if not exists public.project_budget_categories (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  description text,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint ck_project_budget_categories_name_not_blank check (length(trim(name)) >= 2),
  constraint uq_project_budget_categories_project_name unique (project_id, name)
);

alter table public.project_budget_items
  add column if not exists category_id uuid references public.project_budget_categories(id) on delete set null,
  add column if not exists actual_amount numeric(12,2) not null default 0;

insert into public.project_budget_categories (project_id, name, sort_order)
select
  pbi.project_id,
  trim(pbi.category) as name,
  row_number() over (partition by pbi.project_id order by lower(trim(pbi.category)))::integer * 10 as sort_order
from public.project_budget_items pbi
where trim(coalesce(pbi.category, '')) <> ''
group by pbi.project_id, trim(pbi.category)
on conflict (project_id, name) do nothing;

update public.project_budget_items pbi
set category_id = pbc.id
from public.project_budget_categories pbc
where pbi.project_id = pbc.project_id
  and pbi.category_id is null
  and trim(pbi.category) = pbc.name;

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_amounts_non_negative;
alter table public.project_budget_items
  add constraint ck_project_budget_items_amounts_non_negative check (planned_amount >= 0 and committed_amount >= 0 and actual_amount >= 0 and paid_amount >= 0);

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_paid_not_over_committed;
alter table public.project_budget_items
  add constraint ck_project_budget_items_paid_not_over_committed_or_actual check (paid_amount <= case when actual_amount > 0 then actual_amount else committed_amount end);

alter table public.project_budget_items drop constraint if exists ck_project_budget_items_status_amount_consistency;
alter table public.project_budget_items
  add constraint ck_project_budget_items_status_amount_consistency check (
    (status not in ('PLANNED','QUOTED') or paid_amount = 0)
    and (status <> 'PARTIALLY_PAID' or (paid_amount > 0 and paid_amount < case when actual_amount > 0 then actual_amount else committed_amount end))
    and (status <> 'PAID' or (case when actual_amount > 0 then actual_amount else committed_amount end > 0 and paid_amount = case when actual_amount > 0 then actual_amount else committed_amount end))
  );

create or replace function public.set_project_budget_item_integrity()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  vendor_project_id uuid;
  category_project_id uuid;
  category_name text;
begin
  new.currency := upper(coalesce(new.currency, 'UGX'));
  new.status := upper(coalesce(new.status, 'PLANNED'));
  new.planned_amount := coalesce(new.planned_amount, 0);
  new.committed_amount := coalesce(new.committed_amount, 0);
  new.actual_amount := coalesce(new.actual_amount, 0);
  new.paid_amount := coalesce(new.paid_amount, 0);

  if new.vendor_id is not null then
    select v.project_id into vendor_project_id
    from public.vendors v
    where v.id = new.vendor_id;

    if vendor_project_id is null or vendor_project_id <> new.project_id then
      raise exception 'Budget vendor must belong to this event';
    end if;
  end if;

  if new.category_id is not null then
    select c.project_id, c.name into category_project_id, category_name
    from public.project_budget_categories c
    where c.id = new.category_id;

    if category_project_id is null or category_project_id <> new.project_id then
      raise exception 'Budget category must belong to this event';
    end if;

    new.category := category_name;
  end if;

  if tg_op = 'UPDATE' then
    new.updated_at := now();
  end if;

  return new;
end;
$$;

create or replace function public.set_project_budget_category_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if tg_op = 'UPDATE' then
    new.updated_at := now();
  end if;
  return new;
end;
$$;

drop trigger if exists trg_project_budget_categories_updated_at on public.project_budget_categories;
create trigger trg_project_budget_categories_updated_at
before update
on public.project_budget_categories
for each row
execute function public.set_project_budget_category_updated_at();

create index if not exists idx_project_budget_categories_project on public.project_budget_categories(project_id);
create index if not exists idx_project_budget_categories_project_order on public.project_budget_categories(project_id, sort_order, name);
create index if not exists idx_project_budget_items_category_id on public.project_budget_items(category_id) where category_id is not null;
create index if not exists idx_project_budget_items_project_actual on public.project_budget_items(project_id, actual_amount);

alter table public.project_budget_categories enable row level security;

drop policy if exists project_budget_categories_select_members on public.project_budget_categories;
create policy project_budget_categories_select_members on public.project_budget_categories
  for select
  using (public.is_project_member(project_id));

drop policy if exists project_budget_categories_insert_budget_managers on public.project_budget_categories;
create policy project_budget_categories_insert_budget_managers on public.project_budget_categories
  for insert
  with check (public.has_project_permission(project_id, 'budget.edit'));

drop policy if exists project_budget_categories_update_budget_managers on public.project_budget_categories;
create policy project_budget_categories_update_budget_managers on public.project_budget_categories
  for update
  using (public.has_project_permission(project_id, 'budget.edit'))
  with check (public.has_project_permission(project_id, 'budget.edit'));

drop policy if exists project_budget_categories_delete_budget_managers on public.project_budget_categories;
create policy project_budget_categories_delete_budget_managers on public.project_budget_categories
  for delete
  using (public.has_project_permission(project_id, 'budget.edit'));
