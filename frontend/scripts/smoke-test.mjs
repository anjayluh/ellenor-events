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
  'app/staff/page.tsx',
  'app/invite/[token]/page.tsx',
];

for (const route of requiredRoutes) {
  assert.ok(existsSync(join(root, route)), `Missing expected route: ${route}`);
}

const shell = readFileSync(join(root, 'components/PortalShell.tsx'), 'utf8');
for (const label of ['Client Portal', 'Meetings', 'Budget', 'Committee', 'Vendors', 'Staff Portal']) {
  assert.match(shell, new RegExp(label), `Portal shell should include ${label} navigation`);
}

const api = readFileSync(join(root, 'lib/api.ts'), 'utf8');
assert.match(api, /Authorization/, 'API client should support bearer authorization');
assert.match(api, /API_BASE_URL/, 'API client should use the configured API base URL');

const session = readFileSync(join(root, 'lib/session.ts'), 'utf8');
assert.match(session, /localStorage/, 'Session helpers should persist browser auth state');

console.log('Frontend smoke test passed');
