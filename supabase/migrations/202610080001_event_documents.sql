create table if not exists public.project_documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  uploaded_by_user_id uuid not null references public.users(id),
  original_filename text not null,
  storage_path text not null unique,
  mime_type text not null,
  file_size_bytes bigint not null,
  category text not null default 'OTHER',
  description text,
  is_archived boolean not null default false,
  archived_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint ck_project_documents_filename check (length(trim(original_filename)) between 1 and 255),
  constraint ck_project_documents_storage_path check (storage_path like 'projects/%/documents/%/%'),
  constraint ck_project_documents_size check (file_size_bytes > 0 and file_size_bytes <= 10485760),
  constraint ck_project_documents_category check (category in ('INVITATION','CONTRACT','QUOTATION','INVOICE','RECEIPT','VENUE','PLANNING','FAMILY','COMMITTEE','OTHER'))
);

create index if not exists idx_project_documents_project_active on public.project_documents(project_id, is_archived, created_at desc);
create index if not exists idx_project_documents_project_category on public.project_documents(project_id, category);
create index if not exists idx_project_documents_project_uploader on public.project_documents(project_id, uploaded_by_user_id);
create index if not exists idx_project_documents_filename on public.project_documents(project_id, lower(original_filename));

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'event-documents',
  'event-documents',
  false,
  10485760,
  array[
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
    'image/jpeg',
    'image/png',
    'image/webp'
  ]::text[]
)
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

alter table public.project_documents enable row level security;

drop policy if exists project_documents_select_members on public.project_documents;
create policy project_documents_select_members on public.project_documents
  for select using (
    public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER'])
  );

drop policy if exists project_documents_insert_managers on public.project_documents;
create policy project_documents_insert_managers on public.project_documents
  for insert with check (
    (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'documents.manage'))
    and uploaded_by_user_id = auth.uid()
  );

drop policy if exists project_documents_update_managers on public.project_documents;
create policy project_documents_update_managers on public.project_documents
  for update using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'documents.manage'))
  with check (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'documents.manage'));

drop policy if exists project_documents_delete_managers on public.project_documents;
create policy project_documents_delete_managers on public.project_documents
  for delete using (public.has_project_role(project_id, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission(project_id, 'documents.manage'));

drop policy if exists event_documents_storage_select on storage.objects;
create policy event_documents_storage_select on storage.objects
  for select using (
    bucket_id = 'event-documents'
    and public.has_project_role((storage.foldername(name))[2]::uuid, array['OWNER','PARTNER','COMMITTEE_CHAIR','COMMITTEE_MEMBER','FAMILY_VIEWER'])
  );

drop policy if exists event_documents_storage_insert on storage.objects;
create policy event_documents_storage_insert on storage.objects
  for insert with check (
    bucket_id = 'event-documents'
    and (public.has_project_role((storage.foldername(name))[2]::uuid, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission((storage.foldername(name))[2]::uuid, 'documents.manage'))
  );

drop policy if exists event_documents_storage_update on storage.objects;
create policy event_documents_storage_update on storage.objects
  for update using (
    bucket_id = 'event-documents'
    and (public.has_project_role((storage.foldername(name))[2]::uuid, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission((storage.foldername(name))[2]::uuid, 'documents.manage'))
  ) with check (
    bucket_id = 'event-documents'
    and (public.has_project_role((storage.foldername(name))[2]::uuid, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission((storage.foldername(name))[2]::uuid, 'documents.manage'))
  );

drop policy if exists event_documents_storage_delete on storage.objects;
create policy event_documents_storage_delete on storage.objects
  for delete using (
    bucket_id = 'event-documents'
    and (public.has_project_role((storage.foldername(name))[2]::uuid, array['OWNER','PARTNER','COMMITTEE_CHAIR']) or public.has_project_permission((storage.foldername(name))[2]::uuid, 'documents.manage'))
  );
