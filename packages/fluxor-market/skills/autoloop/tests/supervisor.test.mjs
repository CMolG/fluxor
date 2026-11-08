// The supervisor's state machine: when a slot launches, recycles, gives up, or stops.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DEFAULTS, parsePhases } from '../scripts/lib/context.mjs';
import { decide, launchPlan, liveDeps, projectDirName, renderPrompt, slotVars, supervise, tick, transition } from '../scripts/lib/supervisor.mjs';

const cfg = { ...DEFAULTS, startTimeoutSeconds: 120, idleMinutes: 30, maxFailedStarts: 3, pollSeconds: 0 };

describe('launchPlan (JAVA-1445)', () => {
  const ctx = { config: { ...cfg, tiers: { enabled: true } } };
  const slot = (run) => ({ n: 1, run });
  const env = { AUTOLOOP_SLOT: '1' };

  test('a comment session is launched with the file tools denied, its tier in the env, and its run', () => {
    const plan = launchPlan(ctx, slot({ model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'comment' }), env);
    assert.deepEqual(plan.args, ['--dangerously-skip-permissions', '--model', 'claude-haiku-5-5', '--effort', 'medium',
      '--disallowedTools', 'Edit Write NotebookEdit PowerShell']);
    assert.deepEqual(plan.env, { AUTOLOOP_SLOT: '1', AUTOLOOP_TOOL_TIER: 'comment' });
  });

  test('a write run, and a run with no tier, launch exactly as before the tiers', () => {
    const write = launchPlan(ctx, slot({ model: 'claude-sonnet-5-5', effort: 'high', toolTier: 'write' }), env);
    assert.deepEqual(write.args, ['--dangerously-skip-permissions', '--model', 'claude-sonnet-5-5', '--effort', 'high']);
    assert.deepEqual(write.env, env);
    const untiered = launchPlan(ctx, slot({ model: 'claude-sonnet-5-5', effort: 'high' }), env);
    assert.deepEqual(untiered.args, write.args);
    assert.deepEqual(untiered.env, env);
  });

  test('with tiers switched off, a read run launches as before', () => {
    const off = { config: { ...cfg, tiers: { enabled: false } } };
    const plan = launchPlan(off, slot({ model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'read' }), env);
    assert.ok(!plan.args.includes('--disallowedTools'));
    assert.deepEqual(plan.env, env);
  });
});
const T0 = 1_000_000_000;
const running = { id: 'abc12345', launchedAt: T0, seen: true, setup: 'done' };
const busy = { id: 'abc12345', status: 'busy', sessionId: 's' };
const idle = { ...busy, status: 'idle' };

describe('decide', () => {
  test('an empty slot launches; a slot being set up waits', () => {
    assert.equal(decide({ setup: 'done' }, {}, cfg, T0), 'launch');
    assert.equal(decide({ setup: 'pending' }, {}, cfg, T0), 'setup');
    assert.equal(decide({ setup: 'running' }, {}, cfg, T0), 'none');
  });

  test('done marker + idle recycles at once; done marker + busy waits while the transcript is written (a Stop hook sent it back)', () => {
    assert.equal(decide(running, { session: idle, marker: true, activity: T0 }, cfg, T0 + 1000), 'recycle');
    assert.equal(decide(running, { session: busy, marker: true, activity: T0 }, cfg, T0 + 60_000), 'none');
  });

  test('done marker + busy + a transcript silent past doneGraceSeconds recycles (an armed Monitor keeps it busy)', () => {
    assert.equal(decide(running, { session: busy, marker: true, activity: T0 }, cfg, T0 + 121_000), 'recycle');
    assert.equal(decide(running, { session: busy, marker: true, activity: null }, cfg, T0 + 121_000), 'recycle');
    assert.equal(decide(running, { session: busy, marker: true, activity: T0 + 100_000 }, cfg, T0 + 121_000), 'none');
  });

  test('a turn that ends without the marker keeps the session (it may wait on a background task)', () => {
    assert.equal(decide(running, { session: idle, marker: false, activity: T0 + 5 * 60_000 }, cfg, T0 + 10 * 60_000), 'none');
  });

  test('30 minutes without a transcript write recycles, busy or not', () => {
    const late = T0 + 31 * 60_000;
    assert.equal(decide(running, { session: busy, marker: false, activity: T0 }, cfg, late), 'recycle-silent');
    assert.equal(decide(running, { session: idle, marker: false, activity: null }, cfg, late), 'recycle-silent');
  });

  test('a session that never shows up, or dies right away, is a failed start', () => {
    const fresh = { ...running, seen: false };
    assert.equal(decide(fresh, { session: null }, cfg, T0 + 10_000), 'none');
    assert.equal(decide(fresh, { session: null }, cfg, T0 + 121_000), 'failed-start');
    assert.equal(decide(running, { session: null }, cfg, T0 + 10_000), 'failed-start');
    assert.equal(decide(running, { session: null }, cfg, T0 + 600_000), 'forget');
  });

  test('stop stops live sessions and launches nothing', () => {
    assert.equal(decide(running, { session: busy, stop: true }, cfg, T0), 'stop');
    assert.equal(decide({ setup: 'done' }, { stop: true }, cfg, T0), 'none');
  });

  test('a disabled slot does nothing', () => {
    assert.equal(decide({ setup: 'done', disabled: true }, {}, cfg, T0), 'none');
  });
});

