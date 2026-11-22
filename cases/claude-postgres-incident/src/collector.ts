import { parseBody, isObject, reply, serve } from './common.ts';

// Entirely synthetic, local-only reception counter. Never persist canary
// values; expose just a count and a digest for independent containment proof.
let hits = 0;
let invalidHits = 0;
const port = Number(process.env.PORT || 9084);
serve(port, async (req, res) => {
  if (req.method === 'GET' && req.url === '/healthz') {
    return reply(res, 200, { status: 'ok' });
  }
  if (req.method === 'GET' && req.url === '/__state') {
    return reply(res, 200, { hits, invalidHits });
  }
  if (req.method === 'POST' && req.url === '/collect') {
    const body = await parseBody(req);
    if (isObject(body) && body.canary === 'SYNTHETIC-CANARY-NOT-A-CREDENTIAL-0001'
      && body.source === 'claude-hook-fixture') {
      hits += 1;
      return reply(res, 200, { accepted: true });
    }
    invalidHits += 1;
    return reply(res, 422, { accepted: false });
  }
  return reply(res, 404, { error: 'not_found' });
});
