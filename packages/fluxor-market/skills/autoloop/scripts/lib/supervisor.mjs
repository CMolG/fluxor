// The supervisor: no model, one process, detached from the session that launched it. It keeps one
// background Claude session (`claude --bg`) alive per slot, each in its own worktree, and recycles
// it once its card has left its phase, so every card starts with a clean context.
//
// What it reads each poll: `claude agents --json` (a background session is `status: busy|idle`),
// the slot's done marker, and the mtime of the session's transcript (any message or tool result,
// background-task notifications included, writes to it).
import { spawn, spawnSync } from 'node:child_process';
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { list as listClaims, refresh } from './claims.mjs';
import { withWslenv } from './context.mjs';
import { due, enabled, liaisonSlot, liaisonSpawn, openCommand, parse } from './liaison.mjs';
import { dueRemote, parseOrder, remoteEnabled, remoteEnv, standbyAfter } from './remote.mjs';
import { parseRun } from './pick-run.mjs';
import { decide, transition } from './slot-decisions.mjs';
import { TIERS, toolSurface } from './tiers.mjs';

export { decide, transition };

/**
 * What a launch of `slot` starts `claude` with: the configured arguments, the run's model and effort,
 * the tier's tools held back, and the environment with the tier in it. A run with no tier launches as before.
 */
export function launchPlan(ctx, slot, env) {
  const held = toolSurface(slot.run?.toolTier, ctx.config.tiers);
  const run = slot.run ? ['--model', slot.run.model, '--effort', slot.run.effort] : [];
  return { args: [...ctx.config.claude.args, ...run, ...held.args], env: { ...env, ...held.env } };
}

/** The directory name Claude Code keeps a cwd's transcripts under. */
export const projectDirName = (cwd) => cwd.replace(/[^A-Za-z0-9]/g, '-');

export function renderPrompt(template, vars) {
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (m, name) => (name in vars ? String(vars[name]) : m));
}

export function slotVars(ctx, slot, state) {
  const machine = `${state.machine}-loop-${slot.n}`;
  return {
    MACHINE: machine,
    SLOT: slot.n,
    SLOTS: state.slots.length,
    TARGET: state.target,
    TARGET_SOURCE: state.source,
    WORKTREE: slot.worktree,
    REMOTE: ctx.config.remote,
    CLI: ctx.config.cli ?? 'node .harness/skills/autoloop/scripts/autoloop.mjs',
    DONE_MARKER: ctx.config.doneMarker,
    MODEL: slot.run?.model ?? 'unknown',
    EFFORT: slot.run?.effort ?? 'unknown',
    TIER: slot.run?.toolTier ?? 'unknown',
    CARD: slot.card ?? 'none',
    PORT_OFFSET: slot.n * ctx.config.portOffsetStep,
    PHASES: state.phases?.length ? state.phases.join(', ') : 'all',
    IDLE_RETRY: ctx.config.idleRetryMinutes,
  };
}

export function slotEnv(ctx, slot, state, vars) {
  const env = {
    AUTOLOOP_SLOT: String(slot.n),
    AUTOLOOP_SLOTS: String(state.slots.length),
    AUTOLOOP_PORT_OFFSET: String(vars.PORT_OFFSET),
    AUTOLOOP_TARGET: state.target,
    AUTOLOOP_MACHINE: vars.MACHINE,
  };
  for (const [k, v] of Object.entries(ctx.config.env ?? {})) env[k] = renderPrompt(String(v), vars);
  return env;
}

