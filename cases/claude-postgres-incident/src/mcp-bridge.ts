import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { MODEL_TOOLS, publicSchema, validateAction } from './common.ts';

// Phases the model sees. dispatched / already_completed / denied / rejected /
// failed are terminal answers for an intent; approval_pending, in_progress and
// not_dispatched resume the SAME operation when the model repeats the call;
// outcome_unknown is never retried and never replaced by a new operation (the
// effect may have happened; an operator reconciles with the downstream).
export type OperationResult = {
  phase: 'denied' | 'approval_pending' | 'dispatched' | 'already_completed' | 'rejected'
    | 'failed' | 'not_dispatched' | 'in_progress' | 'outcome_unknown';
  action: string;
  operation_id: string;
  status: number;
  code?: string;
  detail?: unknown;
};

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) =>
      [key, canonical((value as Record<string, unknown>)[key])]));
  }
  return value;
}

// intentKey identifies one business INTENT — session, action and exact
// arguments — in the durable intent ledger. It is a lookup key only, never
// the Talon operation id: two legitimate identical actions in one session
// (the credentials drift twice) are two operations.
export function intentKey(session: string, action: string, argumentsJSON: unknown): string {
  return createHash('sha256')
    .update(JSON.stringify(canonical({ session, action, arguments: argumentsJSON })))
    .digest('hex');
}

type LedgerEntry = { operation_id: string; action: string; reported: boolean; updated_at: string };
type Ledger = { version: 1; intents: Record<string, LedgerEntry> };

// ledgerPath: ORDERDESK_INTENT_LEDGER, else a per-session file in the
// temp/state directory. The ledger survives bridge restarts; it holds no
// secret (ids and booleans only).
export function ledgerPath(session: string): string {
  const configured = process.env.ORDERDESK_INTENT_LEDGER;
  if (configured) return configured;
  const dir = process.env.INCIDENT_STATE_DIR || tmpdir();
  return join(dir, 'orderdesk-intents-' + session + '.json');
}

function readLedger(path: string): Ledger {
  let raw: string;
  try { raw = readFileSync(path, 'utf8'); }
  catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') return { version: 1, intents: {} };
    throw new Error('intent_ledger_unreadable');
  }
  const parsed: unknown = JSON.parse(raw);
  if (!parsed || typeof parsed !== 'object' || (parsed as Ledger).version !== 1 ||
      typeof (parsed as Ledger).intents !== 'object') {
    // A corrupt ledger is never treated as empty: that could duplicate an
    // effect. Fail closed; an operator inspects it.
    throw new Error('intent_ledger_invalid');
  }
  return parsed as Ledger;
}

// writeLedger replaces the ledger atomically (write a private temp file,
// then rename), so a crash leaves either the old or the new ledger.
function writeLedger(path: string, ledger: Ledger): void {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const temp = path + '.tmp-' + process.pid + '-' + randomUUID();
  writeFileSync(temp, JSON.stringify(ledger), { mode: 0o600 });
  renameSync(temp, path);
}

