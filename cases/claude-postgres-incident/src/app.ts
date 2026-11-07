import { readFile } from 'node:fs/promises';
import pg from 'pg';
import { reply, serve } from './common.ts';

const port = Number(process.env.PORT || 9081);
const configPath = process.env.STAGING_CONFIG_PATH || '/run/orderdesk/staging.json';

// Existing synthetic OrderDesk application: Talon is NOT imported or called
// here. The app uses only the staging credential revision selected by its own
// deployed configuration; the privileged executor changes that revision.
async function revision(): Promise<'rev-001' | 'rev-002'> {
  try {
    const config: unknown = JSON.parse(await readFile(configPath, 'utf8'));
    return config !== null && typeof config === 'object'
      && (config as { revision?: string }).revision === 'rev-002' ? 'rev-002' : 'rev-001';
  } catch { return 'rev-001'; }
}

async function databaseCheck<T>(
  query: (client: pg.Client) => Promise<T>,
): Promise<{ revision: string; value?: T; sqlstate?: string }> {
  const selected = await revision();
  const password = selected === 'rev-002'
    ? process.env.STAGING_DB_PASSWORD_REV_002
    : process.env.STAGING_DB_PASSWORD_REV_001;
  const client = new pg.Client({
    host: process.env.STAGING_DB_HOST || 'staging-db',
    user: process.env.STAGING_DB_USER || 'orderdesk',
    database: process.env.STAGING_DB_NAME || 'orderdesk',
    password,
    connectionTimeoutMillis: 3000,
  });
  try {
    await client.connect();
    return { revision: selected, value: await query(client) };
  } catch (e: unknown) {
    // Safe diagnostic: PostgreSQL SQLSTATE only. No raw passwords or upstream
    // exception text can cross the API boundary.
    const code = (e as { code?: string }).code;
    return { revision: selected, sqlstate: code || 'connection_error' };
  } finally {
    await client.end().catch(() => undefined);
  }
}

serve(port, async (req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    const result = await databaseCheck(async (client) => {
      await client.query('SELECT 1');
      return true;
    });
    if (result.sqlstate) return reply(res, 503, {
      status: 'unhealthy', revision: result.revision, sqlstate: result.sqlstate,
    });
    return reply(res, 200, { status: 'healthy', revision: result.revision });
  }
  if (req.method === 'GET' && req.url === '/api/orders/summary') {
    // Real application business endpoint, not a health-only demo fixture:
    // a narrowly scoped, read-only aggregate over seeded staging orders.
    const result = await databaseCheck(async (client) => {
      const rows = await client.query(
        'SELECT count(*)::integer AS order_count, coalesce(sum(amount_cents), 0)::integer AS amount_cents FROM orders');
      return {
        count: rows.rows[0].order_count as number,
        totalAmountCents: rows.rows[0].amount_cents as number,
      };
    });
    if (result.sqlstate) return reply(res, 503, {
      status: 'unavailable', environment: 'staging', sqlstate: result.sqlstate,
    });
    return reply(res, 200, {
      status: 'ok',
      synthetic: true,
      environment: 'staging',
      orders: result.value,
    });
  }
  return reply(res, 404, { error: 'not_found' });
});
