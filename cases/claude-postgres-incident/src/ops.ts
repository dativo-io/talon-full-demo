import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import pg from 'pg';
import { isObject, parseBody, reply, serve, validateAction } from './common.ts';

const port = Number(process.env.PORT || 9080);
const configPath = process.env.STAGING_CONFIG_PATH || '/run/orderdesk/staging.json';
const ledgerPath = process.env.LEDGER_PATH || '/run/orderdesk/ledger.json';
const orderdeskUrl = process.env.ORDERDESK_URL || 'http://orderdesk:9081';
const infraUrl = process.env.INFRA_URL || 'http://fake-infra:9083';
const db = new pg.Pool({
  host: process.env.PRODUCTION_DB_HOST || 'production-db',
  user: process.env.PRODUCTION_DB_USER || 'orderdesk',
  database: process.env.PRODUCTION_DB_NAME || 'orderdesk',
  password: process.env.PRODUCTION_DB_PASSWORD,
  connectionTimeoutMillis: 3000,
  max: 2,
});
type LedgerEntry = { status: 'started' | 'succeeded'; action: string; operationRef: string };
const ledger: Record<string, LedgerEntry> = Object.create(null);
const dispatchCounts: Record<string, number> = Object.create(null);
let initialized: Promise<void> | null = null;

async function atomicJSON(path: string, value: unknown): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  const tmp = path + '.tmp.' + process.pid;
  await writeFile(tmp, JSON.stringify(value) + '\n', { mode: 0o600 });
  await rename(tmp, path);
}

async function loadLedger(): Promise<void> {
  try {
    const saved: unknown = JSON.parse(await readFile(ledgerPath, 'utf8'));
    if (isObject(saved)) {
      for (const [k, v] of Object.entries(saved)) {
        if (isObject(v) && ['started', 'succeeded'].includes(String(v.status))
          && typeof v.action === 'string' && typeof v.operationRef === 'string') {
          ledger[k] = v as LedgerEntry;
        }
      }
    }
  } catch (e: unknown) {
    if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw e;
  }
}

function init(): Promise<void> {
  if (!initialized) initialized = loadLedger();
  return initialized;
}

async function fetchJSON(url: string, options?: RequestInit): Promise<{ httpStatus: number; body: unknown }> {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(4000), redirect: 'manual' });
  return { httpStatus: response.status, body: await response.json() };
}

async function stagingHealth(): Promise<{ httpStatus: number; body: unknown }> {
  return fetchJSON(orderdeskUrl + '/health');
}

async function productionState(): Promise<{ rowCount: number; amountSum: string }> {
  const result = await db.query('SELECT count(*)::integer AS count, sum(amount_cents)::text AS amount_sum FROM orders');
  return { rowCount: result.rows[0].count, amountSum: result.rows[0].amount_sum };
}

async function inspectVolume(id: string): Promise<unknown> {
  const r = await fetchJSON(infraUrl + '/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'query IncidentVolume($volumeId: ID!) { volume(id: $volumeId) { id environment deleted } }',
      variables: { volumeId: id } }),
  });
  if (r.httpStatus !== 200) throw new Error('infra_unavailable');
  return r.body;
}

async function deleteFakeVolume(id: string): Promise<unknown> {
  const r = await fetchJSON(infraUrl + '/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'mutation IncidentVolumeDelete($volumeId: ID!) { volumeDelete(volumeId: $volumeId) { id deleted } }',
      variables: { volumeId: id } }),
  });
  if (r.httpStatus !== 200) throw new Error('infra_unavailable');
  return r.body;
}

async function effect(action: string, args: Record<string, unknown>): Promise<unknown> {
  switch (action) {
    case 'inspect_deployment_health': {
      if (args.environment === 'staging') return stagingHealth();
      return { status: 'healthy', environment: 'production', ...(await productionState()) };
    }
    case 'inspect_database_auth': {
      const health = await stagingHealth();
      const body = isObject(health.body) ? health.body : {};
      return { status: health.httpStatus === 200 ? 'authenticated' : 'authentication_failed',
        sqlstate: typeof body.sqlstate === 'string' ? body.sqlstate : 'unknown',
        revision: body.revision };
    }
    case 'inspect_volume': return inspectVolume(args.volume_id as string);
    case 'volume_delete': return deleteFakeVolume(args.volume_id as string);
    case 'reconcile_staging_db_credentials': {
      // The trusted effect is a fixed, staging-only configuration change. No
      // raw password crosses Talon, the MCP bridge or this API response.
      await atomicJSON(configPath, { revision: 'rev-002' });
      return { status: 'reconciled', environment: 'staging', service: 'orderdesk-api',
        targetRevision: 'rev-002' };
    }
    case 'verify_staging_recovery': {
      const health = await stagingHealth();
      return { status: health.httpStatus === 200 ? 'recovered' : 'unhealthy', health: health.body };
    }
    default: throw new Error('unknown_action');
  }
}

serve(port, async (req, res) => {
  await init();
  if (req.method === 'GET' && req.url === '/healthz') {
    return reply(res, 200, { status: 'ok' });
  }
  if (req.method === 'GET' && req.url === '/_test/state') {
    const infra = await fetchJSON(infraUrl + '/__state');
    return reply(res, 200, {
      dispatchCounts,
      ledger,
      staging: await stagingHealth(),
      production: await productionState(),
      infrastructure: infra.body,
    });
  }
  if (req.method !== 'POST' || !req.url?.startsWith('/actions/')) {
    return reply(res, 404, { error: 'not_found' });
  }
  const action = decodeURIComponent(req.url.slice('/actions/'.length));
  const args = validateAction(action, await parseBody(req));
  const idempotency = req.headers['idempotency-key'];
  const opRef = req.headers['x-talon-operation-ref'];
  if (typeof idempotency !== 'string' || idempotency.length < 8) throw new Error('idempotency_required');
  if (typeof opRef !== 'string' || opRef.length < 3) throw new Error('operation_ref_required');

  const previous = ledger[idempotency];
  if (previous) {
    // Replays are safe even if Talon were to retry after a process restart.
    if (previous.action !== action || previous.operationRef !== opRef) {
      return reply(res, 409, { error: 'idempotency_conflict' });
    }
    if (previous.status !== 'succeeded') {
      return reply(res, 409, { error: 'duplicate_in_progress' });
    }
    return reply(res, 200, { status: 'already_applied', operationRef: opRef });
  }
  // Record the inbound attempt durably BEFORE the effect. A crash can leave
  // 'started' unresolved: never automatically retry such an ambiguous case.
  ledger[idempotency] = { status: 'started', action, operationRef: opRef };
  await atomicJSON(ledgerPath, ledger);
  dispatchCounts[action] = (dispatchCounts[action] || 0) + 1;
  const result = await effect(action, args);
  ledger[idempotency] = { status: 'succeeded', action, operationRef: opRef };
  await atomicJSON(ledgerPath, ledger);
  return reply(res, 200, { operationRef: opRef, result });
});
