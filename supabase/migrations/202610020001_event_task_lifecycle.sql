alter table public.tasks drop constraint if exists ck_tasks_status;
alter table public.tasks
  add constraint ck_tasks_status check (status in ('TODO','IN_PROGRESS','DONE','CANCELLED'));

update public.tasks
set completed_at = null
where status <> 'DONE' and completed_at is not null;

alter table public.tasks drop constraint if exists ck_tasks_completed_at_status;
alter table public.tasks
  add constraint ck_tasks_completed_at_status check (status = 'DONE' or completed_at is null);

create or replace function public.set_task_timestamps()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.status = 'DONE' and (tg_op = 'INSERT' or old.status is distinct from 'DONE') then
    new.completed_at := coalesce(new.completed_at, now());
  elsif new.status <> 'DONE' then
    new.completed_at := null;
  end if;

  if tg_op = 'UPDATE' then
    new.updated_at := now();
  end if;

  return new;
end;
$$;

drop trigger if exists trg_tasks_set_timestamps on public.tasks;
create trigger trg_tasks_set_timestamps
before insert or update of status, title, description, priority, category, assigned_to, due_date
on public.tasks
for each row
execute function public.set_task_timestamps();
