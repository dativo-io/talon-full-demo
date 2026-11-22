import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { ACTIONS, MODEL_TOOLS, publicSchema, validateAction } from '../src/common.ts';
import { callAction, intentKey } from '../src/mcp-bridge.ts';

function restoreEnv(previous: Array<string | undefined>): void {
  for (const [idx, key] of ['TALON_ACTION_BASE_URL', 'TALON_SESSION_ID', 'ORDERDESK_INTENT_LEDGER'].entries()) {
    if (previous[idx] === undefined) delete process.env[key];
    else process.env[key] = previous[idx];
  }
}

function saveEnv(): Array<string | undefined> {
  return [process.env.TALON_ACTION_BASE_URL, process.env.TALON_SESSION_ID, process.env.ORDERDESK_INTENT_LEDGER];
}

async function freshLedger(): Promise<{ path: string; cleanup: () => Promise<void> }> {
  const dir = await mkdtemp(join(tmpdir(), 'orderdesk-ledger-'));
  return { path: join(dir, 'intents.json'), cleanup: () => rm(dir, { recursive: true, force: true }) };
}

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

test('the intent key is stable per session, action and exact payload, and is never an operation id', () => {
  const args = { environment: 'staging', service: 'orderdesk-api', target_revision: 'rev-002' };
  const first = intentKey('run-42', 'reconcile_staging_db_credentials', args);
  assert.match(first, /^[a-f0-9]{64}$/);
  assert.equal(first, intentKey('run-42', 'reconcile_staging_db_credentials', {
    target_revision: 'rev-002', service: 'orderdesk-api', environment: 'staging',
  }));
  assert.notEqual(first, intentKey('run-43', 'reconcile_staging_db_credentials', args));
  assert.notEqual(first, intentKey('run-42', 'inspect_database_auth', { environment: 'staging' }));
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
      ? { status: 201, body: { created: true, operation: { operation_status: 'authorized' } } }
      : { status: 200, body: { operation: { operation_status: 'succeeded', outcome_provenance: 'observed' }, attempt: { status: 'succeeded' } } });
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
    restoreEnv(prev);
    await f.close();
  }
});

test('DENY and pending review never cause attempts', async () => {
  const previous = saveEnv();
  const ledger = await freshLedger();
  process.env.ORDERDESK_INTENT_LEDGER = ledger.path;
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
    restoreEnv(previous);
    await f.close();
    await ledger.cleanup();
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
    restoreEnv(old);
  }
});

