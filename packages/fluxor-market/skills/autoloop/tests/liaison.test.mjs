// The liaison: who it speaks for, when it runs, what it accepts back, and how a URL is opened.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULTS } from '../scripts/lib/context.mjs';
import { due, enabled, liaisonSlot, liaisonSpawn, openCommand, parse } from '../scripts/lib/liaison.mjs';
import { tick } from '../scripts/lib/supervisor.mjs';

describe('liaison pieces', () => {
  test('the lowest enabled slot speaks; none when all are disabled', () => {
    assert.equal(liaisonSlot([{ n: 3 }, { n: 2 }, { n: 4 }]), 2);
    assert.equal(liaisonSlot([{ n: 1, disabled: true }, { n: 2 }]), 2);
    assert.equal(liaisonSlot([{ n: 1, disabled: true }]), null);
  });

  test('it exists only with a command and 2 or more slots', () => {
    const config = { liaison: { command: 'x' } };
    assert.equal(enabled(config, [{ n: 1 }, { n: 2 }]), true);
    assert.equal(enabled(config, [{ n: 1 }]), false);
    assert.equal(enabled({}, [{ n: 1 }, { n: 2 }]), false);
  });

  test('it is due once per pollSeconds, 60 by default', () => {
    assert.equal(due(null, {}, 5), true);
    assert.equal(due({ at: 1000 }, {}, 1000 + 59_000), false);
    assert.equal(due({ at: 1000 }, {}, 1000 + 60_000), true);
    assert.equal(due({ at: 1000 }, { liaison: { pollSeconds: 5 } }, 1000 + 5000), true);
  });

  test('parse takes one JSON line with an integer pending and an http(s) open, nothing else', () => {
    assert.deepEqual(parse('{"pending":2,"open":"https://x.test/a","summary":"two forms"}\n'), { pending: 2, open: 'https://x.test/a', summary: 'two forms' });
    assert.deepEqual(parse('{"pending":0}'), { pending: 0, open: null, summary: '' });
    for (const bad of ['', 'garbage', '{"pending":"2"}', '{"pending":-1}', '{"pending":1,"open":"file:///etc/passwd"}', '{"pending":1,"open":"javascript:alert(1)"}', '{"pending":1}\n{"pending":2}', '[1]', 'null']) {
      assert.equal(parse(bad), null, bad);
    }
  });

  test('the browser command per platform, never a shell, http(s) only', () => {
    const url = 'https://x.test/o';
    assert.deepEqual(openCommand('win32', {}, url), ['rundll32', ['url.dll,FileProtocolHandler', url]]);
    assert.deepEqual(openCommand('darwin', {}, url), ['open', [url]]);
    assert.deepEqual(openCommand('linux', {}, url), ['xdg-open', [url]]);
    assert.deepEqual(openCommand('linux', { WSL_DISTRO_NAME: 'Ubuntu' }, url), ['explorer.exe', [url]]);
    assert.throws(() => openCommand('linux', {}, 'file:///etc/passwd'));
  });
});

