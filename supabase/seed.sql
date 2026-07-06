insert into users (id, name, phone, email) values
  ('00000000-0000-0000-0000-000000000101', 'Amina Owner', '+256700000101', 'amina@example.com'),
  ('00000000-0000-0000-0000-000000000102', 'David Partner', '+256700000102', 'david@example.com'),
  ('00000000-0000-0000-0000-000000000103', 'Grace Chair', '+256700000103', 'grace@example.com'),
  ('00000000-0000-0000-0000-000000000104', 'Sarah Viewer', '+256700000104', 'sarah@example.com')
on conflict (id) do nothing;

insert into projects (id, type, title, owner_user_id, partner_user_id, event_date, status) values
  ('10000000-0000-0000-0000-000000000001', 'introduction', 'Introduction - Amina & David', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000102', '2026-08-15', 'active'),
  ('10000000-0000-0000-0000-000000000002', 'wedding', 'Wedding - Amina & David', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000102', '2026-09-12', 'active')
on conflict (id) do nothing;

insert into project_links (id, primary_project_id, linked_project_id, relationship_type, shared_committee, shared_budget, notes) values
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000002', 'linked_ceremony', true, false, 'Introduction and wedding share committee visibility but keep separate budgets.')
on conflict (primary_project_id, linked_project_id) do nothing;

insert into project_members (project_id, user_id, role, permissions_level, budget_visibility_mode) values
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000101', 'OWNER', 'admin', 'FULL_ACCESS'),
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000102', 'PARTNER', 'admin', 'FULL_ACCESS'),
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000103', 'COMMITTEE_CHAIR', 'committee_admin', 'SUMMARY_ACCESS'),
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000104', 'FAMILY_VIEWER', 'viewer', 'CONTRIBUTION_ONLY'),
  ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000101', 'OWNER', 'admin', 'FULL_ACCESS'),
  ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000102', 'PARTNER', 'admin', 'FULL_ACCESS'),
  ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000103', 'COMMITTEE_CHAIR', 'committee_admin', 'SUMMARY_ACCESS')
on conflict (project_id, user_id) do nothing;

insert into participants (id, project_id, name, contact, role_type) values
  ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Auntie Rose', '+256700000201', 'family'),
  ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'Uncle Peter', '+256700000202', 'family')
on conflict (id) do nothing;

insert into vendors (id, project_id, name, category, contact, status, notes, external_url) values
  ('40000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Kampala Decor House', 'decor', '+256700000301', 'contacted', 'Intro ceremony decor shortlist.', 'https://example.com/decor'),
  ('40000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'Pearl Gardens Catering', 'catering', '+256700000302', 'shortlisted', 'Wedding reception catering option.', 'https://example.com/catering')
on conflict (id) do nothing;

insert into budgets (project_id, total, spent) values
  ('10000000-0000-0000-0000-000000000001', 18000000, 3500000),
  ('10000000-0000-0000-0000-000000000002', 42000000, 7500000)
on conflict (project_id) do nothing;

insert into contributions (id, project_id, contributor, pledged, paid, status) values
  ('50000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Bride family', 5000000, 3000000, 'partial'),
  ('50000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'Committee friends', 12000000, 4500000, 'partial')
on conflict (id) do nothing;

insert into project_settings (project_id, whatsapp_first, email_fallback, rsvp_required, budget_editing_mode, vendor_mode) values
  ('10000000-0000-0000-0000-000000000001', true, true, false, 'owners_only', 'directory'),
  ('10000000-0000-0000-0000-000000000002', true, true, false, 'owners_only', 'directory')
on conflict (project_id) do nothing;

insert into budget_line_items (id, project_id, category, description, estimated_amount, actual_amount, status) values
  ('60000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'decor', 'Introduction ceremony decor', 4500000, 1500000, 'approved'),
  ('60000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'catering', 'Wedding reception catering', 16000000, 4500000, 'approved')
on conflict (id) do nothing;

insert into budget_proposals (id, project_id, proposed_by, title, description, amount, status) values
  ('70000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000103', 'Add family tent', 'Extra seating shade for elders.', 900000, 'pending')
on conflict (id) do nothing;

insert into staff_members (id, user_id, role, status) values
  ('80000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000101', 'PLATFORM_ADMIN', 'active')
on conflict (user_id) do nothing;

insert into notification_preferences (project_id, whatsapp_enabled, email_fallback_enabled, meeting_updates, invite_updates, budget_updates) values
  ('10000000-0000-0000-0000-000000000001', true, true, true, true, false),
  ('10000000-0000-0000-0000-000000000002', true, true, true, true, false)
on conflict (project_id) do nothing;