test('synthetic Claude hook really attempts egress when a collector is reachable (fixture, not containment proof)', async () => {
  let received = 0;
  const server = createServer(async (req, res) => {
    let raw = '';
    for await (const part of req) raw += part.toString();
    const payload = JSON.parse(raw);
    if (req.url === '/collect' && payload.canary === 'SYNTHETIC-CANARY-NOT-A-CREDENTIAL-0001') {
      received += 1; res.writeHead(200); res.end('ok');
    } else { res.writeHead(422); res.end('invalid'); }
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('collector_bind_failed');
  const temp = await mkdtemp(join(tmpdir(), 'talon-hook-fixture-'));
  const receipt = join(temp, 'attempt.json');
  try {
    const exitCode = await new Promise<number | null>((accept, reject) => {
      const child = spawn(process.execPath, ['--experimental-strip-types',
        resolve('cases/claude-postgres-incident/src/hook.ts')], {
        env: { ...process.env,
          INCIDENT_CANARY_COLLECTOR_URL: 'http://127.0.0.1:' + address.port + '/collect',
          INCIDENT_HOOK_RECEIPT: receipt,
        },
        stdio: 'ignore',
      });
      child.once('error', reject);
      child.once('exit', accept);
    });
    assert.equal(exitCode, 0);
    const fact = JSON.parse(await readFile(receipt, 'utf8'));
    assert.equal(fact.attempted, true);
    assert.equal(fact.outcome, 'delivered');
    assert.equal(received, 1);
  } finally {
    await rm(temp, { recursive: true, force: true });
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});

// ---------------------------------------------------------------------------
// Durable per-intent operation ids, against a stateful fake of the Talon
// Action Gateway routes. Envelopes and status codes follow Talon's
// internal/server/handlers_actions.go: establish 201 / 202 (created, awaiting
// approval) / 200 (replay) / 403 (deny) with {created, operation}; GET 200
// {operation} or 404; claim 200 {operation, attempt} for any finished
// attempt, 409 {error:{code}} for a blocker. `dispatches` counts what reached
// the downstream business system.
type FakeOp = { id: string; action: string; args: string; status: string; provenance?: string };
type Outcome = 'succeed' | 'not_dispatched' | 'unknown';

async function fakeTalon(opts: { approval?: boolean } = {}) {
  const ops = new Map<string, FakeOp>();
  const state = { dispatches: 0, establishes: 0, next: [] as Outcome[] };
  const send = (res: import('node:http').ServerResponse, status: number, body: unknown) => {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(body));
  };
  const view = (op: FakeOp) => ({ operation_id: op.id, action: op.action, operation_status: op.status,
    ...(op.provenance ? { outcome_provenance: op.provenance } : {}),
    ...(op.status === 'awaiting_approval' ? { approval: { id: 'apr_' + op.id, status: 'pending' } } : {}) });
  const server = createServer(async (req, res) => {
    let raw = '';
    for await (const chunk of req) raw += chunk.toString();
    const url = req.url || '';
    if (req.method === 'POST' && url === '/v1/action-operations') {
      const body = JSON.parse(raw) as { operation_id: string; action: string; arguments: unknown };
      const args = JSON.stringify(body.arguments);
      const existing = ops.get(body.operation_id);
      if (existing) {
        if (existing.args !== args) return send(res, 409, { error: { code: 'operation_conflict' } });
        return send(res, existing.status === 'denied' ? 403 : 200, { created: false, operation: view(existing) });
      }
      state.establishes++;
      const op: FakeOp = { id: body.operation_id, action: body.action, args,
        status: body.action === 'volume_delete' ? 'denied' : (opts.approval ? 'awaiting_approval' : 'authorized') };
      ops.set(op.id, op);
      return send(res, op.status === 'denied' ? 403 : op.status === 'awaiting_approval' ? 202 : 201,
        { created: true, operation: view(op) });
    }
    const m = /^\/v1\/action-operations\/([^/]+)(\/attempts)?$/.exec(url);
    const op = m ? ops.get(decodeURIComponent(m[1])) : undefined;
    if (!m || !op) return send(res, 404, { error: { code: 'not_found' } });
    if (req.method === 'GET') return send(res, 200, { operation: view(op) });
    const blocker: Record<string, string> = { awaiting_approval: 'approval_pending', succeeded: 'operation_already_succeeded',
      unknown: 'operation_outcome_unknown', executing: 'attempt_already_in_progress', denied: 'policy_denied' };
    if (blocker[op.status]) return send(res, 409, { error: { code: blocker[op.status] } });
    const outcome = state.next.shift() ?? 'succeed';
    if (outcome === 'not_dispatched') { op.status = 'failed'; op.provenance = 'not_dispatched'; }
    else { state.dispatches++; op.status = outcome === 'succeed' ? 'succeeded' : 'unknown';
      op.provenance = outcome === 'succeed' ? 'observed' : 'unknown'; }
    return send(res, 200, { operation: view(op), attempt: { status: op.status } });
  });
  await new Promise<void>((accept) => server.listen(0, '127.0.0.1', accept));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('fake_talon_listen_failed');
  return { url: 'http://127.0.0.1:' + address.port, ops, state,
    approve: (id: string) => { const op = ops.get(id); if (op) op.status = 'authorized'; },
    close: () => new Promise<void>((accept) => server.close(() => accept())) };
}

const RECONCILE = { environment: 'staging', service: 'orderdesk-api', target_revision: 'rev-002' };

async function withFake(opts: { approval?: boolean }, run: (t: Awaited<ReturnType<typeof fakeTalon>>, ledger: string) => Promise<void>) {
  const previous = saveEnv();
  const t = await fakeTalon(opts);
  const ledger = await freshLedger();
  try {
    process.env.TALON_ACTION_BASE_URL = t.url;
    process.env.TALON_SESSION_ID = 'intent-run-' + randomUUID().slice(0, 8);
    process.env.ORDERDESK_INTENT_LEDGER = ledger.path;
    await run(t, ledger.path);
  } finally {
    restoreEnv(previous);
    await t.close();
    await ledger.cleanup();
  }
}

test('two identical consequential intents after the first completed are two operations and two dispatches', async () => {
  await withFake({}, async (t) => {
    const first = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(first.phase, 'dispatched');
    const second = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(second.phase, 'dispatched');
    assert.notEqual(second.operation_id, first.operation_id, 'a legitimate second action is not collapsed into the first');
    assert.match(first.operation_id, /^incident-[0-9a-f-]{36}$/);
    assert.equal(t.state.dispatches, 2);
    assert.equal(t.state.establishes, 2);
  });
});

test('a repeat while awaiting approval resumes the same operation; one dispatch after the approval', async () => {
  await withFake({ approval: true }, async (t) => {
    const pending = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(pending.phase, 'approval_pending');
    const again = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(again.phase, 'approval_pending');
    assert.equal(again.operation_id, pending.operation_id);
    assert.equal(t.state.dispatches, 0);
    t.approve(pending.operation_id);
    const resumed = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(resumed.phase, 'dispatched');
    assert.equal(resumed.operation_id, pending.operation_id);
    assert.equal(t.state.dispatches, 1);
    assert.equal(t.state.establishes, 1);
  });
});

test('a retry after a not-dispatched failure reuses the operation id', async () => {
  await withFake({}, async (t) => {
    t.state.next.push('not_dispatched');
    const failed = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(failed.phase, 'not_dispatched');
    assert.equal(t.state.dispatches, 0);
    const retried = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(retried.phase, 'dispatched');
    assert.equal(retried.operation_id, failed.operation_id);
    assert.equal(t.state.dispatches, 1);
    assert.equal(t.state.establishes, 1);
  });
});

test('an unknown outcome is never retried and never replaced by a new operation', async () => {
  await withFake({}, async (t) => {
    t.state.next.push('unknown');
    const unknown = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(unknown.phase, 'outcome_unknown');
    for (let i = 0; i < 3; i++) {
      const repeat = await callAction('reconcile_staging_db_credentials', RECONCILE);
      assert.equal(repeat.phase, 'outcome_unknown');
      assert.equal(repeat.operation_id, unknown.operation_id);
    }
    assert.equal(t.state.dispatches, 1);
    assert.equal(t.state.establishes, 1);
  });
});

test('a crash after the ledger write resumes the same id, whether or not the establish reached Talon', async () => {
  await withFake({}, async (t, ledger) => {
    const session = process.env.TALON_SESSION_ID as string;
    const key = intentKey(session, 'reconcile_staging_db_credentials', RECONCILE);
    // (a) ledgered and established, never claimed.
    t.ops.set('incident-established-not-claimed', { id: 'incident-established-not-claimed',
      action: 'reconcile_staging_db_credentials', args: JSON.stringify(RECONCILE), status: 'authorized' });
    await writeFile(ledger, JSON.stringify({ version: 1, intents: { [key]: {
      operation_id: 'incident-established-not-claimed', action: 'reconcile_staging_db_credentials',
      reported: false, updated_at: new Date().toISOString() } } }), { mode: 0o600 });
    const resumed = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(resumed.phase, 'dispatched');
    assert.equal(resumed.operation_id, 'incident-established-not-claimed');
    // (b) ledgered, the establish never reached Talon (GET 404).
    await writeFile(ledger, JSON.stringify({ version: 1, intents: { [key]: {
      operation_id: 'incident-never-established', action: 'reconcile_staging_db_credentials',
      reported: false, updated_at: new Date().toISOString() } } }), { mode: 0o600 });
    const established = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(established.phase, 'dispatched');
    assert.equal(established.operation_id, 'incident-never-established');
    assert.equal(t.state.dispatches, 2);
    const mode = (await stat(ledger)).mode & 0o777;
    assert.equal(mode, 0o600, 'the ledger is private');
  });
});

test('a terminal outcome the model was not told is reported, not executed again', async () => {
  await withFake({}, async (t, ledger) => {
    const session = process.env.TALON_SESSION_ID as string;
    const key = intentKey(session, 'reconcile_staging_db_credentials', RECONCILE);
    t.ops.set('incident-done-unreported', { id: 'incident-done-unreported', action: 'reconcile_staging_db_credentials',
      args: JSON.stringify(RECONCILE), status: 'succeeded', provenance: 'observed' });
    await writeFile(ledger, JSON.stringify({ version: 1, intents: { [key]: {
      operation_id: 'incident-done-unreported', action: 'reconcile_staging_db_credentials',
      reported: false, updated_at: new Date().toISOString() } } }), { mode: 0o600 });
    const told = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.equal(told.phase, 'already_completed');
    assert.equal(told.operation_id, 'incident-done-unreported');
    assert.equal(t.state.dispatches, 0);
    const next = await callAction('reconcile_staging_db_credentials', RECONCILE);
    assert.notEqual(next.operation_id, 'incident-done-unreported', 'once reported, a repeat is a new intent');
    assert.equal(t.state.dispatches, 1);
  });
});

test('a corrupt ledger fails closed instead of duplicating an effect', async () => {
  await withFake({}, async (t, ledger) => {
    await writeFile(ledger, '{"not":"a ledger"}', { mode: 0o600 });
    await assert.rejects(() => callAction('reconcile_staging_db_credentials', RECONCILE), /intent_ledger_invalid/);
    assert.equal(t.state.establishes, 0);
  });
});

// The MCP stdio bridge as a real process: the ledger survives a restart and
// a terminal answer is recorded only after it was written to the client.
test('the intent ledger survives a bridge restart', async () => {
  await withFake({ approval: true }, async (t, ledger) => {
    const bridge = resolve('cases/claude-postgres-incident/src/mcp-bridge.ts');
    const call = (id: number) => new Promise<Record<string, unknown>>((accept, reject) => {
      const child = spawn(process.execPath, ['--experimental-strip-types', bridge], {
        env: { ...process.env }, stdio: ['pipe', 'pipe', 'ignore'] });
      let out = '';
      let answer: Record<string, unknown> | undefined;
      child.stdout.on('data', (d: Buffer) => {
        out += d.toString();
        const line = out.split('\n').find((l) => l.trim());
        // The client got its answer: close the stream, as a client does;
        // the bridge ends after recording what it reported.
        if (line && !answer) { answer = JSON.parse(line) as Record<string, unknown>; child.stdin.end(); }
      });
      child.once('exit', () => answer ? accept(answer) : reject(new Error('bridge exited without an answer')));
      child.once('error', reject);
      child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method: 'tools/call',
        params: { name: 'reconcile_staging_db_credentials', arguments: RECONCILE } }) + '\n');
    });
    const phaseOf = (msg: Record<string, unknown>) =>
      JSON.parse(((msg.result as { content: Array<{ text: string }> }).content[0]).text) as { phase: string; operation_id: string };
    const first = phaseOf(await call(1));
    assert.equal(first.phase, 'approval_pending');
    t.approve(first.operation_id);
    const afterRestart = phaseOf(await call(2));
    assert.equal(afterRestart.phase, 'dispatched');
    assert.equal(afterRestart.operation_id, first.operation_id, 'a new bridge process resumes the same operation');
    assert.equal(t.state.dispatches, 1);
    const saved = JSON.parse(await readFile(ledger, 'utf8')) as { intents: Record<string, { reported: boolean }> };
    assert.equal(Object.values(saved.intents)[0].reported, true, 'recorded as reported after the answer was written');
  });
});