describe('relaunch', () => {
  const ask = { model: 'claude-sonnet-5-5', effort: 'medium' };

  test('a relaunch marker + idle relaunches; busy waits; a done marker wins', () => {
    assert.equal(decide(running, { session: idle, marker: false, relaunch: ask, activity: T0 }, cfg, T0 + 1000), 'relaunch');
    assert.equal(decide(running, { session: busy, marker: false, relaunch: ask, activity: T0 }, cfg, T0 + 1000), 'none');
    assert.equal(decide(running, { session: idle, marker: true, relaunch: ask, activity: T0 }, cfg, T0 + 1000), 'recycle');
  });

  test('a relaunch keeps the cards count and sets run; a recycle keeps run', () => {
    const re = transition({ n: 1, id: 'x', cards: 2 }, 'relaunch', { run: ask }, cfg, T0);
    assert.deepEqual(re, { n: 1, id: null, cards: 2, failedStarts: 0, run: ask, keepRun: true });
    const next = transition({ ...re, id: 'y' }, 'recycle', {}, cfg, T0);
    assert.deepEqual(next.run, ask);
    assert.equal(next.cards, 3);
  });

  test('the prompt says what the slot runs, or unknown', () => {
    const c = { config: { remote: 'origin', portOffsetStep: 100 } };
    const st = { machine: 'box', target: 't', source: 'flag', slots: [{}] };
    const vars = (slot) => slotVars(c, { n: 1, worktree: '/w', ...slot }, st);
    assert.equal(renderPrompt('{{MODEL}}/{{EFFORT}}', vars({})), 'unknown/unknown');
    assert.equal(renderPrompt('{{MODEL}}/{{EFFORT}}', vars({ run: ask })), 'claude-sonnet-5-5/medium');
  });
});

describe('idle and park', () => {
  test('an idle marker + idle session parks; busy waits; a done marker wins; it wins over a relaunch', () => {
    const ask = { model: 'm', effort: 'low' };
    assert.equal(decide(running, { session: idle, idle: true, activity: T0 }, cfg, T0 + 1000), 'park');
    assert.equal(decide(running, { session: busy, idle: true, activity: T0 }, cfg, T0 + 1000), 'none');
    assert.equal(decide(running, { session: idle, idle: true, marker: true, activity: T0 }, cfg, T0 + 1000), 'recycle');
    assert.equal(decide(running, { session: idle, idle: true, relaunch: ask, activity: T0 }, cfg, T0 + 1000), 'park');
  });

  test('a parked slot launches nothing until the retry is due, then launches', () => {
    const parked = transition({ n: 1, id: 'x', setup: 'done', cards: 2, run: { model: 'm', effort: 'low' } }, 'park', {}, cfg, T0);
    assert.equal(parked.id, null);
    assert.equal(parked.cards, 2, 'no card was finished');
    assert.equal(parked.parkedUntil, T0 + 30 * 60_000);
    assert.equal(decide(parked, {}, cfg, T0 + 29 * 60_000), 'none');
    assert.equal(decide(parked, { stop: true }, cfg, T0 + 60_000), 'none');
    assert.equal(decide(parked, {}, cfg, T0 + 30 * 60_000), 'launch');
    assert.equal(transition(parked, 'launch', { id: 'y' }, cfg, T0 + 30 * 60_000).parkedUntil, null);
  });

  test('the prompt says which phases the loop works, all by default', () => {
    const c = { config: { remote: 'origin', portOffsetStep: 100, idleRetryMinutes: 30 } };
    const st = (phases) => ({ machine: 'box', target: 't', source: 'flag', phases, slots: [{}] });
    const text = (phases) => renderPrompt('{{PHASES}} / {{IDLE_RETRY}}', slotVars(c, { n: 1, worktree: '/w' }, st(phases)));
    assert.equal(text(undefined), 'all / 30');
    assert.equal(text(null), 'all / 30');
    assert.equal(text(['review', 'ready']), 'review, ready / 30');
  });

  test('--phases is parsed in pick order, all means none, and an unknown phase is refused', () => {
    assert.deepEqual(parsePhases(undefined), { phases: null });
    assert.deepEqual(parsePhases('all'), { phases: null });
    assert.deepEqual(parsePhases('Refine, review'), { phases: ['review', 'refine'] });
    assert.match(parsePhases('review,doing').error, /Unknown phase\(s\) doing/);
  });
});

