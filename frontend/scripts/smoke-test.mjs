import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();

const requiredRoutes = [
  'app/page.tsx',
  'app/login/page.tsx',
  'app/meetings/page.tsx',
  'app/budget/page.tsx',
  'app/committee/page.tsx',
  'app/vendors/page.tsx',
  'app/invites/page.tsx',
  'app/staff/page.tsx',
  'app/invite/[token]/page.tsx',
];

for (const route of requiredRoutes) {
  assert.ok(existsSync(join(root, route)), `Missing expected route: ${route}`);
}

for (const asset of [
  'app/favicon.ico',
  'app/icon.png',
  'app/apple-icon.png',
  'public/assets/ellenor-events-logo.png',
  'public/assets/ellenor-events-logo-64.png',
]) {
  assert.ok(existsSync(join(root, asset)), `Missing expected brand asset: ${asset}`);
}

const shell = readFileSync(join(root, 'components/PortalShell.tsx'), 'utf8');
assert.match(shell, /AuthNav/, 'Portal shell should delegate navigation to auth-aware client nav');
assert.match(shell, /ellenor-events-logo-64\.png/, 'Portal shell should render the Ellenor Events logo');

const authNav = readFileSync(join(root, 'components/AuthNav.tsx'), 'utf8');
assert.doesNotMatch(authNav, /href="\/meetings"|href="\/budget"|href="\/committee"|href="\/vendors"|href="\/invites"/, 'Global nav should not expose event-scoped sections without an event context');

const api = readFileSync(join(root, 'lib/api.ts'), 'utf8');
assert.match(api, /Authorization/, 'API client should support bearer authorization');
assert.match(api, /API_BASE_URL/, 'API client should use the configured API base URL');

const session = readFileSync(join(root, 'lib/session.ts'), 'utf8');
assert.match(session, /localStorage/, 'Session helpers should persist browser auth state');
assert.match(session, /clearActiveProjectId/, 'Logout should clear the selected event workspace');

const activeProjectHook = readFileSync(join(root, 'lib/useActiveProject.ts'), 'utf8');
assert.match(activeProjectHook, /eecs_active_project_id|getActiveProjectId/, 'Feature pages should use the active event workspace instead of the first project');
assert.match(activeProjectHook, /selection_required/, 'Feature pages should require an event selection when no event is active');

const protectedPages = readFileSync(join(root, 'components/ProtectedPages.tsx'), 'utf8');
assert.match(protectedPages, /InvitesClientPage/, 'Authenticated users should have an invite management screen');
assert.match(protectedPages, /delivery_channel: "email"/, 'Invite creation should default to email delivery');
assert.match(protectedPages, /ActiveEventSwitcher/, 'Event-scoped pages should visibly show the selected event context');

console.log('Frontend smoke test passed');

const loginForm = readFileSync(join(root, 'components/LoginForm.tsx'), 'utf8');
assert.match(loginForm, /password/, 'Login form should collect password for Supabase email auth');
assert.doesNotMatch(loginForm, /demo-token/, 'Login form should not save demo sessions');

const homePage = readFileSync(join(root, 'app/page.tsx'), 'utf8');
assert.doesNotMatch(homePage, /demoProjects/, 'Home page should not expose demo project data to anonymous users');
