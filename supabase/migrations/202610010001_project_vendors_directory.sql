create table if not exists public.project_vendors (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  category text not null,
  contact_person text,
  phone text,
  email text,
  address text,
  website text,
  service_description text,
  status text not null default 'SHORTLISTED',
  notes text,
  event_day_contact text,
  booking_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint ck_project_vendors_name_not_blank check (length(trim(name)) >= 2),
  constraint ck_project_vendors_category_not_blank check (length(trim(category)) >= 2),
  constraint ck_project_vendors_status check (status in ('PROSPECT','SHORTLISTED','CONTACTED','QUOTED','BOOKED','CONFIRMED','COMPLETED','CANCELLED'))
);

insert into public.project_vendors (
  id,
  project_id,
  name,
  category,
  contact_person,
  phone,
  email,
  website,
  service_description,
  status,
  notes,
  created_at,
  updated_at
)
select
  v.id,
  v.project_id,
  v.name,
  case
    when upper(coalesce(v.category, '')) in ('VENUE','CATERING','DECOR','PHOTOGRAPHY','VIDEOGRAPHY','MC','TRANSPORT','CAKE','ATTIRE','FLORIST','STATIONERY','ACCOMMODATION','SECURITY','OTHER') then upper(v.category)
    when lower(coalesce(v.category, '')) in ('pa / sound','pa_sound','sound') then 'PA_SOUND'
    when lower(coalesce(v.category, '')) in ('makeup','hair','beauty','makeup / beauty') then 'MAKEUP_BEAUTY'
    when lower(coalesce(v.category, '')) in ('planner / coordinator','planner','coordinator','event planner') then 'OTHER'
    when lower(coalesce(v.category, '')) in ('dj','entertainment','dj / entertainment') then 'DJ_ENTERTAINMENT'
    else 'OTHER'
  end,
  coalesce(v.contact_name, v.contact),
  v.phone,
  v.email,
  v.external_url,
  v.notes,
  case
    when lower(coalesce(v.status, '')) in ('quote_requested') then 'QUOTED'
    when lower(coalesce(v.status, '')) in ('booked','preferred') then 'BOOKED'
    when lower(coalesce(v.status, '')) in ('confirmed') then 'CONFIRMED'
    when lower(coalesce(v.status, '')) in ('completed') then 'COMPLETED'
    when lower(coalesce(v.status, '')) in ('cancelled','declined','rejected') then 'CANCELLED'
    when lower(coalesce(v.status, '')) in ('contacted') then 'CONTACTED'
    when lower(coalesce(v.status, '')) in ('shortlisted') then 'SHORTLISTED'
    else 'PROSPECT'
  end,
  v.notes,
  coalesce(v.created_at, now()),
  v.updated_at
from public.vendors v
where exists (select 1 from public.projects p where p.id = v.project_id)
on conflict (id) do nothing;

create or replace function public.set_project_vendor_integrity()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.name := trim(new.name);
  new.category := upper(trim(new.category));
  new.status := upper(coalesce(new.status, 'SHORTLISTED'));
  new.email := lower(nullif(trim(coalesce(new.email, '')), ''));
  new.phone := nullif(trim(coalesce(new.phone, '')), '');
  new.contact_person := nullif(trim(coalesce(new.contact_person, '')), '');
  new.event_day_contact := nullif(trim(coalesce(new.event_day_contact, '')), '');
  new.address := nullif(trim(coalesce(new.address, '')), '');
  new.website := nullif(trim(coalesce(new.website, '')), '');
  new.service_description := nullif(trim(coalesce(new.service_description, '')), '');
  new.notes := nullif(trim(coalesce(new.notes, '')), '');

  if tg_op = 'UPDATE' then
    new.updated_at := now();
  end if;

  return new;
end;
$$;

drop trigger if exists trg_project_vendors_integrity on public.project_vendors;
create trigger trg_project_vendors_integrity
before insert or update
on public.project_vendors
for each row
execute function public.set_project_vendor_integrity();

alter table public.project_budget_items drop constraint if exists project_budget_items_vendor_id_fkey;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'fk_project_budget_items_project_vendor'
      and conrelid = 'public.project_budget_items'::regclass
  ) then
    alter table public.project_budget_items
      add constraint fk_project_budget_items_project_vendor
      foreign key (vendor_id)
      references public.project_vendors(id);
  end if;
end;
$$;

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
    from public.project_vendors v
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

create index if not exists idx_project_vendors_project on public.project_vendors(project_id);
create index if not exists idx_project_vendors_project_category on public.project_vendors(project_id, category);
create index if not exists idx_project_vendors_project_status on public.project_vendors(project_id, status);
create index if not exists idx_project_vendors_project_name on public.project_vendors(project_id, lower(name));

alter table public.project_vendors enable row level security;

drop policy if exists project_vendors_select_members on public.project_vendors;
create policy project_vendors_select_members on public.project_vendors
  for select
  using (public.is_project_member(project_id));

drop policy if exists project_vendors_insert_vendor_managers on public.project_vendors;
create policy project_vendors_insert_vendor_managers on public.project_vendors
  for insert
  with check (public.has_project_permission(project_id, 'vendors.manage'));

drop policy if exists project_vendors_update_vendor_managers on public.project_vendors;
create policy project_vendors_update_vendor_managers on public.project_vendors
  for update
  using (public.has_project_permission(project_id, 'vendors.manage'))
  with check (public.has_project_permission(project_id, 'vendors.manage'));

drop policy if exists project_vendors_delete_vendor_managers on public.project_vendors;
create policy project_vendors_delete_vendor_managers on public.project_vendors
  for delete
  using (public.has_project_permission(project_id, 'vendors.manage'));
