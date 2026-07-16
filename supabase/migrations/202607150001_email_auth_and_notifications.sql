comment on table public.users is 'Application profile table mapped to Supabase Auth. Password hashes live only in auth.users, never in public.users.';

alter table invites
  alter column delivery_channel set default 'email';

alter table notification_preferences
  alter column whatsapp_enabled set default false,
  alter column email_fallback_enabled set default true;

update notification_preferences
set whatsapp_enabled = false,
    email_fallback_enabled = true;
