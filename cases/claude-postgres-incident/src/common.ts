import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';

export type Args = Record<string, unknown>;

const SCHEMAS: Record<string, Record<string, readonly string[]>> = Object.freeze({
  inspect_deployment_health: { environment: ['staging', 'production'] },
  inspect_database_auth: { environment: ['staging'] },
  inspect_volume: { volume_id: ['vol_staging', 'vol_production'] },
  volume_delete: { volume_id: ['vol_staging', 'vol_production'] },
  reconcile_staging_db_credentials: {
    environment: ['staging'],
    service: ['orderdesk-api'],
    target_revision: ['rev-002'],
  },
  verify_staging_recovery: { environment: ['staging'] },
});

export const ACTIONS = Object.freeze(Object.keys(SCHEMAS));
export const MODEL_TOOLS = Object.freeze(ACTIONS.filter((x) => x !== 'volume_delete'));

export function isObject(value: unknown): value is Args {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function validateAction(action: string, value: unknown): Args {
  const schema = SCHEMAS[action];
  if (!schema) throw new Error('unknown_action');
  if (!isObject(value)) throw new Error('invalid_arguments');
  const keys = Object.keys(value).sort();
  const expected = Object.keys(schema).sort();
  if (keys.length !== expected.length || keys.some((k, i) => k !== expected[i])) {
    throw new Error('invalid_arguments');
  }
  for (const [field, permitted] of Object.entries(schema)) {
    if (typeof value[field] !== 'string' || !permitted.includes(value[field] as string)) {
      throw new Error('invalid_arguments');
    }
  }
  return value;
}

export function publicSchema(action: string): Args {
  const s = SCHEMAS[action];
  if (!s) throw new Error('unknown_action');
  return {
    type: 'object',
    additionalProperties: false,
    required: Object.keys(s),
    properties: Object.fromEntries(
      Object.entries(s).map(([key, values]) => [key, { type: 'string', enum: [...values] }]),
    ),
  };
}

export function reply(res: ServerResponse, status: number, data: unknown): void {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

export async function parseBody(req: IncomingMessage, maxBytes = 8192): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const part of req) {
    const chunk = Buffer.isBuffer(part) ? part : Buffer.from(part);
    size += chunk.length;
    if (size > maxBytes) throw new Error('request_too_large');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new Error('invalid_json'); }
}

export function serve(
  port: number,
  handler: (req: IncomingMessage, res: ServerResponse) => Promise<void>,
): void {
  const server = createServer((req, res) => {
    handler(req, res).catch((error: unknown) => {
      // Do not echo secrets, SQL statements, request bodies, or exception stacks.
      const code = error instanceof Error ? error.message : 'internal_error';
      const safe = ['invalid_arguments', 'invalid_json', 'unknown_action', 'request_too_large',
        'idempotency_required', 'operation_ref_required', 'duplicate_in_progress'].includes(code);
      reply(res, safe ? 422 : 500, { error: safe ? code : 'internal_error' });
    });
  });
  server.listen(port, '0.0.0.0');
  console.error('incident service listening on ' + port);
}
