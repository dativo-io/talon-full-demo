import { readFile } from 'node:fs/promises';
import pg from 'pg';
import { reply, serve } from './common.ts';

const port = Number(process.env.PORT || 9081);
const configPath = process.env.STAGING_CONFIG_PATH || '/run/orderdesk/staging.json';

async function revision(): Promise<string> {
  try {
    const config = JSON.parse(await readFile(configPath, 'utf8'));
    return config.revision === 'rev-002' ? 'rev-002' : 'rev-001';
  } catch { return 'rev-001'; }
}

async function health(): Promise<{ status: string; revision: string; sqlstate?: string }> {
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
    await client.query('SELECT 1');
    return { status: 'healthy', revision: selected };
  } catch (e: unknown) {
    // PostgreSQL SQLSTATE, never raw errors or secret values.
    const code = (e as { code?: string }).code;
    return { status: 'unhealthy', revision: selected, sqlstate: code || 'connection_error' };
  } finally { await client.end().catch(() => undefined); }
}

serve(port, async (req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    const value = await health();
    return reply(res, value.status === 'healthy' ? 200 : 503, value);
  }
  return reply(res, 404, { error: 'not_found' });
});