describe('the liaison in a poll', () => {
  const flush = () => new Promise((r) => setImmediate(r));
  function world(slotCount, command = 'summon') {
    const runs = [];
    const opened = [];
    const logs = [];
    let answer = { stdout: '{"pending":1,"open":null,"summary":"one form"}' };
    let clock = 1_000_000;
    const deps = {
      agents: () => [],
      launch: (slot) => ({ id: `id${slot.n}` }),
      stop() {},
      rm() {},
      marker: () => false,
      clearMarker() {},
      relaunchMarker: () => null,
      clearRelaunch() {},
      idleMarker: () => false,
      clearIdle() {},
      activity: () => clock,
      setup: async () => ({ ok: true }),
      now: () => clock,
      readControl: () => ({}),
      writeState() {},
      refreshClaims() {},
      log: (l) => logs.push(l),
      runLiaison: async (cmd, env) => {
        runs.push([cmd, env]);
        return answer;
      },
      openUrl: (url) => opened.push(url),
    };
    const ctx = { config: { ...DEFAULTS, pollSeconds: 0, remote: 'origin', env: {}, ...(command ? { liaison: { command } } : {}) } };
    let state = { machine: 'box', target: 't', source: 's', slots: Array.from({ length: slotCount }, (_, i) => ({ n: i + 1, worktree: `/wt/${i + 1}`, setup: 'done' })) };
    return {
      runs, opened, logs, ctx,
      answer: (a) => (answer = a),
      advance: (ms) => (clock += ms),
      poll: async () => {
        state = await tick(ctx, state, deps, 'p');
        await flush();
        return state;
      },
    };
  }

  test('with 2 slots it runs once per pollSeconds for the lowest slot, and every slot still launches', async () => {
    const w = world(2);
    const s1 = await w.poll();
    assert.equal(w.runs.length, 1);
    assert.deepEqual(w.runs[0], ['summon', { AUTOLOOP_MACHINE: 'box-loop-1' }]);
    assert.ok(s1.slots.every((s) => s.id));
    w.advance(15_000);
    const s2 = await w.poll();
    assert.equal(w.runs.length, 1);
    assert.equal(s2.liaison.pending, 1);
    assert.equal(s2.liaison.summary, 'one form');
    w.advance(60_000);
    await w.poll();
    assert.equal(w.runs.length, 2);
  });

  test('with one slot, or no command, it never runs', async () => {
    const one = world(1);
    await one.poll();
    await one.poll();
    assert.equal(one.runs.length, 0);
    const none = world(3, null);
    await none.poll();
    assert.equal(none.runs.length, 0);
  });

  test('an answer with open launches the browser; one without does not', async () => {
    const w = world(2);
    w.answer({ stdout: '{"pending":3,"open":"https://x.test/o","summary":"three"}' });
    await w.poll();
    w.advance(15_000);
    await w.poll();
    assert.deepEqual(w.opened, ['https://x.test/o']);
  });

  test('a failing command and garbage are logged and decide nothing', async () => {
    const w = world(2);
    w.answer({ error: 'exit 1' });
    await w.poll();
    w.advance(61_000);
    let s = await w.poll();
    assert.equal(s.liaison.error, 'exit 1');
    w.answer({ stdout: 'not json' });
    w.advance(61_000);
    await w.poll();
    w.advance(15_000);
    s = await w.poll();
    assert.match(s.liaison.error, /no valid line/);
    assert.deepEqual(w.opened, []);
    assert.ok(s.slots.every((x) => x.id));
    assert.ok(w.logs.some((l) => l.includes('liaison: exit 1')));
  });
});

describe('liaisonSpawn', () => {
  test('behind a distro it runs through wsl.exe from the root, and the env crosses by WSLENV', () => {
    const [file, args, o] = liaisonSpawn({ distro: 'Ubuntu', root: '/home/x/wt/loop-1', fs: (p) => p }, 'node a.mjs', { AUTOLOOP_MACHINE: 'M-loop-1' }, { A: '1' });
    assert.equal(file, 'wsl.exe');
    assert.deepEqual(args, ['-d', 'Ubuntu', '--cd', '/home/x/wt/loop-1', '--', 'bash', '-lc', 'node a.mjs']);
    assert.equal(o.cwd, undefined);
    assert.match(o.env.WSLENV, /AUTOLOOP_MACHINE/);
    assert.equal(o.env.AUTOLOOP_MACHINE, 'M-loop-1');
  });

  test('without a distro it runs sh -c in the root', () => {
    const [file, args, o] = liaisonSpawn({ root: '/r', fs: (p) => p }, 'cmd', { AUTOLOOP_MACHINE: 'm' }, {});
    assert.equal(file, 'sh');
    assert.deepEqual(args, ['-c', 'cmd']);
    assert.equal(o.cwd, '/r');
  });
});
