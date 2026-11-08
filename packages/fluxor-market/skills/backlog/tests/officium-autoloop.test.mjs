// officium-autoloop.mjs against a fake API: the beat it sends, the order it passes on, and one JSON line
// with `null` for every failure, the token only in the Authorization header.
import { after, before, describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { beat } from '../scripts/officium-autoloop.mjs';

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), '..', 'scripts', 'officium-autoloop.mjs');
const PROJECT = '11111111-2222-4333-8444-555555555555';
const TOKEN = 'sekrit-token-456';

let server;
let base;
let reply;
const seen = [];
const dir = mkdtempSync(join(tmpdir(), 'autoloop-beat-'));
const configPath = join(dir, 'backlog.json');

before(async () => {
  server = createServer((req, res) => {
    let body = '';
    req.on('data', (d) => (body += d));
    req.on('end', () => {
      seen.push({ method: req.method, url: req.url, auth: req.headers.authorization, body });
      res.writeHead(reply.status, { 'content-type': 'application/json' });
      res.end(JSON.stringify(reply.body ?? {}));
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}`;
  writeFileSync(configPath, JSON.stringify({ project: { id: PROJECT } }));
});
after(() => server.close());

const env = (extra = {}) => ({
  OFFICIUM_API_URL: base, OFFICIUM_HEARTBEAT_TOKEN: TOKEN, OFFICIUM_BACKLOG_CONFIG: configPath,
  AUTOLOOP_MACHINE: 'BOX', AUTOLOOP_STATE: 'idle', AUTOLOOP_SLOTS: '2', AUTOLOOP_TARGET: 'feat/cb-x', ...extra,
});

describe('beat', () => {
  test('it sends the loop state with the token and passes the queued order on', async () => {
    reply = { status: 200, body: { command: 'start' } };
    const r = await beat({ env: env() });
    assert.deepEqual(r, { ok: true, command: 'start' });
    const last = seen.at(-1);
    assert.equal(last.url, `/officium/v1/projects/${PROJECT}/autoloop/heartbeat`);
    assert.equal(last.auth, `Bearer ${TOKEN}`);
    assert.deepEqual(JSON.parse(last.body), { machine: 'BOX', state: 'idle', slots: 2, target: 'feat/cb-x' });
  });

  test('a stop reason and gate pass through, trimmed and capped; wrong types are dropped', async () => {
    const gate = { open: false, reasons: [], branch: 'feat/x', compareUrl: 'u', wallCard: 'PROJ-1' };
    reply = { status: 200, body: { command: 'stop', reason: ` ${'x'.repeat(600)} `, gate } };
    const r = await beat({ env: env() });
    assert.equal(r.reason.length, 500);
    assert.deepEqual(r.gate, gate);
    reply = { status: 200, body: { command: 'stop', reason: 3, gate: 'no' } };
    assert.deepEqual(await beat({ env: env() }), { ok: true, command: 'stop' });
  });

  test('an order it does not know is no order', async () => {
    reply = { status: 200, body: { command: 'reboot' } };
    assert.deepEqual(await beat({ env: env({ AUTOLOOP_STATE: 'running' }) }), { ok: true, command: null });
  });

  test('a refusal, a missing route, a bad state and no token each fail with null', async () => {
    reply = { status: 401, body: { error: 'invalid_token' } };
    assert.match((await beat({ env: env() })).reason, /refused \(401\)/);
    reply = { status: 404 };
    assert.match((await beat({ env: env() })).reason, /404/);
    assert.match((await beat({ env: env({ AUTOLOOP_STATE: 'paused' }) })).reason, /running or idle/);
    const noToken = await beat({ env: env({ OFFICIUM_HEARTBEAT_TOKEN: '', OFFICIUM_HEARTBEAT_TOKEN_FILE: join(dir, 'none') }) });
    assert.deepEqual([noToken.ok, noToken.command], [false, null]);
  });

  test('the script prints one JSON line and never the token', async () => {
    reply = { status: 500 };
    const { stdout, code } = await new Promise((resolve) => {
      execFile(process.execPath, [SCRIPT], { env: { ...process.env, ...env() } }, (error, out) =>
        resolve({ stdout: out, code: error?.code ?? 0 }));
    });
    assert.equal(code, 1);
    assert.equal(stdout.trim(), '{"command":null}');
    assert.ok(!stdout.includes(TOKEN));
  });
});