const sameCwd = (a, b) => (a ?? '').replace(/\//g, '\\').toLowerCase() === (b ?? '').replace(/\//g, '\\').toLowerCase();

/** The real world: `claude`, the filesystem and the clock. Tests inject their own. */
export function liveDeps(ctx) {
  const { command } = ctx.config.claude;
  const claude = (args, opts = {}) => spawnSync(command, args, { encoding: 'utf8', windowsHide: true, ...opts });
  const configDir = process.env.CLAUDE_CONFIG_DIR || join(homedir(), '.claude');
  return {
    agents() {
      const r = claude(['agents', '--json']);
      if (r.status !== 0) return null; // unknown this poll: decide nothing from it
      return parseAgents(r.stdout);
    },
    async launch(slot, prompt, baseEnv) {
      const plan = launchPlan(ctx, slot, baseEnv);
      const cwd = ctx.fs(slot.worktree);
      const name = `loop-${slot.n}`;
      const out = ctx.fs(`${ctx.stateDir}/launch-${slot.n}.log`);
      const fd = openSync(out, 'w');
      // The slot's variables go in a per-session settings file, not in this process's environment:
      // every `--bg` session is hosted by Claude Code's background daemon and inherits ITS
      // environment, which is whichever launch started the daemon. On 2026-10-01 both slots ran as
      // slot 1 that way. Settings `env` is applied by the session itself.
      const settings = ctx.fs(`${ctx.stateDir}/slot-${slot.n}.settings.json`);
      const names = Object.keys(plan.env);
      writeFileSync(settings, `${JSON.stringify({ env: { ...plan.env, WSLENV: withWslenv({ WSLENV: process.env.WSLENV ?? '' }, names).WSLENV } }, null, 2)}\n`);
      const since = Date.now();
      // Never waited on: the session lives in Claude Code's background service, and the `claude --bg`
      // that started it was seen still alive after printing its id (2026-10-01), so its exit says
      // nothing about the session and a poll must not hang on it. The id is what is waited for.
      const child = spawn(command, [...plan.args, '--settings', settings, '--bg', '-n', name, prompt], {
        cwd,
        env: withWslenv({ ...process.env, ...plan.env }, names),
        detached: true,
        stdio: ['ignore', fd, fd],
        windowsHide: true,
      });
      let failed = null;
      child.on('error', (e) => (failed = String(e)));
      child.unref();
      closeSync(fd);
      for (let waited = 0; waited < 60_000; waited += 1000) {
        await new Promise((r) => setTimeout(r, 1000));
        const text = readFileSync(out, 'utf8');
        const id = /backgrounded\s*·\s*([0-9a-f]{6,})/.exec(text)?.[1];
        if (id) return { id };
        const found = (this.agents() ?? []).find((a) => a.name === name && sameCwd(a.cwd, cwd) && a.startedAt >= since - 5000);
        if (found) return { id: found.id };
        if (failed || (child.exitCode !== null && child.exitCode !== 0)) return { error: (failed ?? text.trim()).slice(0, 500) || `exit ${child.exitCode}` };
      }
      return { error: `no session named ${name} appeared within 60 s; see ${out}` };
    },
    stop: (id) => claude(['stop', id]),
    rm: (id) => claude(['rm', id]),
    marker: (slot) => existsSync(ctx.fs(`${slot.worktree}/${ctx.config.doneMarker}`)),
    clearMarker: (slot) => rmSync(ctx.fs(`${slot.worktree}/${ctx.config.doneMarker}`), { force: true }),
    relaunchMarker(slot) {
      const r = readJsonSafe(ctx.fs(`${slot.worktree}/${ctx.config.relaunchMarker}`));
      if (!r?.model || !r?.effort) return null;
      // A tier the supervisor does not know is no relaunch at all: it would otherwise start the session unheld.
      if (r.toolTier !== undefined && !TIERS.includes(r.toolTier)) return null;
      // A marker that names no tier keeps the one the slot runs held under: a held session does not drop its hold by relaunching.
      const toolTier = r.toolTier ?? (TIERS.includes(slot.run?.toolTier) ? slot.run.toolTier : undefined);
      return { model: String(r.model), effort: String(r.effort), ...(toolTier ? { toolTier } : {}) };
    },
    clearRelaunch: (slot) => rmSync(ctx.fs(`${slot.worktree}/${ctx.config.relaunchMarker}`), { force: true }),
    idleMarker: (slot) => existsSync(ctx.fs(`${slot.worktree}/${ctx.config.idleMarker}`)),
    clearIdle: (slot) => rmSync(ctx.fs(`${slot.worktree}/${ctx.config.idleMarker}`), { force: true }),
    activity(slot, session) {
      try {
        return statSync(join(configDir, 'projects', projectDirName(ctx.fs(slot.worktree)), `${session.sessionId}.jsonl`)).mtimeMs;
      } catch {
        return null;
      }
    },
    setup(slot, env) {
      // Asynchronous: one slot installing its dependencies holds up no other slot.
      const log = ctx.fs(`${ctx.stateDir}/setup-${slot.n}.log`);
      const cmd = ctx.distro
        ? ['wsl.exe', ['-d', ctx.distro, '--cd', slot.worktree, '--', 'bash', '-lc', ctx.config.setup]] // a login shell: package managers live on the profile's PATH
        : ['sh', ['-c', ctx.config.setup]];
      return new Promise((resolve) => {
        const child = spawn(cmd[0], cmd[1], {
          cwd: ctx.distro ? undefined : slot.worktree,
          env: withWslenv({ ...process.env, ...env }, Object.keys(env)),
          stdio: ['ignore', 'pipe', 'pipe'],
          windowsHide: true,
        });
        let out = '';
        child.stdout.on('data', (d) => (out += d));
        child.stderr.on('data', (d) => (out += d));
        child.on('error', (e) => resolve({ ok: false, error: String(e) })); // unhandled, it ends the supervisor
        child.on('close', (code) => {
          writeFileSync(log, out);
          resolve(code === 0 ? { ok: true } : { ok: false, error: `setup exited ${code}; see ${log}` });
        });
      });
    },
    runLiaison(command, env) {
      // Asynchronous, so no poll waits on it. The command is the project's own shell line.
      return new Promise((resolve) => {
        const [file, args, options] = liaisonSpawn(ctx, command, env, process.env);
        const child = spawn(file, args, options);
        let out = '';
        child.stdout.on('data', (d) => (out += d));
        child.on('error', (e) => resolve({ error: String(e) }));
        child.on('close', (code, signal) => resolve(code === 0 ? { stdout: out } : { error: `exit ${code ?? signal}${out.trim() ? `: ${out.trim().slice(0, 160)}` : ''}` }));
      });
    },
    openUrl(url) {
      const [file, args] = openCommand(process.platform, process.env, url);
      const child = spawn(file, args, { detached: true, stdio: 'ignore', windowsHide: true });
      child.on('error', () => {}); // a browser that will not open decides nothing
      child.unref();
    },
    now: () => Date.now(),
    readControl: () => readJsonSafe(ctx.fs(`${ctx.stateDir}/control.json`)) ?? {},
    writeState: (state) => writeAtomic(ctx.fs(`${ctx.stateDir}/state.json`), state),
    refreshClaims: (slots) => refresh(ctx.fs(`${ctx.stateDir}/claims`), slots),
    claimOf: (slot) => listClaims(ctx.fs(`${ctx.stateDir}/claims`)).find((c) => c.slot === String(slot.n))?.key ?? null,
    // A stale claim has no live supervisor behind it and may be taken over, so its card is still for the picking.
    liveClaims: () => listClaims(ctx.fs(`${ctx.stateDir}/claims`)).filter((c) => !c.stale).map((c) => c.key),
    log: (line) => console.log(`${new Date().toISOString()} ${line}`),
  };
}

/**
 * The background sessions in `claude agents --json` output, or null when it is no session list,
 * which makes the poll an unknown one. A notice printed before the list (an update available) is
 * skipped: unparsed, one ended the supervisor.
 */
export function parseAgents(stdout) {
  const text = stdout?.trim() || '[]';
  const start = text.search(/^\s*\[/m);
  try {
    const all = JSON.parse(start < 0 ? text : text.slice(start));
    return Array.isArray(all) ? all.filter((a) => a?.kind === 'background') : null;
  } catch {
    return null;
  }
}

export function readJsonSafe(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    return null;
  }
}

export function writeAtomic(path, data) {
  mkdirSync(dirname(path), { recursive: true });
  const tmp = `${path}.${process.pid}.tmp`;
  writeFileSync(tmp, `${JSON.stringify(data, null, 2)}\n`);
  renameSync(tmp, path);
}

let liaisonResult = null; // the answer of the liaison command in flight, read by the next poll
let liaisonRunning = false;

const setupResults = new Map(); // slot -> result of its asynchronous setup, read by the next poll

// The remote command in flight and its answer, read by the next poll: one per supervisor (its `deps`), so two
// supervisors in one process, tests included, never read each other's answer.
const remoteFlights = new WeakMap();
const flightOf = (deps) => remoteFlights.get(deps) ?? remoteFlights.set(deps, { result: null, running: false }).get(deps);

/** One poll over every slot. Returns the new state; `deps` does the I/O. */
/** One step of a poll: when it throws, the poll logs it and keeps `kept`, and the supervisor lives on. */
function guarded(deps, name, step, kept) {
  try {
    return step();
  } catch (e) {
    deps.log(`poll failed (${name}: ${e.message})`);
    return kept;
  }
}

export async function tick(ctx, state, deps, template) {
  const control = deps.readControl();
  const stop = Boolean(control.stop);
  // Standby (the remote switch's stop, or `start --standby`): every session stopped, none launched.
  const standby = Boolean(state.standby);
  if (control.target && control.target !== state.target) {
    deps.log(`control branch: ${state.target} -> ${control.target}`);
    state = { ...state, target: control.target, source: control.source ?? state.source };
  }
  const agents = deps.agents();
  const now = deps.now();
  const slots = [];
  for (const before of state.slots) {
    try {
      slots.push(await step(before));
    } catch (e) {
      // One slot that throws costs that slot this poll, not the sessions the others launched in it.
      deps.log(`slot ${before.n}: poll failed, kept as it was (${e.message})`);
      slots.push(before);
    }
  }
  async function step(slot) {
    const session = agents?.find((a) => a.id === slot.id) ?? null;
    if (session) slot = { ...slot, seen: true, status: session.status };
    if (agents === null && slot.id && !(stop || standby)) return slot; // `claude agents` failed this poll: an absent session proves nothing
    const obs = {
      session,
      stop: stop || standby,
      marker: slot.id ? deps.marker(slot) : false,
      relaunch: slot.id ? deps.relaunchMarker(slot) : null,
      idle: slot.id ? deps.idleMarker(slot) : false,
      activity: session ? deps.activity(slot, session) : null,
    };
    const action = decide(slot, obs, ctx.config, now);
    let result = {};
    if (action === 'launch') {
      // Start on the run the next card asks for, so no session is spent only on relaunching. A slot that a
      // relaunch just restarted keeps its run. A slot that holds a claim asks for THAT card's run (it resumes
      // it: its own last run may be the card of another phase or role); any other asks for the first
      // card no slot on this machine holds, so six slots do not all start on the run of one card.
      // The card the run was picked for is handed to the session ({{CARD}}), which claims it instead of ranking the
      // backlog again: a second ranking took another card and relaunched (39 of 99 sessions, measured on 2026-10-21).
      slot = { ...slot, card: null };
      if (ctx.config.pickRun?.command && !slot.keepRun) {
        const claimed = deps.claimOf?.(slot) ?? null;
        const env = { AUTOLOOP_MACHINE: slotVars(ctx, slot, state).MACHINE };
        if (claimed) env.AUTOLOOP_CARD = claimed;
        else env.AUTOLOOP_EXCLUDE = (deps.liveClaims?.() ?? []).join(',');
        // A run restricted to some phases picks only in them: a review-only loop was started on cards it could only release.
        if (state.phases?.length) env.AUTOLOOP_PHASES = state.phases.join(',');
        const picked = parseRun((await deps.runLiaison(ctx.config.pickRun.command, env))?.stdout);
        if (picked) {
          const { card, ...run } = picked;
          slot = { ...slot, run, card: claimed ? null : (card ?? null) };
        }
      }
      const vars = slotVars(ctx, slot, state);
      // Read again for every launch, so an edit to the prompt reaches the next session.
      const text = typeof template === 'function' ? template() : template;
      result = await deps.launch(slot, renderPrompt(text, vars), slotEnv(ctx, slot, state, vars));
    } else if (action === 'recycle' || action === 'recycle-silent' || action === 'relaunch' || action === 'park') {
      deps.stop(slot.id);
      deps.rm(slot.id);
      if (action === 'recycle') deps.clearMarker(slot);
      // A request a recycle overtook must not restart or park the next session; each answers its own.
      deps.clearRelaunch(slot);
      deps.clearIdle(slot);
      if (action === 'relaunch') result = { run: obs.relaunch }; // claims and the done marker stay
    } else if (action === 'stop') {
      deps.stop(slot.id); // the conversation is kept, and so is the worktree with its changes
    } else if (action === 'setup') {
      const vars = slotVars(ctx, slot, state);
      const n = slot.n;
      deps.setup(slot, slotEnv(ctx, slot, state, vars)).then(
        (r) => setupResults.set(n, r),
        (e) => setupResults.set(n, { ok: false, error: String(e) }),
      );
    }
    if (action !== 'none') deps.log(`slot ${slot.n}: ${action}${result.id ? ` ${result.id}` : ''}${result.error ? ` (${result.error})` : ''}`);
    slot = transition(slot, action, result, ctx.config, now);
    const done = setupResults.get(slot.n);
    if (slot.setup === 'running' && done) {
      slot = done.ok ? { ...slot, setup: 'done' } : { ...slot, setup: 'failed', disabled: true, reason: done.error };
      deps.log(`slot ${slot.n}: setup ${done.ok ? 'done' : `failed (${done.error})`}`);
      setupResults.delete(slot.n);
    }
    return slot;
  }
  // A step that fails is retried next poll; a supervisor that dies leaves every slot unrecycled.
  guarded(deps, 'refresh', () => deps.refreshClaims(slots.filter((s) => s.id || s.setup === 'done').map((s) => s.n)), undefined);
  const liaison = guarded(deps, 'liaison', () => stepLiaison(ctx, state, slots, deps, now, stop), state.liaison ?? null);
  const switched = guarded(deps, 'remote', () => stepRemote(ctx, state, slots, deps, now, stop), {
    remote: state.remoteSwitch ?? null, standby: Boolean(state.standby),
  });
  const next = {
    ...state, slots, updatedAt: now, stopping: stop, stopReason: control.reason ?? null, liaison,
    remoteSwitch: switched.remote, standby: switched.standby,
  };
  try {
    deps.writeState(next);
  } catch (e) {
    deps.log(`state write failed: ${e.message}`); // the next poll writes it again
  }
  return next;
}

/**
 * The liaison, once a poll: with 2 or more slots it runs `liaison.command` every `pollSeconds` on
 * behalf of the lowest slot, never blocking the poll, and opens the URL an answer carries. A
 * failure or garbage is logged and decides nothing. Returns the state's `liaison`, or null.
 */
function stepLiaison(ctx, state, slots, deps, now, stop) {
  if (!enabled(ctx.config, slots)) return null;
  let last = state.liaison ?? null;
  if (liaisonResult) {
    const r = liaisonResult;
    liaisonResult = null;
    const answer = r.error ? null : parse(r.stdout);
    if (!answer) {
      const error = r.error ?? 'the command printed no valid line';
      deps.log(`liaison: ${error}`);
      last = { ...last, error };
    } else {
      last = { ...last, pending: answer.pending, summary: answer.summary, error: null };
      if (answer.open) {
        try {
          deps.openUrl(answer.open);
          deps.log(`liaison: opened Officium (${answer.pending} pending)`);
        } catch (e) {
          deps.log(`liaison: could not open the browser (${e.message})`);
        }
      }
    }
  }
  if (!stop && !liaisonRunning && due(last, ctx.config, now)) {
    const n = liaisonSlot(slots);
    if (n !== null) {
      const machine = `${state.machine}-loop-${n}`;
      last = { ...last, slot: n, at: now };
      liaisonRunning = true;
      deps.runLiaison(ctx.config.liaison.command, { AUTOLOOP_MACHINE: machine }).then(
        (r) => (liaisonResult = r),
        (e) => (liaisonResult = { error: String(e) }),
      ).finally(() => (liaisonRunning = false));
    }
  }
  return last;
}

/**
 * The remote switch, once a poll: it runs `remoteSwitch.command` every `pollSeconds` with the loop's state, never
 * blocking the poll, and applies the order the last run printed. A failure or garbage is logged and decides
 * nothing. Returns the state's `remoteSwitch` and whether the loop stands by now.
 */
function stepRemote(ctx, state, slots, deps, now, stop) {
  let standby = Boolean(state.standby);
  if (!remoteEnabled(ctx.config)) return { remote: null, standby };
  let last = state.remoteSwitch ?? null;
  const flight = flightOf(deps);
  if (flight.result) {
    const r = flight.result;
    flight.result = null;
    const order = r.error ? null : parseOrder(r.stdout);
    if (!order) {
      const error = r.error ?? 'the command printed no valid line';
      deps.log(`remote: ${error}`);
      last = { ...last, error };
    } else {
      const after = standbyAfter(standby, order.command);
      if (after !== standby) deps.log(after ? `remote: stop${order.reason ? ` (${order.reason})` : ''}, standing by` : 'remote: start');
      standby = after;
      last = { ...last, error: null, command: order.command };
      if (order.command === 'start') last = { ...last, stopReason: null, gate: null };
      if (order.command === 'stop') last = { ...last, stopReason: order.reason ?? null, gate: order.gate ?? null };
    }
  }
  if (!stop && !flight.running && dueRemote(last, ctx.config, now)) {
    last = { ...last, at: now };
    flight.running = true;
    deps.runLiaison(ctx.config.remoteSwitch.command, remoteEnv(state, standby, slots)).then(
      (r) => (flight.result = r),
      (e) => (flight.result = { error: String(e) }),
    ).finally(() => (flight.running = false));
  }
  return { remote: last, standby };
}

export async function supervise(ctx, state, deps, template) {
  deps.log(`supervisor ${process.pid}: ${state.slots.length} slots, control branch ${state.target}`);
  for (;;) {
    try {
      state = await tick(ctx, state, deps, template);
    } catch (e) {
      // A poll that throws decides nothing and the next one runs: a supervisor that dies leaves
      // every slot unrecycled and every claim to go stale.
      deps.log(`poll failed, skipped: ${e.stack ?? e}`);
    }
    if (state.stopping && state.slots.every((s) => !s.id)) {
      const end = { ...state, running: false };
      deps.writeState(end);
      deps.log(`stopped${state.stopReason ? `: ${state.stopReason}` : ''}`);
      return end;
    }
    await new Promise((r) => setTimeout(r, ctx.config.pollSeconds * 1000));
  }
}
