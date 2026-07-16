comment on table public.users is 'Application profile table. For authenticated Supabase users, public.users.id must equal auth.users.id.';

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
