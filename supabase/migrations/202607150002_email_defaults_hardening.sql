alter table public.project_settings
  alter column whatsapp_first set default false;

update public.project_settings
set whatsapp_first = false
where whatsapp_first is true;

alter table public.notifications
  alter column channel set default 'email',
  alter column provider set default 'resend';