function putEntry(path: string, key: string, entry: Omit<LedgerEntry, 'updated_at'>): void {
  const ledger = readLedger(path);
  ledger.intents[key] = { ...entry, updated_at: new Date().toISOString() };
  writeLedger(path, ledger);
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

type ProjectionView = { operation_status?: string; outcome_provenance?: string; outcome_code?: string };

function projectionOf(body: Record<string, unknown>): ProjectionView | undefined {
  const op = body.operation;
  return op && typeof op === 'object' ? op as ProjectionView : undefined;
}

const TERMINAL_PHASES = new Set<OperationResult['phase']>(
  ['dispatched', 'already_completed', 'denied', 'rejected', 'failed']);

// phaseOfFinished maps Talon's answer to a finished claim (200 with the
// operation) to the model's phase. Success is only what Talon recorded as
// succeeded; anything unrecognized is an unknown outcome, never a success.
function phaseOfFinished(op: ProjectionView | undefined): OperationResult['phase'] {
  switch (op?.operation_status) {
    case 'succeeded': return 'dispatched';
    case 'failed': return op.outcome_provenance === 'not_dispatched' ? 'not_dispatched' : 'failed';
    default: return 'outcome_unknown';
  }
}

// establishAndClaim is the Action Gateway lifecycle for one operation id:
// establish (a replay of the same id and arguments returns the existing
// operation), then claim at most one attempt.
async function establishAndClaim(action: string, argumentsJSON: unknown, operation_id: string): Promise<OperationResult> {
  const established = await talonRequest('POST', '/v1/action-operations',
    { operation_id, action, arguments: argumentsJSON });
  if (established.status === 403) {
    return { phase: 'denied', action, operation_id, status: 403,
      code: errorCode(established.body), detail: established.body };
  }
  if (established.status === 202 ||
      (established.status === 200 && projectionOf(established.body)?.operation_status === 'awaiting_approval')) {
    return { phase: 'approval_pending', action, operation_id, status: established.status,
      detail: established.body };
  }
  if (![200, 201].includes(established.status)) {
    return { phase: 'rejected', action, operation_id, status: established.status,
      code: errorCode(established.body) };
  }
  // Talon revalidates the human approval and the trusted definition at the
  // claim. The bridge never impersonates a reviewer or sends an operation
  // directly.
  const claimed = await talonRequest('POST',
    '/v1/action-operations/' + encodeURIComponent(operation_id) + '/attempts', {});
  const code = errorCode(claimed.body);
  if (claimed.status === 409) {
    switch (code) {
      case 'operation_already_succeeded':
        return { phase: 'already_completed', action, operation_id, status: 409, code, detail: claimed.body };
      case 'approval_pending':
        return { phase: 'approval_pending', action, operation_id, status: 409, code, detail: claimed.body };
      case 'attempt_already_in_progress':
        return { phase: 'in_progress', action, operation_id, status: 409, code, detail: claimed.body };
      case 'operation_outcome_unknown':
        return { phase: 'outcome_unknown', action, operation_id, status: 409, code, detail: claimed.body };
    }
  }
  if (claimed.status !== 200) {
    return { phase: 'rejected', action, operation_id, status: claimed.status, code, detail: claimed.body };
  }
  const op = projectionOf(claimed.body);
  return { phase: phaseOfFinished(op), action, operation_id, status: 200,
    code: op?.outcome_code, detail: claimed.body };
}

// existingOutcome reports a ledgered operation's terminal state that the
// model has not been told yet.
function existingOutcome(action: string, operation_id: string, op: ProjectionView): OperationResult {
  const detail = { operation: op };
  switch (op.operation_status) {
    case 'succeeded':
      return { phase: 'already_completed', action, operation_id, status: 200, code: 'operation_already_succeeded', detail };
    case 'denied':
      return { phase: 'denied', action, operation_id, status: 200, code: 'policy_denied', detail };
    case 'failed':
      return { phase: 'failed', action, operation_id, status: 200, code: op.outcome_code, detail };
    default: // cancelled: rejected, expired, invalidated
      return { phase: 'rejected', action, operation_id, status: 200, code: op.outcome_code || 'approval_rejected', detail };
  }
}

export type ActionCall = { result: OperationResult; acknowledge: () => void };

// callActionWithAck runs one model tool call. For a consequential action the
// operation id comes from the durable intent ledger: a repeat of the same
// intent RESUMES its operation (approval, retry after a not-dispatched
// failure, a crash between establish and claim), while an intent whose
// operation already ended and was reported is a NEW operation with a new
// random id. acknowledge() records that the terminal answer reached the
// model; the MCP server calls it only after writing the response.
export async function callActionWithAck(action: string, args: unknown): Promise<ActionCall> {
  // Local argument validation is defensive schema hygiene, NOT authorization.
  // Talon remains the sole policy and effect authority.
  const argumentsJSON = validateAction(action, args);
  const session = process.env.TALON_SESSION_ID;
  if (!session) throw new Error('TALON_SESSION_ID_required');
  const noAck = () => { /* nothing to record */ };
  // Fresh read operations must reflect a new snapshot: one random id each.
  const readOnly = action.startsWith('inspect_') || action === 'verify_staging_recovery';
  if (readOnly) {
    return { result: await establishAndClaim(action, argumentsJSON, 'incident-' + randomUUID()), acknowledge: noAck };
  }

  const path = ledgerPath(session);
  const key = intentKey(session, action, argumentsJSON);
  const entry = readLedger(path).intents[key];
  let operation_id: string | undefined;
  if (entry) {
    const current = await talonRequest('GET', '/v1/action-operations/' + encodeURIComponent(entry.operation_id));
    const op = current.status === 200 ? projectionOf(current.body) : undefined;
    if (current.status === 404) {
      // Ledgered but never established (a crash before the establish
      // reached Talon): establish it now under the same id.
      operation_id = entry.operation_id;
    } else if (!op) {
      return { result: { phase: 'rejected', action, operation_id: entry.operation_id, status: current.status,
        code: errorCode(current.body) }, acknowledge: noAck };
    } else {
      switch (op.operation_status) {
        case 'awaiting_approval':
        case 'authorized':
          operation_id = entry.operation_id; // resume: approval, or a crash before the claim
          break;
        case 'executing':
          return { result: { phase: 'in_progress', action, operation_id: entry.operation_id, status: 200,
            code: 'attempt_already_in_progress', detail: { operation: op } }, acknowledge: noAck };
        case 'unknown':
          // Never a new operation for an intent whose effect may have
          // happened: the entry stays until an operator reconciles.
          return { result: { phase: 'outcome_unknown', action, operation_id: entry.operation_id, status: 200,
            code: 'operation_outcome_unknown', detail: { operation: op } }, acknowledge: noAck };
        case 'failed':
          if (op.outcome_provenance === 'not_dispatched') { operation_id = entry.operation_id; break; }
          // fall through: a definitive failure is terminal
        default:
          if (!entry.reported) {
            const result = existingOutcome(action, entry.operation_id, op);
            return { result, acknowledge: () => putEntry(path, key, { ...entry, reported: true }) };
          }
          // Terminal and already reported: this repeat is a new intent.
      }
    }
  }
  if (!operation_id) {
    operation_id = 'incident-' + randomUUID();
    // Persist BEFORE establishing: a crash after the establish resumes this
    // operation instead of creating a duplicate.
    putEntry(path, key, { operation_id, action, reported: false });
  }
  const result = await establishAndClaim(action, argumentsJSON, operation_id);
  const id = operation_id;
  const acknowledge = TERMINAL_PHASES.has(result.phase)
    ? () => putEntry(path, key, { operation_id: id, action, reported: true })
    : noAck;
  return { result, acknowledge };
}

// callAction runs one tool call and records its terminal answer as
// reported at once (direct callers: the probe, tests).
export async function callAction(action: string, args: unknown): Promise<OperationResult> {
  const call = await callActionWithAck(action, args);
  call.acknowledge();
  return call.result;
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

const ERROR_PHASES = new Set<OperationResult['phase']>(
  ['denied', 'rejected', 'failed', 'not_dispatched', 'outcome_unknown']);

async function handleRPC(req: MCPRequest): Promise<{ result: unknown; acknowledge?: () => void }> {
  if (req.method === 'initialize') {
    return { result: {
      protocolVersion: '2025-11-25',
      capabilities: { tools: { listChanged: false } },
      serverInfo: { name: 'talon-claude-incident-bridge', version: '0.1.0' },
    } };
  }
  if (req.method === 'ping') return { result: {} };
  if (req.method === 'tools/list') return { result: { tools: toolsList() } };
  if (req.method === 'tools/call') {
    const name = req.params?.name;
    if (typeof name !== 'string' || !MODEL_TOOLS.includes(name))
      throw new Error('unknown_tool');
    const call = await callActionWithAck(name, req.params?.arguments ?? {});
    return { result: { content: [{ type: 'text', text: JSON.stringify(call.result) }],
      isError: ERROR_PHASES.has(call.result.phase) }, acknowledge: call.acknowledge };
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
      const { result, acknowledge } = await handleRPC(request);
      process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id, result }) + '\n');
      // Only after the answer is written: the model has been told the
      // terminal outcome, so a later identical call is a new intent.
      acknowledge?.();
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
        // A generic 403 (including auth failure) is NOT C06. Require Talon's
        // typed, company-sourced operation verdict; the proof harness must
        // still assert signed evidence and zero downstream delete effects.
        const op = (result.detail && typeof result.detail === 'object')
          ? (result.detail as Record<string, unknown>).operation : undefined;
        const companyDeny = result.phase === 'denied' &&
          op !== null && typeof op === 'object' &&
          (op as Record<string, unknown>).verdict === 'DENY' &&
          (op as Record<string, unknown>).matched_rule_source === 'company';
        process.exitCode = companyDeny ? 0 : 1;
      }).catch((err: unknown) => {
        console.error(err instanceof Error ? err.message : 'probe_error'); process.exitCode = 1;
      });
  } else {
    serveMCP().catch((err: unknown) => {
      console.error(err instanceof Error ? err.message : 'mcp_bridge_error'); process.exitCode = 1;
    });
  }
}
