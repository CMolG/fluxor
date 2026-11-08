// The remote switch (card://JAVA-1528): when it beats, what it accepts back, and how start and stop move the slots.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULTS } from '../scripts/lib/context.mjs';
import { dueRemote, parseOrder, remoteEnabled, remoteEnv, standbyAfter } from '../scripts/lib/remote.mjs';
import { tick } from '../scripts/lib/supervisor.mjs';

describe('remote switch pieces', () => {
  test('it exists with a command, whatever the slots, and the git remote does not count', () => {
    assert.equal(remoteEnabled({ remoteSwitch: { command: 'x' } }), true);
    assert.equal(remoteEnabled({ remote: 'origin' }), false);
  });

  test('it beats once per pollSeconds, 20 by default', () => {
    assert.equal(dueRemote(null, {}, 5), true);
    assert.equal(dueRemote({ at: 1000 }, {}, 1000 + 19_000), false);
    assert.equal(dueRemote({ at: 1000 }, {}, 1000 + 20_000), true);
    assert.equal(dueRemote({ at: 1000 }, { remoteSwitch: { pollSeconds: 5 } }, 1000 + 5000), true);
  });

  test('parseOrder takes one JSON line with start, stop or null, nothing else', () => {
    assert.deepEqual(parseOrder('{"command":"start"}\n'), { command: 'start' });
    assert.deepEqual(parseOrder('{"command":null}'), { command: null });
    for (const bad of ['', 'garbage', '{}', '{"command":"pause"}', '{"command":"stop"}\n{"command":"start"}', 'null', '[1]']) {
      assert.equal(parseOrder(bad), null, bad);
    }
  });

  test('parseOrder keeps a reason and a gate, and drops the ones of the wrong type', () => {
    const gate = { open: false, branch: 'feat/x', compareUrl: 'https://example.com/c', wallCard: 'PROJ-1' };
    assert.deepEqual(parseOrder(JSON.stringify({ command: 'stop', reason: ' merge it ', gate })), { command: 'stop', reason: 'merge it', gate });
    assert.deepEqual(parseOrder('{"command":"stop","reason":5,"gate":"x"}'), { command: 'stop' });
    assert.deepEqual(parseOrder('{"command":"stop","reason":"","gate":[1]}'), { command: 'stop' });
  });

  test('parseOrder caps the reason at 500 characters, whatever command printed it', () => {
    assert.equal(parseOrder(JSON.stringify({ command: 'stop', reason: 'x'.repeat(900) })).reason.length, 500);
  });

  test('start leaves standby, stop enters it, nothing keeps it; the env says which', () => {
    assert.equal(standbyAfter(true, 'start'), false);
    assert.equal(standbyAfter(false, 'stop'), true);
    assert.equal(standbyAfter(true, null), true);
    assert.deepEqual(remoteEnv({ machine: 'box', target: 't' }, true, [{}, {}]), {
      AUTOLOOP_STATE: 'idle', AUTOLOOP_MACHINE: 'box', AUTOLOOP_SLOTS: '2', AUTOLOOP_TARGET: 't',
    });
  });
});