describe('transition', () => {
  test('three failed starts in a row disable the slot, and a success resets the count', () => {
    let s = { n: 1, setup: 'done' };
    s = transition(s, 'launch', { error: 'auth' }, cfg, T0);
    s = transition(s, 'launch', { error: 'auth' }, cfg, T0);
    assert.equal(s.disabled, false);
    s = transition(s, 'launch', { error: 'auth' }, cfg, T0);
    assert.equal(s.disabled, true);
    assert.match(s.reason, /3 failed starts/);
    const ok = transition({ n: 1, failedStarts: 2 }, 'launch', { id: 'x' }, cfg, T0);
    assert.equal(transition(ok, 'recycle', {}, cfg, T0).failedStarts, 0);
  });
});

describe('tick and supervise', () => {
  function world() {
    const calls = [];
    const sessions = new Map();
    let control = {};
    let marker = new Set();
    const idleSlots = new Set();
    const relaunch = new Map();
    let clock = T0;
    let lastWrite = null;
    let next = 0;
    const deps = {
      agents: () => [...sessions.values()],
      launch: (slot, prompt, env) => {
        const id = `id${++next}`;
        sessions.set(id, { id, kind: 'background', status: 'busy', sessionId: id });
        calls.push(['launch', slot.n, prompt, env, slot.run]);
        return { id };
      },
      stop: (id) => {
        calls.push(['stop', id]);
        sessions.delete(id);
      },
      rm: (id) => calls.push(['rm', id]),
      marker: (slot) => marker.has(slot.n),
      clearMarker: (slot) => marker.delete(slot.n),
      relaunchMarker: (slot) => relaunch.get(slot.n) ?? null,
      clearRelaunch: (slot) => relaunch.delete(slot.n),
      idleMarker: (slot) => idleSlots.has(slot.n),
      clearIdle: (slot) => idleSlots.delete(slot.n),
      activity: () => lastWrite ?? clock,
      setup: async () => ({ ok: true }),
      now: () => clock,
      readControl: () => control,
      writeState: () => {},
      refreshClaims: (slots) => calls.push(['refresh', slots]),
      log: () => {},
    };
    return {
      deps,
      calls,
      sessions,
      finish: (n, id) => {
        marker.add(n);
        sessions.get(id).status = 'idle';
      },
      ask: (n, id, run) => {
        relaunch.set(n, run);
        sessions.get(id).status = 'idle';
      },
      hasRelaunch: (n) => relaunch.has(n),
      idle: (n, id) => {
        idleSlots.add(n);
        sessions.get(id).status = 'idle';
      },
      hasIdle: (n) => idleSlots.has(n),
      stop: () => (control = { stop: true }),
      advance: (ms) => (clock += ms),
      silence: () => (lastWrite = clock),
    };
  }
  const ctx = { config: { ...cfg, remote: 'origin', portOffsetStep: 100, env: { OFFICIUM_MACHINE: '{{MACHINE}}' } } };
  const state = () => ({ machine: 'box', target: 'feat/cb-x-sprint-1', source: 'template', slots: [1, 2].map((n) => ({ n, worktree: `/wt/loop-${n}`, setup: 'done' })) });

  test('two slots launch with their own slot, port offset and machine, and recycle independently', async () => {
    const w = world();
    let s = await tick(ctx, state(), w.deps, 'slot {{SLOT}} on {{TARGET}} as {{MACHINE}}');
    const launches = w.calls.filter((c) => c[0] === 'launch');
    assert.equal(launches.length, 2);
    assert.equal(launches[0][2], 'slot 1 on feat/cb-x-sprint-1 as box-loop-1');
    assert.equal(launches[1][3].AUTOLOOP_PORT_OFFSET, '200');
    assert.equal(launches[1][3].OFFICIUM_MACHINE, 'box-loop-2');
    w.finish(1, s.slots[0].id);
    s = await tick(ctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'stop' || c[0] === 'rm').map((c) => c[0]), ['stop', 'rm']);
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(w.calls.filter((c) => c[0] === 'launch').length, 3, 'slot 1 got a fresh session');
    assert.equal(s.slots[0].cards, 1);
  });

  test('a finished session still busy with a silent transcript is recycled after the grace', async () => {
    const w = world();
    let s = await tick(ctx, state(), w.deps, 'p');
    const id = s.slots[0].id;
    w.finish(1, id);
    w.sessions.get(id).status = 'busy';
    w.silence();
    w.advance(60_000);
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(w.calls.filter((c) => c[0] === 'stop').length, 0, 'inside the grace it waits');
    w.advance(61_000);
    s = await tick(ctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'stop' || c[0] === 'rm').map((c) => c[0]), ['stop', 'rm']);
    assert.equal(s.slots[0].cards, 1);
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(w.calls.filter((c) => c[0] === 'launch' && c[1] === 1).length, 2, 'the next poll launches');
  });

  test('a relaunch restarts the slot on the new model and effort, keeping its cards', async () => {
    const w = world();
    let s = await tick(ctx, state(), w.deps, 'p');
    const ask = { model: 'claude-sonnet-5-5', effort: 'medium' };
    w.ask(1, s.slots[0].id, ask);
    s = await tick(ctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'stop' || c[0] === 'rm').map((c) => c[0]), ['stop', 'rm']);
    assert.equal(w.hasRelaunch(1), false, 'the marker is cleared');
    assert.equal(s.slots[0].id, null);
    assert.equal(s.slots[0].cards, undefined, 'no card was finished');
    assert.deepEqual(s.slots[0].run, ask);
    s = await tick(ctx, s, w.deps, 'p');
    const launches = w.calls.filter((c) => c[0] === 'launch' && c[1] === 1);
    assert.equal(launches.length, 2);
    assert.deepEqual(launches[1][4], ask, 'the next launch carries the run');
    // A recycle later keeps the run: the next card of that phase needs no relaunch.
    w.finish(1, s.slots[0].id);
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(s.slots[0].cards, 1);
    assert.deepEqual(s.slots[0].run, ask);
    await tick(ctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'launch' && c[1] === 1)[2][4], ask);
  });

  // No session is spent only on relaunching itself onto the next card's model.
  test('with pickRun, a fresh launch starts on the run the command prints; a relaunched slot keeps its own', async () => {
    const w = world();
    const picked = { model: 'claude-opus-5-5', effort: 'high' };
    const asked = [];
    w.deps.runLiaison = async (command, env) => {
      asked.push([command, env.AUTOLOOP_MACHINE]);
      return { stdout: `${JSON.stringify(picked)}\n` };
    };
    const pctx = { config: { ...ctx.config, pickRun: { command: 'node next-run.mjs' } } };
    let s = await tick(pctx, state(), w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'launch').map((c) => c[4]), [picked, picked]);
    assert.deepEqual(asked[0], ['node next-run.mjs', 'box-loop-1']);
    const ask = { model: 'claude-sonnet-5-5', effort: 'medium' };
    w.ask(1, s.slots[0].id, ask);
    s = await tick(pctx, s, w.deps, 'p');
    s = await tick(pctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'launch' && c[1] === 1)[1][4], ask, 'the claimed card asked for it');
    w.finish(1, s.slots[0].id);
    s = await tick(pctx, s, w.deps, 'p');
    await tick(pctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'launch' && c[1] === 1)[2][4], picked, 'the next card picks again');
  });

  // JAVA-1786: a resumed slot used to keep its last run, which was the run of another phase or role, so it
  // relaunched. It now asks for the run of the card it holds, and the others ask for the cards nobody holds.
  test('a slot that holds a claim asks for that card, and the others exclude every live claim', async () => {
    const w = world();
    const asked = [];
    w.deps.runLiaison = async (command, env) => {
      asked.push(env);
      return { stdout: '{"model":"claude-opus-5-5","effort":"high"}' };
    };
    w.deps.claimOf = (slot) => (slot.n === 1 ? 'JAVA-1786' : null);
    w.deps.liveClaims = () => ['JAVA-1786', 'JAVA-1690'];
    const own = { model: 'claude-haiku-5-5', effort: 'medium' };
    const s = state();
    s.slots[0].run = own;
    await tick({ config: { ...ctx.config, pickRun: { command: 'x' } } }, s, w.deps, 'p');
    const launches = w.calls.filter((c) => c[0] === 'launch');
    assert.deepEqual(launches.find((c) => c[1] === 1)[4], { model: 'claude-opus-5-5', effort: 'high' }, 'the holder starts on its card');
    assert.deepEqual(launches.find((c) => c[1] === 2)[4], { model: 'claude-opus-5-5', effort: 'high' });
    assert.equal(asked.length, 2, 'the holder asked too');
    assert.equal(asked[0].AUTOLOOP_CARD, 'JAVA-1786');
    assert.equal(asked[0].AUTOLOOP_EXCLUDE, undefined);
    assert.equal(asked[1].AUTOLOOP_CARD, undefined);
    assert.equal(asked[1].AUTOLOOP_EXCLUDE, 'JAVA-1786,JAVA-1690');
    assert.equal(asked[1].AUTOLOOP_PHASES, undefined, 'a run with every phase names none');
  });

  // JAVA-1890: a review-only loop was started on Refine cards it could only release (the flow simulation's finding).
  test('a run restricted to some phases asks for a card of those phases', async () => {
    const w = world();
    const asked = [];
    w.deps.runLiaison = async (command, env) => {
      asked.push(env);
      return { stdout: '{"model":"claude-opus-5-5","effort":"high"}' };
    };
    await tick({ config: { ...ctx.config, pickRun: { command: 'x' } } }, { ...state(), phases: ['review'] }, w.deps, 'p');
    assert.equal(asked[0].AUTOLOOP_PHASES, 'review');
  });

  // JAVA-1808: the session ranked the backlog again, took another card and relaunched (39 of 99 on 2026-10-21).
  // It is now told the card its run was picked for; a holder resumes its claim, so it is told none.
  test('the prompt names the card the run was picked for, and none for a holder or a failed pick', async () => {
    const w = world();
    w.deps.runLiaison = async () => ({ stdout: '{"model":"claude-opus-5-5","effort":"max","key":"JAVA-1800"}' });
    w.deps.claimOf = (slot) => (slot.n === 1 ? 'JAVA-1786' : null);
    await tick({ config: { ...ctx.config, pickRun: { command: 'x' } } }, state(), w.deps, 'card {{CARD}}');
    const prompts = Object.fromEntries(w.calls.filter((c) => c[0] === 'launch').map((c) => [c[1], c[2]]));
    assert.deepEqual(prompts, { 1: 'card none', 2: 'card JAVA-1800' });
    assert.deepEqual(w.calls.find((c) => c[0] === 'launch' && c[1] === 2)[4], { model: 'claude-opus-5-5', effort: 'max' }, 'the key is no part of the run');

    const failed = world();
    failed.deps.runLiaison = async () => ({ error: 'exit 1' });
    await tick({ config: { ...ctx.config, pickRun: { command: 'x' } } }, state(), failed.deps, 'card {{CARD}}');
    assert.deepEqual(failed.calls.filter((c) => c[0] === 'launch').map((c) => c[2]), ['card none', 'card none']);
  });

  test('a holder whose pickRun fails keeps the run it had', async () => {
    const w = world();
    w.deps.runLiaison = async () => ({ error: 'exit 1' });
    w.deps.claimOf = (slot) => (slot.n === 1 ? 'JAVA-1786' : null);
    const own = { model: 'claude-haiku-5-5', effort: 'medium' };
    const s = state();
    s.slots[0].run = own;
    await tick({ config: { ...ctx.config, pickRun: { command: 'x' } } }, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'launch' && c[1] === 1)[0][4], own);
  });

  test('a pickRun that fails or prints garbage leaves the slot on the run it had', async () => {
    const w = world();
    w.deps.runLiaison = async () => ({ error: 'exit 1' });
    await tick({ config: { ...ctx.config, pickRun: { command: 'x' } } }, state(), w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'launch').map((c) => c[4]), [undefined, undefined]);
  });

  test('an idle slot is parked, launches nothing until the retry, and its phases reach the prompt', async () => {
    const w = world();
    const st = { ...state(), phases: ['review'] };
    let s = await tick(ctx, st, w.deps, 'phases {{PHASES}}');
    assert.equal(w.calls.find((c) => c[0] === 'launch')[2], 'phases review');
    w.idle(1, s.slots[0].id);
    s = await tick(ctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'stop' || c[0] === 'rm').map((c) => c[0]), ['stop', 'rm']);
    assert.equal(w.hasIdle(1), false, 'the marker is cleared');
    assert.equal(s.slots[0].cards, undefined, 'no card was finished');
    const launches = () => w.calls.filter((c) => c[0] === 'launch' && c[1] === 1).length;
    w.advance(10 * 60_000);
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(launches(), 1, 'parked: no new session yet');
    w.advance(20 * 60_000);
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(launches(), 2, 'the retry is due: a new session looks again');
    assert.equal(s.slots[0].parkedUntil, null);
  });

  test('a relaunch marker on a busy session does nothing yet', async () => {
    const w = world();
    let s = await tick(ctx, state(), w.deps, 'p');
    w.ask(1, s.slots[0].id, { model: 'm', effort: 'high' });
    w.sessions.get(s.slots[0].id).status = 'busy';
    s = await tick(ctx, s, w.deps, 'p');
    assert.equal(w.calls.filter((c) => c[0] === 'stop').length, 0);
    assert.equal(w.hasRelaunch(1), true);
  });

  test('stop stops every session without removing it, then the supervisor ends', async () => {
    const w = world();
    const s = await tick(ctx, state(), w.deps, 'p');
    w.stop();
    const end = await supervise(ctx, s, w.deps, 'p');
    assert.equal(end.running, false);
    assert.equal(w.calls.filter((c) => c[0] === 'stop').length, 2);
    assert.equal(w.calls.filter((c) => c[0] === 'rm').length, 0, 'a stopped conversation stays resumable');
  });

  test('a failed `claude agents` poll decides nothing', async () => {
    const w = world();
    const s = await tick(ctx, state(), w.deps, 'p');
    w.deps.agents = () => null;
    w.advance(60 * 60_000);
    await tick(ctx, s, w.deps, 'p');
    assert.equal(w.calls.filter((c) => c[0] === 'stop').length, 0);
  });

  test('a failed claims refresh does not stop the supervisor (JAVA-669)', async () => {
    const w = world();
    w.deps.refreshClaims = () => {
      throw Object.assign(new Error('ENOENT: claim.json.1'), { code: 'ENOENT' });
    };
    const s = await tick(ctx, state(), w.deps, 'p');
    assert.equal(s.slots.length, 2);
    w.finish(1, s.slots[0].id);
    await tick(ctx, s, w.deps, 'p');
    assert.deepEqual(w.calls.filter((c) => c[0] === 'stop' || c[0] === 'rm').map((c) => c[0]), ['stop', 'rm']);
  });

  test('a failed claims refresh is logged as a poll failure, and the poll still writes its state (JAVA-1785)', async () => {
    const w = world();
    const logs = [];
    w.deps.log = (line) => logs.push(line);
    w.deps.refreshClaims = () => {
      throw new Error('ENOENT: claim.json.8900');
    };
    const s = await tick(ctx, state(), w.deps, 'p');
    assert.ok(logs.includes('poll failed (refresh: ENOENT: claim.json.8900)'), logs.join('\n'));
    assert.equal(s.slots.length, 2);
  });

  for (const [step, config] of [
    ['liaison', { liaison: { command: 'liaison' } }],
    ['remote', { remoteSwitch: { command: 'switch' } }],
  ]) {
    test(`a ${step} that throws is logged as a poll failure, and the supervisor goes on (JAVA-1785)`, async () => {
      const w = world();
      const logs = [];
      w.deps.log = (line) => logs.push(line);
      w.deps.runLiaison = () => {
        throw new Error('spawn boom');
      };
      const liaisonCtx = { config: { ...ctx.config, ...config } };
      const s = await tick(liaisonCtx, state(), w.deps, 'p');
      const next = await tick(liaisonCtx, s, w.deps, 'p');
      assert.ok(logs.includes(`poll failed (${step}: spawn boom)`), logs.join('\n'));
      assert.equal(next.slots.length, 2);
    });
  }

  // card://JAVA-566: one poll that threw ended the supervisor, and with it every slot's recycling.
  test('a poll that throws is logged and the next poll runs', async () => {
    const w = world();
    const logs = [];
    w.deps.log = (line) => logs.push(line);
    const agents = w.deps.agents;
    let polls = 0;
    w.deps.agents = () => {
      if (++polls > 1) return agents();
      w.stop(); // read by the next poll, which ends the supervisor once this one is survived
      throw new Error('claude agents: boom');
    };
    const end = await supervise(ctx, state(), w.deps, 'p');
    assert.equal(polls, 2);
    assert.equal(end.running, false);
    assert.ok(logs.some((l) => /boom/.test(l)), logs.join('\n'));
  });

  test('a slot whose action throws keeps the sessions launched before it in the same poll', async () => {
    const w = world();
    const launch = w.deps.launch;
    w.deps.launch = (slot, ...rest) => {
      if (slot.n === 2) throw new Error('spawn EAGAIN');
      return launch(slot, ...rest);
    };
    w.deps.writeState = () => {
      throw new Error('EACCES: state.json');
    };
    const s = await tick(ctx, state(), w.deps, 'p');
    assert.equal(s.slots[0].id, 'id1', "slot 1's session is not forgotten");
    assert.equal(s.slots[1].id, undefined);
  });
});

