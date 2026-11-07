import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { ACTIONS, MODEL_TOOLS, publicSchema, validateAction } from '../src/common.ts';
import { callAction, stableOperationId } from '../src/mcp-bridge.ts';

test('six closed, deliberately restricted action schemas match the ratified names', () => {
  assert.deepEqual([...ACTIONS].sort(), [
    'inspect_database_auth', 'inspect_deployment_health', 'inspect_volume',
    'reconcile_staging_db_credentials', 'verify_staging_recovery', 'volume_delete',
  ].sort());
  assert.equal(MODEL_TOOLS.includes('volume_delete'), false);
  for (const action of ACTIONS) {
    const schema = publicSchema(action);
    assert.equal(schema.additionalProperties, false);
    assert.deepEqual((schema.required as string[]).sort(),
      Object.keys(schema.properties as Record<string, unknown>).sort());
  }
  assert.deepEqual(validateAction('reconcile_staging_db_credentials', {
    environment: 'staging', service: 'orderdesk-api', target_revision: 'rev-002',
  }), { environment: 'staging', service: 'orderdesk-api', target_revision: 'rev-002' });
  assert.throws(() => validateAction('reconcile_staging_db_credentials', {
    environment: 'production', service: 'orderdesk-api', target_revision: 'rev-002',
  }), /invalid_arguments/);
  assert.throws(() => validateAction('volume_delete', {
    volume_id: 'vol_production', dangerous_extra: true,
  }), /invalid_arguments/);
  assert.throws(() => validateAction('inspect_volume', { volume_id: '../../../' }), /invalid_arguments/);
});

test('operation identity is stable per session, intent and exact payload', () => {
  const args = { environment: 'staging', service: 'orderdesk-api', target_revision: 'rev-002' };
  const first = stableOperationId('run-42', 'reconcile_staging_db_credentials', args);
  assert.match(first, /^incident-[a-f0-9]{30}$/);
  assert.equal(first, stableOperationId('run-42', 'reconcile_staging_db_credentials', args));
  assert.notEqual(first, stableOperationId('run-43', 'reconcile_staging_db_credentials', args));
  assert.notEqual(first, stableOperationId('run-42', 'inspect_database_auth', { environment: 'staging' }));
});

async function fixture(response: (req: import('node:http').IncomingMessage,
  data: Record<string, unknown>) => { status: number; body: unknown }) {
  const calls: Array<{ path: string; method: string; headers: Record<string, unknown>; payload: unknown }> = [];
  const server = createServer(async (req, res) => {
    let raw = '';
    for await (const chunk of req) raw += chunk.toString();
    const payload = raw ? JSON.parse(raw) : undefined;
    const result = response(req, { payload });
    calls.push({ path: req.url || '', method: req.method || '',
      headers: req.headers, payload });
    res.writeHead(result.status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(result.body));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('fixture_listen_failed');
  return { url: 'http://127.0.0.1:' + address.port, calls,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())) };
}

test('bridge uses only Talon action routes, no agent/reviewer auth, and claims allowed action once', async () => {
  const prev = [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID];
  const f = await fixture((req) =>
    req.url === '/v1/action-operations'
      ? { status: 201, body: { operation_status: 'authorized' } }
      : { status: 200, body: { attempt: { status: 'succeeded' } } });
  try {
    process.env.TALON_ACTION_BASE_URL = f.url;
    process.env.TALON_SESSION_ID = 'test-run-01';
    const result = await callAction('inspect_database_auth', { environment: 'staging' });
    assert.equal(result.phase, 'dispatched');
    assert.equal(f.calls.length, 2);
    assert.deepEqual(f.calls.map((x) => x.path), [
      '/v1/action-operations',
      '/v1/action-operations/' + result.operation_id + '/attempts',
    ]);
    const first = f.calls[0];
    assert.equal(first.headers['authorization'], undefined);
    assert.equal(first.headers['x-talon-workload-assertion'], undefined);
    assert.equal(first.headers['x-talon-session-id'], 'test-run-01');
    assert.deepEqual(first.payload, {
      operation_id: result.operation_id,
      action: 'inspect_database_auth',
      arguments: { environment: 'staging' },
    });
  } finally {
    [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID] = prev;
    await f.close();
  }
});

test('DENY and pending review never cause attempts', async () => {
  const previous = [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID];
  let mode: 'deny' | 'pending' = 'deny';
  const f = await fixture(() => mode === 'deny'
    ? { status: 403, body: { error: { code: 'action_forbidden' } } }
    : { status: 202, body: { operation_status: 'approval_pending' } });
  try {
    process.env.TALON_ACTION_BASE_URL = f.url;
    process.env.TALON_SESSION_ID = 'test-run-02';
    const denied = await callAction('volume_delete', { volume_id: 'vol_production' });
    assert.equal(denied.phase, 'denied');
    assert.equal(denied.status, 403);
    mode = 'pending';
    const pending = await callAction('reconcile_staging_db_credentials', {
      environment: 'staging', service: 'orderdesk-api', target_revision: 'rev-002',
    });
    assert.equal(pending.phase, 'approval_pending');
    assert.equal(f.calls.length, 2);
    assert.ok(f.calls.every(x => x.path === '/v1/action-operations'));
  } finally {
    [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID] = previous;
    await f.close();
  }
});

test('without Talon URL the bridge fails closed', async () => {
  const old = [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID];
  try {
    delete process.env.TALON_ACTION_BASE_URL;
    process.env.TALON_SESSION_ID = 'test-run-03';
    await assert.rejects(() => callAction('inspect_volume', { volume_id: 'vol_staging' }),
      /TALON_ACTION_BASE_URL_required/);
  } finally {
    [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID] = old;
  }
});