describe('the remote switch in a poll', () => {
  const flush = () => new Promise((r) => setImmediate(r));
  function world({ standby = false, slotCount = 1 } = {}) {
    const runs = [];
    const stopped = [];
    const logs = [];
    let answer = { stdout: '{"command":null}' };
    let clock = 5_000_000;
    let control = {};
    const deps = {
      agents: () => [],
      launch: (slot) => ({ id: `id${slot.n}` }),
      stop: (id) => stopped.push(id),
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
      readControl: () => control,
      writeState() {},
      refreshClaims() {},
      log: (l) => logs.push(l),
      runLiaison: async (cmd, env) => {
        runs.push([cmd, env]);
        return answer;
      },
      openUrl() {},
    };
    const ctx = { config: { ...DEFAULTS, pollSeconds: 0, remote: 'origin', env: {}, remoteSwitch: { command: 'beat' } } };
    let state = {
      machine: 'box', target: 't', source: 's', standby,
      slots: Array.from({ length: slotCount }, (_, i) => ({ n: i + 1, worktree: `/wt/${i + 1}`, setup: 'done' })),
    };
    return {
      runs, stopped, logs,
      answer: (a) => (answer = a),
      control: (c) => (control = c),
      advance: (ms) => (clock += ms),
      poll: async () => {
        state = await tick(ctx, state, deps, 'p');
        await flush();
        return state;
      },
      agentsAlive: () => (deps.agents = () => state.slots.filter((s) => s.id).map((s) => ({ id: s.id, status: 'running' }))),
    };
  }

  test('a loop started in standby launches nothing and beats idle until it is told start', async () => {
    const w = world({ standby: true });
    let s = await w.poll();
    assert.ok(s.slots.every((x) => !x.id));
    assert.equal(w.runs[0][0], 'beat');
    assert.equal(w.runs[0][1].AUTOLOOP_STATE, 'idle');
    w.answer({ stdout: '{"command":"start"}' });
    w.advance(20_000);
    await w.poll(); // the beat that brings the order
    s = await w.poll(); // the order applied
    assert.equal(s.standby, false);
    s = await w.poll(); // the slot launches
    assert.ok(s.slots.every((x) => x.id));
    assert.ok(w.logs.includes('remote: start'));
  });

  test('stop stops every session, keeps the supervisor, and the next beat says idle', async () => {
    const w = world({ slotCount: 2 });
    w.agentsAlive();
    let s = await w.poll();
    assert.ok(s.slots.every((x) => x.id));
    w.answer({ stdout: '{"command":"stop"}' });
    w.advance(20_000);
    await w.poll();
    s = await w.poll();
    assert.equal(s.standby, true);
    assert.equal(s.stopping, false);
    s = await w.poll();
    assert.deepEqual(w.stopped.sort(), ['id1', 'id2']);
    assert.ok(s.slots.every((x) => !x.id));
    w.answer({ stdout: '{"command":null}' });
    w.advance(20_000);
    await w.poll();
    assert.equal(w.runs.at(-1)[1].AUTOLOOP_STATE, 'idle');
  });

  test('a stop with a reason is logged and kept in the state until start clears it', async () => {
    const w = world();
    const gate = { branch: 'feat/x', wallCard: 'PROJ-1' };
    w.answer({ stdout: JSON.stringify({ command: 'stop', reason: 'merge the control branch', gate }) });
    await w.poll();
    w.advance(20_000);
    await w.poll();
    let s = await w.poll();
    assert.ok(w.logs.includes('remote: stop (merge the control branch), standing by'), w.logs.join('|'));
    assert.equal(s.remoteSwitch.stopReason, 'merge the control branch');
    assert.deepEqual(s.remoteSwitch.gate, gate);
    w.answer({ stdout: '{"command":null}' });
    w.advance(20_000);
    s = await w.poll();
    s = await w.poll();
    assert.equal(s.remoteSwitch.stopReason, 'merge the control branch', 'a null beat keeps it');
    w.answer({ stdout: '{"command":"start"}' });
    w.advance(20_000);
    await w.poll();
    s = await w.poll();
    assert.equal(s.remoteSwitch.stopReason, null);
    assert.equal(s.remoteSwitch.gate, null);
  });

  test('standby holds over many polls, and a fresh supervisor reads no answer it did not ask for', async () => {
    const w = world({ standby: true });
    let s = await w.poll();
    assert.ok(!w.logs.some((l) => l.startsWith('remote:')), 'the first poll consumed a stale answer');
    for (let i = 0; i < 4; i++) {
      w.advance(20_000);
      s = await w.poll();
    }
    assert.equal(s.standby, true);
    assert.ok(s.slots.every((x) => !x.id));
    assert.ok(w.runs.length >= 3);
    assert.ok(w.runs.every(([, env]) => env.AUTOLOOP_STATE === 'idle'));
  });

  test('a local stop while standing by leaves the supervisor ready to end', async () => {
    const w = world({ standby: true });
    await w.poll();
    w.control({ stop: true });
    const s = await w.poll();
    // supervise() returns on exactly this: stopping, and no slot holding a session.
    assert.equal(s.stopping, true);
    assert.ok(s.slots.every((x) => !x.id));
  });

  test('a failing or garbled beat is logged and decides nothing; a local stop beats no more', async () => {
    const w = world();
    w.answer({ error: 'exit 1' });
    await w.poll();
    let s = await w.poll();
    assert.equal(s.remoteSwitch.error, 'exit 1');
    assert.equal(s.standby, false);
    w.answer({ stdout: 'not json' });
    w.advance(20_000);
    await w.poll();
    s = await w.poll();
    assert.match(s.remoteSwitch.error, /no valid line/);
    const before = w.runs.length;
    w.control({ stop: true });
    w.advance(20_000);
    await w.poll();
    assert.equal(w.runs.length, before);
  });
});