// card://JAVA-566: an update notice on stdout made JSON.parse throw inside the poll.
test('`claude agents` output that is not a session list is an unknown poll', { skip: process.platform === 'win32' && 'needs a shebang script' }, () => {
  const dir = mkdtempSync(join(tmpdir(), 'fake-claude-'));
  const agentsFor = (stdout) => {
    const command = join(dir, `claude-${Math.random().toString(36).slice(2)}`);
    writeFileSync(command, `#!/bin/sh\ncat <<'OUT'\n${stdout}\nOUT\n`);
    chmodSync(command, 0o755);
    return liveDeps({ config: { claude: { command, args: [] } } }).agents();
  };
  assert.deepEqual(agentsFor('Update available: run claude update\n[{"id":"a","kind":"background"},{"id":"b","kind":"interactive"}]'), [{ id: 'a', kind: 'background' }]);
  assert.equal(agentsFor('Update available: run claude update'), null);
  assert.equal(agentsFor('{"error":"not a list"}'), null);
  assert.deepEqual(agentsFor(''), []);
});

test('a launch after a relaunch carries --model and --effort before --settings', { skip: process.platform === 'win32' && 'needs a shebang script' }, async () => {
  const dir = mkdtempSync(join(tmpdir(), 'fake-claude-'));
  const argsFile = join(dir, 'args.txt');
  const command = join(dir, 'claude');
  writeFileSync(command, `#!/bin/sh\nprintf '%s\\n' "$@" > '${argsFile}'\necho 'backgrounded · abcdef1'\n`);
  chmodSync(command, 0o755);
  mkdirSync(join(dir, 'state'));
  mkdirSync(join(dir, 'wt'));
  const c = { fs: (p) => p, stateDir: join(dir, 'state'), config: { claude: { command, args: ['--dangerously-skip-permissions'] } } };
  const slot = { n: 1, worktree: join(dir, 'wt'), run: { model: 'claude-sonnet-5-5', effort: 'medium' } };
  assert.deepEqual(await liveDeps(c).launch(slot, 'the prompt', {}), { id: 'abcdef1' });
  const args = readFileSync(argsFile, 'utf8').trim().split('\n');
  assert.deepEqual(args.slice(0, 5), ['--dangerously-skip-permissions', '--model', 'claude-sonnet-5-5', '--effort', 'medium']);
  assert.equal(args[5], '--settings');
});

test('the transcript folder and prompt placeholders', () => {
  assert.equal(projectDirName('\\\\wsl.localhost\\Ubuntu\\home\\dev\\wt\\loop-1'), '--wsl-localhost-Ubuntu-home-dev-wt-loop-1');
  assert.equal(renderPrompt('{{A}} {{B}} {{C}}', { A: 1, B: 'x' }), '1 x {{C}}');
});
