// officium-next-run.mjs against a fake API: the run it passes on, the token only in the Authorization header, and
// nulls for every failure.
import { after, before, describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { nextRun } from '../scripts/officium-next-run.mjs';

const PROJECT = '11111111-2222-4333-8444-555555555555';
const TOKEN = 'sekrit-token-789';

let server;
let base;
let reply;
const seen = [];
const dir = mkdtempSync(join(tmpdir(), 'autoloop-next-run-'));
const configPath = join(dir, 'backlog.json');

before(async () => {
  server = createServer((req, res) => {
    seen.push({ method: req.method, url: req.url, auth: req.headers.authorization });
    res.writeHead(reply.status, { 'content-type': 'application/json' });
    res.end(JSON.stringify(reply.body ?? {}));
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}`;
  writeFileSync(configPath, JSON.stringify({ project: { id: PROJECT } }));
});
after(() => server.close());

const env = () => ({ OFFICIUM_API_URL: base, OFFICIUM_HEARTBEAT_TOKEN: TOKEN, OFFICIUM_BACKLOG_CONFIG: configPath });

describe('nextRun', () => {
  test('it asks with the token and passes the next card run on, with the card it is for (JAVA-1808)', async () => {
    reply = { status: 200, body: { key: 'PROJ-12', model: 'claude-opus-5-5', effort: 'high' } };
    assert.deepEqual(await nextRun({ env: env() }), { ok: true, model: 'claude-opus-5-5', effort: 'high', key: 'PROJ-12' });
    const last = seen.at(-1);
    assert.equal(last.method, 'GET');
    assert.equal(last.url, `/officium/v1/projects/${PROJECT}/autoloop/next-run`);
    assert.equal(last.auth, `Bearer ${TOKEN}`);
  });

  test('a slot that holds a claim asks for that card, and the live claims of the machine are excluded (JAVA-1786)', async () => {
    reply = { status: 200, body: { key: 'PROJ-7', model: 'claude-haiku-5-5', effort: 'medium' } };
    await nextRun({ env: { ...env(), AUTOLOOP_CARD: 'PROJ-7' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run?card=PROJ-7`);
    await nextRun({ env: { ...env(), AUTOLOOP_EXCLUDE: 'PROJ-1, PROJ-2,' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run?exclude=PROJ-1%2CPROJ-2`);
    await nextRun({ env: { ...env(), AUTOLOOP_EXCLUDE: '' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run`);
  });

  test("the slot's machine is sent, so its stale sessions end and its own unit comes first (JAVA-2004)", async () => {
    reply = { status: 200, body: { key: 'PROJ-4', model: 'claude-sonnet-5-5', effort: 'medium' } };
    await nextRun({ env: { ...env(), AUTOLOOP_MACHINE: 'MacBook-Pro.local-loop-1' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run?machine=MacBook-Pro.local-loop-1`);
    await nextRun({ env: { ...env(), AUTOLOOP_MACHINE: ' ' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run`);
  });

  test('a loop run with --phases asks only for a card of those phases (JAVA-1890)', async () => {
    reply = { status: 200, body: { key: 'PROJ-9', model: 'claude-sonnet-5-5', effort: 'high' } };
    await nextRun({ env: { ...env(), AUTOLOOP_PHASES: 'review' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run?phases=review`);
    await nextRun({ env: { ...env(), AUTOLOOP_PHASES: ' ' } });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/next-run`);
  });

  test('nothing eligible is no run', async () => {
    reply = { status: 200, body: { key: null, model: null, effort: null } };
    assert.deepEqual(await nextRun({ env: env() }), { ok: true, model: null, effort: null });
  });

  test('the widest tier of the card\'s roles is passed on beside the run (JAVA-1445)', async () => {
    reply = { status: 200, body: { key: 'PROJ-12', model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'write' } };
    assert.deepEqual(await nextRun({ env: env() }),
      { ok: true, model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'write', key: 'PROJ-12' });
  });

  test('a tier the picker does not know is a failure with nulls: the slot keeps the run it had', async () => {
    reply = { status: 200, body: { key: 'PROJ-12', model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'admin' } };
    const r = await nextRun({ env: env() });
    assert.equal(r.ok, false);
    assert.equal(r.model, null);
    assert.match(r.reason, /tool tier/);
  });

  test('a refused token is a failure with nulls', async () => {
    reply = { status: 401, body: {} };
    const r = await nextRun({ env: env() });
    assert.equal(r.ok, false);
    assert.equal(r.model, null);
    assert.match(r.reason, /heartbeat token/);
  });
});
