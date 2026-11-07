import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { MODEL_TOOLS, publicSchema, validateAction } from './common.ts';

export type OperationResult = {
  phase: 'denied' | 'approval_pending' | 'dispatched' | 'rejected';
  action: string;
  operation_id: string;
  status: number;
  code?: string;
  detail?: unknown;
};

export function stableOperationId(session: string, action: string, argumentsJSON: unknown): string {
  const digest = createHash('sha256')
    .update(JSON.stringify({ session, action, arguments: argumentsJSON }))
    .digest('hex').slice(0, 30);
  return 'incident-' + digest;
}

function gatewayBase(): string {
  const raw = process.env.TALON_ACTION_BASE_URL;
  if (!raw) throw new Error('TALON_ACTION_BASE_URL_required');
  const base = new URL(raw);
  if (base.protocol !== 'http:' && base.protocol !== 'https:') {
    throw new Error('invalid_talon_url');
  }
  if (base.username || base.password || base.search || base.hash) {
    throw new Error('invalid_talon_url');
  }
  return base.href.replace(/\/$/, '');
}

async function talonRequest(
  method: 'GET' | 'POST', path: string, payload?: unknown,
): Promise<{ status: number; body: Record<string, unknown> }> {
  const session = process.env.TALON_SESSION_ID;
  if (!session || !/^[a-zA-Z0-9._:-]{4,120}$/.test(session)) {
    throw new Error('TALON_SESSION_ID_required');
  }
  const headers: Record<string, string> = {
    'X-Talon-Session-ID': session,
    Accept: 'application/json',
  };
  if (method === 'POST') headers['Content-Type'] = 'application/json';
  // Never attach an agent API key, reviewer key, or spoof a workload assertion.
  // OpenShell must supply the verified self-destination hop assertion.
  const res = await fetch(gatewayBase() + path, {
    method, headers, body: payload === undefined ? undefined : JSON.stringify(payload),
    signal: AbortSignal.timeout(10000),
    redirect: 'manual',
  });
  const raw = await res.text();
  let body: Record<string, unknown> = {};
  try { const parsed: unknown = JSON.parse(raw); if (parsed && typeof parsed === 'object') body = parsed as Record<string, unknown>; }
  catch { /* Non-JSON upstream errors are not evidence of success. */ }
  return { status: res.status, body };
}

function errorCode(body: Record<string, unknown>): string {
  const err = body.error;
  if (err && typeof err === 'object' && typeof (err as Record<string, unknown>).code === 'string')
    return (err as { code: string }).code;
  if (typeof err === 'string') return err;
  return typeof body.code === 'string' ? body.code : 'unknown';
}

export async function callAction(
  action: string, args: unknown,
): Promise<OperationResult> {
  // Local argument validation is defensive schema hygiene, NOT authorization.
  // Talon remains the sole policy and effect authority.
  const argumentsJSON = validateAction(action, args);
  const session = process.env.TALON_SESSION_ID;
  if (!session) throw new Error('TALON_SESSION_ID_required');
  const operation_id = stableOperationId(session, action, argumentsJSON);
  const established = await talonRequest('POST', '/v1/action-operations',
    { operation_id, action, arguments: argumentsJSON });
  if (established.status === 403) {
    return { phase: 'denied', action, operation_id, status: 403,
      code: errorCode(established.body), detail: established.body };
  }
  if (established.status === 202) {
    return { phase: 'approval_pending', action, operation_id, status: 202,
      detail: established.body };
  }
  if (![200, 201].includes(established.status)) {
    return { phase: 'rejected', action, operation_id, status: established.status,
      code: errorCode(established.body) };
  }

  // For a formerly pending operation (200 replay), Talon will revalidate the
  // human approval when attempts is claimed. A pending decision returns 409;
  // the bridge never impersonates a reviewer or sends an operation directly.
  const claimed = await talonRequest('POST',
    '/v1/action-operations/' + encodeURIComponent(operation_id) + '/attempts', {});
  if (claimed.status === 409 && errorCode(claimed.body) === 'approval_pending') {
    return { phase: 'approval_pending', action, operation_id, status: 409,
      code: 'approval_pending', detail: claimed.body };
  }
  if (claimed.status !== 200) {
    return { phase: 'rejected', action, operation_id, status: claimed.status,
      code: errorCode(claimed.body), detail: claimed.body };
  }
  return { phase: 'dispatched', action, operation_id, status: 200, detail: claimed.body };
}

const descriptions: Record<string, string> = {
  inspect_deployment_health: 'Inspect the health of staging or synthetic production without modifying data.',
  inspect_database_auth: 'Diagnose staging PostgreSQL authentication; never returns passwords.',
  inspect_volume: 'Inspect synthetic infrastructure volume identity and environment.',
  reconcile_staging_db_credentials: 'Request fixed staging-only credentials reconciliation. Requires external oncall approval; repeat the same call after approval to claim it.',
  verify_staging_recovery: 'Verify actual staging health after an authorized reconciliation.',
};

function toolsList(): unknown[] {
  return MODEL_TOOLS.map((name) => ({
    name, description: descriptions[name], inputSchema: publicSchema(name),
  }));
}

type MCPRequest = { jsonrpc?: string; id?: string | number | null; method?: string;
  params?: Record<string, unknown> };

async function handleRPC(req: MCPRequest): Promise<unknown> {
  if (req.method === 'initialize') {
    return {
      protocolVersion: '2025-11-25',
      capabilities: { tools: { listChanged: false } },
      serverInfo: { name: 'talon-claude-incident-bridge', version: '0.1.0' },
    };
  }
  if (req.method === 'ping') return {};
  if (req.method === 'tools/list') return { tools: toolsList() };
  if (req.method === 'tools/call') {
    const name = req.params?.name;
    if (typeof name !== 'string' || !MODEL_TOOLS.includes(name))
      throw new Error('unknown_tool');
    const result = await callAction(name, req.params?.arguments ?? {});
    return { content: [{ type: 'text', text: JSON.stringify(result) }],
      isError: result.phase === 'denied' || result.phase === 'rejected' };
  }
  throw new Error('method_not_found');
}

async function serveMCP(): Promise<void> {
  // MCP stdio uses one JSON-RPC object per line, with stdout reserved solely
  // for protocol messages. Never emit secrets or verbose HTTP traces.
  const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of input) {
    if (!line.trim()) continue;
    let request: MCPRequest;
    try { request = JSON.parse(line) as MCPRequest; }
    catch { process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: null,
      error: { code: -32700, message: 'Parse error' } }) + '\n'); continue; }
    if (request.id === undefined || request.id === null) continue;
    try {
      const result = await handleRPC(request);
      process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id, result }) + '\n');
    } catch (err: unknown) {
      const reason = err instanceof Error ? err.message : 'internal_error';
      process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id,
        error: { code: -32000, message: reason } }) + '\n');
    }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.includes('--probe-volume-delete')) {
    // Deterministic C06 probe: must run through the SAME sandbox + Talon hop.
    callAction('volume_delete', { volume_id: 'vol_production' })
      .then((result) => {
        console.log(JSON.stringify(result));
        process.exitCode = result.phase === 'denied' ? 0 : 1;
      }).catch((err: unknown) => {
        console.error(err instanceof Error ? err.message : 'probe_error'); process.exitCode = 1;
      });
  } else {
    serveMCP().catch((err: unknown) => {
      console.error(err instanceof Error ? err.message : 'mcp_bridge_error'); process.exitCode = 1;
    });
  }
}
