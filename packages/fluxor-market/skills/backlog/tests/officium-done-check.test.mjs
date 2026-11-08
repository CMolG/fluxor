// officium-done-check.mjs against a fake API (card://JAVA-2004): the first held unit with work answers, none open lets
// the `done` through, and every failure is `open: null` so the autoloop never traps a session on it.
import { after, before, describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { doneCheck } from '../scripts/officium-done-check.mjs';

const PROJECT = '11111111-2222-4333-8444-555555555555';
const TOKEN = 'sekrit-token-456';

let server;
let base;
let replies;
const seen = [];
const dir = mkdtempSync(join(tmpdir(), 'autoloop-done-check-'));
const configPath = join(dir, 'backlog.json');

before(async () => {
  server = createServer((req, res) => {
    seen.push({ url: req.url, auth: req.headers.authorization });
    const key = new URL(req.url, 'http://x').searchParams.get('card');
    const reply = replies[key] ?? { status: 404 };
    res.writeHead(reply.status, { 'content-type': 'application/json' });
    res.end(JSON.stringify(reply.body ?? {}));
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}`;
  writeFileSync(configPath, JSON.stringify({ project: { id: PROJECT } }));
});
after(() => server.close());

const env = (cards) => ({
  OFFICIUM_API_URL: base, OFFICIUM_HEARTBEAT_TOKEN: TOKEN, OFFICIUM_BACKLOG_CONFIG: configPath, AUTOLOOP_CARD: cards,
});

describe('doneCheck', () => {
  test('a sweep with a checkpoint to build is open, with the server reason, asked with the token', async () => {
    replies = { 'JAVA-1598': { status: 200, body: { key: 'JAVA-1598', open: true, reason: 'JAVA-1601 is the checkpoint the sweep builds now' } } };
    assert.deepEqual(await doneCheck({ env: env('JAVA-1598') }),
      { ok: true, open: true, key: 'JAVA-1598', reason: 'JAVA-1601 is the checkpoint the sweep builds now' });
    assert.equal(seen.at(-1).url, `/officium/v1/projects/${PROJECT}/autoloop/unit?card=JAVA-1598`);
    assert.equal(seen.at(-1).auth, `Bearer ${TOKEN}`);
  });

  test('the first held unit with work answers; none open lets the done through', async () => {
    replies = {
      'PROJ-1': { status: 200, body: { key: 'PROJ-1', open: false, reason: 'left its phase' } },
      'PROJ-2': { status: 200, body: { key: 'PROJ-2', open: true, reason: 'still In progress' } },
    };
    assert.equal((await doneCheck({ env: env('PROJ-1, PROJ-2') })).key, 'PROJ-2');
    replies['PROJ-2'] = { status: 200, body: { key: 'PROJ-2', open: false } };
    assert.equal((await doneCheck({ env: env('PROJ-1,PROJ-2') })).open, false);
  });

  test('no held card is not a question', async () => {
    assert.equal((await doneCheck({ env: env('') })).open, false);
  });

  test('every failure is open: null, never a refusal', async () => {
    replies = {};
    assert.equal((await doneCheck({ env: env('PROJ-9') })).open, null);
    replies = { 'PROJ-9': { status: 500 } };
    assert.equal((await doneCheck({ env: env('PROJ-9') })).open, null);
    replies = { 'PROJ-9': { status: 200, body: { key: 'PROJ-9' } } };
    assert.equal((await doneCheck({ env: env('PROJ-9') })).open, null);
    const noToken = { ...env('PROJ-9'), OFFICIUM_HEARTBEAT_TOKEN: '', OFFICIUM_HEARTBEAT_TOKEN_FILE: join(dir, 'none') };
    assert.equal((await doneCheck({ env: noToken })).open, null);
  });
});
