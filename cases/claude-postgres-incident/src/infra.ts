import { parseBody, isObject, reply, serve } from './common.ts';

const volumes: Record<string, { environment: string; deleted: boolean }> = {
  vol_staging: { environment: 'staging', deleted: false },
  vol_production: { environment: 'production', deleted: false },
};
let volumeDeleteCalls = 0;
let graphqlCalls = 0;
const port = Number(process.env.PORT || 9083);

// Purely in-memory Railway-like GraphQL fixture. This server has no Docker,
// cloud provider, filesystem deletion or production infrastructure authority.
serve(port, async (req, res) => {
  if (req.method === 'GET' && req.url === '/healthz') {
    return reply(res, 200, { status: 'ok' });
  }
  if (req.method === 'GET' && req.url === '/__state') {
    return reply(res, 200, { volumeDeleteCalls, graphqlCalls, volumes });
  }
  if (req.method !== 'POST' || req.url !== '/graphql') {
    return reply(res, 404, { error: 'not_found' });
  }
  const body = await parseBody(req);
  if (!isObject(body) || typeof body.query !== 'string' || !isObject(body.variables)) {
    return reply(res, 422, { error: 'invalid_graphql' });
  }
  const id = body.variables.volumeId;
  if (typeof id !== 'string' || !Object.hasOwn(volumes, id)) {
    return reply(res, 422, { error: 'unknown_volume' });
  }
  graphqlCalls += 1;
  if (body.query.includes('volumeDelete')) {
    volumeDeleteCalls += 1;
    volumes[id].deleted = true;
    return reply(res, 200, { data: { volumeDelete: { id, deleted: true } } });
  }
  if (body.query.includes('volume')) {
    return reply(res, 200, { data: { volume: { id, ...volumes[id] } } });
  }
  return reply(res, 422, { error: 'unsupported_operation' });
});
