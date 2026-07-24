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
assert.match(api, /expireSession/, 'API client should expire local sessions when authenticated requests return 401');
assert.match(api, /isPublicPath/, 'API client should not attach stale bearer tokens to public auth and invite endpoints');
assert.match(api, /apiDelete/, 'API client should support resource deletion endpoints');

const session = readFileSync(join(root, 'lib/session.ts'), 'utf8');
assert.match(session, /localStorage/, 'Session helpers should persist browser auth state');
assert.match(session, /clearActiveProjectId/, 'Logout should clear the selected event workspace');
assert.match(session, /getAccessToken\(\)/, 'Session user lookup should require an access token');
assert.match(session, /consumeSessionNotice/, 'Expired sessions should produce a user-facing notice');

const activeProjectHook = readFileSync(join(root, 'lib/useActiveProject.ts'), 'utf8');
assert.match(activeProjectHook, /eecs_active_project_id|getActiveProjectId/, 'Feature pages should use the active event workspace instead of the first project');
assert.match(activeProjectHook, /selection_required/, 'Feature pages should require an event selection when no event is active');
assert.match(activeProjectHook, /status === 401/, 'Event workspace loading should treat 401 responses as signed-out state');

const protectedPages = readFileSync(join(root, 'components/ProtectedPages.tsx'), 'utf8');
assert.match(protectedPages, /InvitesClientPage/, 'Authenticated users should have an invite management screen');
assert.match(protectedPages, /delivery_channel: "email"/, 'Invite creation should default to email delivery');
assert.match(protectedPages, /ActiveEventSwitcher/, 'Event-scoped pages should visibly show the selected event context');
assert.match(protectedPages, /Decision stage/, 'Vendor status should be shown as user-facing decision stage language');
assert.match(protectedPages, /apiDelete/, 'Meetings, tasks, and vendors should expose backend delete actions in the UI');

const activeEventSwitcher = readFileSync(join(root, 'components/ActiveEventSwitcher.tsx'), 'utf8');
assert.match(activeEventSwitcher, /Back to event details/, 'Event-scoped pages should provide a direct path back to the selected event dashboard');
assert.match(activeEventSwitcher, /href=\{`\/events\/\$\{activeProjectId\}`\}/, 'Back-to-event link should target the active event dashboard');
assert.match(activeEventSwitcher, /data-icon="←"/, 'Back-to-event link should include a directional icon for scanability');

const eventDashboard = readFileSync(join(root, 'components/EventDashboard.tsx'), 'utf8');
assert.match(eventDashboard, /Save event/, 'Event dashboard should allow permitted users to edit event details');
assert.match(eventDashboard, /Archive event/, 'Event dashboard should expose safe event archival instead of silent deletion');
assert.match(eventDashboard, /resourceCard/, 'Event dashboard cards should opt into shared card alignment');

const styles = readFileSync(join(root, 'app/styles.css'), 'utf8');
assert.match(styles, /resourceCard/, 'Styles should provide shared resource card alignment');
assert.match(styles, /data-icon/, 'Styles should align icon-enhanced action buttons consistently');

console.log('Frontend smoke test passed');

const loginForm = readFileSync(join(root, 'components/LoginForm.tsx'), 'utf8');
assert.match(loginForm, /password/, 'Login form should collect password for Supabase email auth');
assert.doesNotMatch(loginForm, /demo-token/, 'Login form should not save demo sessions');

const homePage = readFileSync(join(root, 'app/page.tsx'), 'utf8');
assert.doesNotMatch(homePage, /demoProjects/, 'Home page should not expose demo project data to anonymous users');
