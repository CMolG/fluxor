#!/usr/bin/env node
// The autoloop: N background Claude sessions, each on a different card in its own worktree,
// integrating into one control branch. See ../SKILL.md for the protocol; this is its tooling.
//
// For the person (through `/autoloop`):
//   start [n] [--target <branch>] [--sprint <n>] [--phases <p,...>]
//                                                   prepare worktrees, launch the supervisor; the
//                                                   workers take cards only in those phases (review,
//                                                   ready, todo, refine; default all); exit 6 when
//                                                   the config's pickRun fails on this machine
//   status [--json]                                 slot, worktree, session, card, state
//   stop [--reason <text>]                          stop every session; worktrees are kept as they are
// For a worker session (run from its worktree):
//   slot                          this slot: branch, uncommitted changes, the cards it holds
//   claim <KEY> [<KEY>...]        claim the first free card of the list, in priority order
//   release <KEY> [--any]         free a card
//   claims [--json]               every claimed card and its slot
//   begin <KEY>                   switch to wt/<KEY> (made from the control branch's tip)
//   publish <KEY>                 push wt/<KEY> for its reviewer
//   integrate <KEY> merge|push|abort    the review's integration into the control branch
//   target [--check] [--sprint <n>]     the control branch; whether it is spent; move to a sprint's
//   done [--forced <reason>]      release this slot's cards, park the worktree, write the done marker;
//                                 refused (exit 7) while the config's doneCheck says the unit still has
//                                 work; --forced run-killed|environment|context goes past it
//   relaunch --model <m> --effort <e> [--tier <t>]   restart this slot on that model, effort and tier, keeping its card
//   idle [--reason <text>]        nothing to claim: park this slot until the retry is due
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, openSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import * as claims from './lib/claims.mjs';
import { machineName, openContext, parsePhases, projectTag } from './lib/context.mjs';
import * as finish from './lib/finish.mjs';
import * as integration from './lib/integrate.mjs';
import { liaisonSpawn } from './lib/liaison.mjs';
import { liveDeps, readJsonSafe, supervise, writeAtomic } from './lib/supervisor.mjs';
import { checkSpent, currentRound, ensureRemoteBranch, onSpent, resolveTarget } from './lib/target.mjs';
import { composeTemplate } from './lib/template.mjs';

const SCRIPT = fileURLToPath(import.meta.url);
const argv = process.argv.slice(2);
if (argv.length === 0 || argv.includes('--help') || argv.includes('-h')) {
  // The usage is this file's header comment, so it cannot drift from a second copy.
  const lines = readFileSync(SCRIPT, 'utf8').split('\n').slice(1);
  const header = lines.slice(0, lines.findIndex((l) => !l.startsWith('//')));
  console.log(header.map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
  process.exit(0);
}
const flag = (name) => {
  const i = argv.indexOf(name);
  if (i < 0) return undefined;
  const v = argv[i + 1];
  argv.splice(i, 2);
  return v;
};
const bool = (name) => {
  const i = argv.indexOf(name);
  if (i >= 0) argv.splice(i, 1);
  return i >= 0;
};

function fail(message, code = 1) {
  console.error(message);
  process.exit(code);
}

// Every flag is taken out before the positional arguments are read.
const root = flag('--root');
const asJson = bool('--json');
const opt = {
  slot: flag('--slot'),
  slots: flag('--slots'),
  target: flag('--target'),
  sprint: flag('--sprint'),
  phases: flag('--phases'),
  reason: flag('--reason'),
  model: flag('--model'),
  effort: flag('--effort'),
  tier: flag('--tier'),
  any: bool('--any'),
  check: bool('--check'),
  standby: bool('--standby'),
  forced: flag('--forced'),
};
const [command, ...rest] = argv;
const ctx = openContext({ root });
const state = () => readJsonSafe(ctx.fs(`${ctx.stateDir}/state.json`));
const claimsDir = () => ctx.fs(`${ctx.stateDir}/claims`);
const ttlMs = () => ctx.config.claimTtlMinutes * 60_000;
/**
 * This session's slot. A slot worktree (`<worktreePrefix><n>`) names its own slot, and that wins:
 * a variable can arrive wrong (on 2026-10-01 a daemon handed slot 1's to slot 2, and both claimed
 * the same card), so a mismatch stops here instead of sharing claims.
 */
function slotId() {
  const given = process.env.AUTOLOOP_SLOT ?? opt.slot ?? null;
  const here = ctx.root.split('/').pop();
  const own = here.startsWith(ctx.config.worktreePrefix) && /^\d+$/.test(here.slice(ctx.config.worktreePrefix.length))
    ? here.slice(ctx.config.worktreePrefix.length)
    : null;
  if (own && given && given !== own) fail(`This worktree is slot ${own}, but AUTOLOOP_SLOT says ${given}: refusing, two slots would share claims.`, 6);
  return own ?? given ?? '0';
}
const target = () => process.env.AUTOLOOP_TARGET || state()?.target || ctx.config.target || fail('No control branch: is the loop running? (`status`)');
// A poll can take a launch (up to a minute) longer than pollSeconds; and a killed supervisor stops
// writing without a word, so its pid is asked too wherever a pid means something to this process.
const exists = (pid) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === 'EPERM';
  }
};
const alive = (s) =>
  Boolean(s && s.running !== false && Date.now() - s.updatedAt < ctx.config.pollSeconds * 4000 + 120_000) &&
  (s.platform !== process.platform || !s.pid || exists(s.pid));
const out = (data, text) => console.log(asJson ? JSON.stringify(data, null, 2) : text);
/** A config command asked once from the project root: its ONE JSON line, or null when it cannot answer. */
function askOnce(command, env) {
  const [file, args, options] = liaisonSpawn(ctx, command, env, process.env);
  const run = spawnSync(file, args, { ...options, encoding: 'utf8' });
  const lines = String(run.stdout ?? '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (run.status !== 0 || lines.length !== 1) return null;
  try {
    return JSON.parse(lines[0]);
  } catch {
    return null;
  }
}
const worker = { ctx, fail, opt, slotId, claimsDir, ttlMs, state, ask: askOnce }; // what finish.mjs needs of this file

function loadTemplate() {
  const own = readFileSync(fileURLToPath(new URL('../prompt.md', import.meta.url)), 'utf8');
  const extra = ctx.config.prompt ? readFileSync(ctx.fs(`${ctx.root}/${ctx.config.prompt}`), 'utf8') : '';
  return composeTemplate(own, extra);
}

function worktrees() {
  const listed = ctx.git(['worktree', 'list', '--porcelain']).stdout;
  return new Set([...listed.matchAll(/^worktree (.+)$/gm)].map((m) => m[1]));
}

const commands = {
  start() {
    const n = Number(rest[0] ?? opt.slots ?? ctx.config.slots);
    if (!Number.isInteger(n) || n < 1 || n > ctx.config.maxSlots) fail(`Slots must be 1..${ctx.config.maxSlots} (maxSlots in the config).`);
    const current = state();
    if (alive(current) && !current.stopping) fail(`The loop is already running (supervisor ${current.pid}, ${current.slots.length} slots). \`status\`, or \`stop\` first.`);
    const { phases, error: badPhases } = parsePhases(opt.phases);
    if (badPhases) fail(badPhases, 2);
    if (opt.standby && !ctx.config.remoteSwitch?.command) fail('--standby needs a remote switch: set remoteSwitch.command in the config.', 2);
    // A pickRun that cannot answer starts every session on an unknown run, so every session relaunches, and a
    // resumed sweep is read blind (2026-11-03: a machine with no heartbeat token). Asked once, as the supervisor
    // asks it, before anything is created.
    if (ctx.config.pickRun?.command) {
      const env = { AUTOLOOP_MACHINE: `${machineName(ctx.config.machineName)}-loop-1`, ...(phases?.length ? { AUTOLOOP_PHASES: phases.join(',') } : {}) };
      const [file, args, options] = liaisonSpawn(ctx, ctx.config.pickRun.command, env, process.env);
      const probe = spawnSync(file, args, { ...options, encoding: 'utf8' });
      if (probe.status !== 0) {
        const why = String(probe.stderr ?? '').trim().split(/\r?\n/).pop() || String(probe.error ?? `exit ${probe.status ?? probe.signal}`);
        fail(`pickRun failed on this machine: ${why}. Every session would start on an unknown run and relaunch; fix it, then start again.`, 6);
      }
    }
    // What this machine cannot run, said before a session spends its time finding out (an epic's
    // gate ran 12.5 minutes on a Mac with no dev API to learn it). It warns and goes on: plans and reviews still run.
    if (ctx.config.preflight?.command) {
      const [file, args, options] = liaisonSpawn(ctx, ctx.config.preflight.command, {}, process.env);
      const check = spawnSync(file, args, { ...options, encoding: 'utf8', timeout: 120_000 });
      if (check.status !== 0) console.error(`preflight: this machine cannot run everything a card may ask for:\n${String(check.stdout ?? '').trim() || String(check.stderr ?? '').trim()}`);
    }
    const resolved = resolveTarget({ flag: opt.target, config: ctx.config, sprint: opt.sprint, projectTag: projectTag(ctx) });
    if (resolved.error) fail(resolved.error, 2);
    if (resolved.source === 'template') resolved.branch = currentRound(ctx, resolved.branch).branch;
    const spent = checkSpent(ctx, resolved.branch);
    if (spent.spent) fail(`${resolved.branch} is spent: PR #${spent.pr} merged at ${spent.mergedAt}. ${onSpent(resolved.source).say}`, 5);
    const made = ensureRemoteBranch(ctx, resolved.branch);
    mkdirSync(ctx.fs(`${ctx.stateDir}/claims`), { recursive: true });
    const have = worktrees();
    const base = ctx.expand(ctx.config.worktreeRoot);
    const slots = [];
    for (let i = 1; i <= n; i++) {
      const worktree = `${base}/${ctx.config.worktreePrefix}${i}`;
      let setup = 'done';
      if (!have.has(worktree)) {
        if (existsSync(ctx.fs(worktree))) fail(`${worktree} exists and is not a worktree of this repository.`);
        const add = ctx.git(['worktree', 'add', '--detach', worktree, `${ctx.config.remote}/${resolved.branch}`]);
        if (add.status !== 0) fail(add.stderr.trim());
        setup = ctx.config.setup ? 'pending' : 'done';
      }
      const previous = current?.slots?.find((s) => s.n === i);
      // A session the last supervisor left running (it was killed, not stopped) is adopted, not
      // launched twice into the same worktree; a stopped one left no id behind.
      const adopted = previous?.id ? { id: previous.id, launchedAt: previous.launchedAt, seen: previous.seen } : {};
      const kept = { ...(previous?.run ? { run: previous.run } : {}), ...(previous?.cards ? { cards: previous.cards } : {}) };
      slots.push({ n: i, worktree, setup: previous?.setup === 'pending' ? 'pending' : setup, failedStarts: 0, ...adopted, ...kept });
    }
    writeAtomic(ctx.fs(`${ctx.stateDir}/control.json`), { stop: false });
    const initial = {
      pid: null,
      startedAt: Date.now(),
      updatedAt: Date.now(),
      machine: machineName(ctx.config.machineName),
      target: resolved.branch,
      source: resolved.source,
      phases,
      slots,
      // A loop started in standby launches nothing until its remote switch says start (`remoteSwitch` in the config).
      standby: opt.standby,
    };
    writeAtomic(ctx.fs(`${ctx.stateDir}/state.json`), initial);
    const log = openSync(ctx.fs(`${ctx.stateDir}/supervisor.log`), 'a');
    const child = spawn(process.execPath, [SCRIPT, 'supervise', '--root', ctx.fs(ctx.root)], {
      detached: true,
      stdio: ['ignore', log, log],
      windowsHide: true,
    });
    child.unref();
    out(
      { pid: child.pid, target: resolved.branch, source: resolved.source, created: made.created, phases, standby: opt.standby, slots },
      [
        `Supervisor ${child.pid} started: ${n} slot(s) on ${resolved.branch} (${resolved.source}${made.created ? ', created from the base branch' : ''}), phases ${phases?.join(',') ?? 'all'}.`,
        ...slots.map((s) => `  slot ${s.n}  ${s.worktree}${s.setup === 'pending' ? '  (setup first)' : ''}${s.id ? `  (adopted session ${s.id})` : ''}`),
        `Log: ${ctx.stateDir}/supervisor.log`,
      ].join('\n'),
    );
  },

  async supervise() {
    const s = state() ?? fail('No state.json: run `start`.');
    await supervise(ctx, { ...s, pid: process.pid, platform: process.platform, running: true }, liveDeps(ctx), loadTemplate);
  },

  status() {
    const s = state();
    if (!s) return out({ running: false }, 'The loop has never run here.');
    const held = claims.list(claimsDir(), { ttlMs: ttlMs() });
    const rows = s.slots.map((slot) => {
      const branch = ctx.run('git', ['branch', '--show-current'], { cwd: slot.worktree }).stdout.trim() || 'detached';
      const cards = held.filter((c) => c.slot === String(slot.n)).map((c) => c.key);
      const parked = !slot.id && slot.parkedUntil > Date.now() ? `parked until ${new Date(slot.parkedUntil).toISOString().slice(11, 16)}Z` : null;
      const st = slot.disabled ? `disabled: ${slot.reason}` : slot.setup === 'running' || slot.setup === 'pending' ? `setup ${slot.setup}` : slot.id ? slot.status ?? 'starting' : parked ?? 'idle slot';
      return { slot: slot.n, worktree: slot.worktree, session: slot.id, branch, cards, state: st, cardsDone: slot.cards ?? 0 };
    });
    const running = alive(s);
    out(
      { running, stopping: Boolean(s.stopping), pid: s.pid, target: s.target, source: s.source, phases: s.phases ?? null, slots: rows, liaison: s.liaison ?? null, standby: Boolean(s.standby), remoteSwitch: s.remoteSwitch ?? null, claims: held },
      [
        `${running ? (s.stopping ? 'Stopping' : s.standby ? 'Standing by' : 'Running') : 'Not running'} · supervisor ${s.pid ?? '-'} · control branch ${s.target} (${s.source}) · phases ${s.phases?.join(',') ?? 'all'} · updated ${new Date(s.updatedAt).toISOString()}`,
        ...(s.standby && s.remoteSwitch?.stopReason
          ? [
              `Stopped by the tracker: ${s.remoteSwitch.stopReason}`,
              ...(s.remoteSwitch.gate?.branch ? [`  branch ${s.remoteSwitch.gate.branch}${s.remoteSwitch.gate.compareUrl ? ` · ${s.remoteSwitch.gate.compareUrl}` : ''}`] : []),
              ...(s.remoteSwitch.gate?.wallCard ? [`  merge card ${s.remoteSwitch.gate.wallCard}`] : []),
            ]
          : []),
        ...(s.liaison ? [`  liaison  slot ${s.liaison.slot}  ${s.liaison.error ? `error: ${s.liaison.error}` : `${s.liaison.pending ?? '-'} pending${s.liaison.summary ? ` · ${s.liaison.summary}` : ''}`}  (last run ${s.liaison.at ? new Date(s.liaison.at).toISOString() : '-'})`] : []),
        ...rows.map((r) => `  slot ${r.slot}  ${r.state.padEnd(10)}  ${(r.session ?? '-').padEnd(8)}  ${r.cards.join(',') || '-'}  ${r.branch}  ${r.worktree}  (${r.cardsDone} done)`),
      ].join('\n'),
    );
  },

  stop() {
    const reason = opt.reason ?? rest.join(' ');
    writeAtomic(ctx.fs(`${ctx.stateDir}/control.json`), { stop: true, reason: reason || null });
    const s = state();
    if (alive(s)) return out({ stopping: true }, `Asked supervisor ${s.pid} to stop every session (within ${ctx.config.pollSeconds}s). Worktrees and their changes are kept.`);
    // No supervisor to do it: stop what the last state names, directly.
    const deps = liveDeps(ctx);
    for (const slot of s?.slots ?? []) if (slot.id) deps.stop(slot.id);
    out({ stopping: true, direct: true }, 'No live supervisor; stopped the sessions it had left. Worktrees and their changes are kept.');
  },

  claim() {
    if (!rest.length) fail('claim <KEY> [<KEY>...]: the candidates in priority order.');
    const r = claims.claimFirst(claimsDir(), rest, { slot: slotId(), session: process.env.CLAUDE_SESSION_ID ?? '', ttlMs: ttlMs() });
    if (r.key) return out(r, `claimed ${r.key}`);
    out(r, `taken: ${r.taken.map((c) => `${c.key} (slot ${c.slot})`).join(', ')}`);
    process.exit(1);
  },

  release() {
    const { any } = opt;
    for (const key of rest) console.log(claims.release(claimsDir(), key, { slot: slotId(), any }) ? `released ${key}` : `${key} was not claimed`);
  },

  claims() {
    const all = claims.list(claimsDir(), { ttlMs: ttlMs() });
    out(all, all.map((c) => `${c.key}  slot ${c.slot}${c.stale ? '  (stale)' : ''}`).join('\n') || 'no claims');
  },

  slot() {
    const branch = ctx.git(['branch', '--show-current']).stdout.trim() || null;
    const dirty = ctx.git(['status', '--porcelain', '--untracked-files=no']).stdout.trim() !== '';
    const merging = ctx.git(['rev-parse', '-q', '--verify', 'MERGE_HEAD']).status === 0;
    const mine = claims.list(claimsDir(), { ttlMs: ttlMs() }).filter((c) => c.slot === slotId()).map((c) => c.key);
    const resume = mine.length > 0 || dirty || merging || /^wt\//.test(branch ?? '');
    out(
      { slot: slotId(), branch, dirty, merging, cards: mine, resume },
      `slot ${slotId()} · ${branch ?? 'detached'}${dirty ? ' · uncommitted changes' : ''}${merging ? ' · merge in progress' : ''} · cards: ${mine.join(', ') || 'none'}${resume ? '\nRESUME: finish this before picking a new card.' : ''}`,
    );
  },

  begin() {
    const key = rest[0] ?? fail('begin <KEY>');
    const { remote } = ctx.config;
    const tgt = target();
    if (ctx.git(['status', '--porcelain', '--untracked-files=no']).stdout.trim()) fail('Uncommitted changes in this worktree: finish or discard them first.');
    ctx.git(['fetch', '-q', remote, tgt]);
    ctx.git(['fetch', '-q', remote, `wt/${key}`]);
    const local = ctx.git(['rev-parse', '-q', '--verify', `refs/heads/wt/${key}`]).status === 0;
    const published = ctx.git(['rev-parse', '-q', '--verify', `refs/remotes/${remote}/wt/${key}`]).status === 0;
    const args = local
      ? ['switch', `wt/${key}`]
      : ['switch', '--no-track', '-c', `wt/${key}`, published ? `${remote}/wt/${key}` : `${remote}/${tgt}`];
    const r = ctx.git(args);
    if (r.status !== 0) fail(r.stderr.trim());
    console.log(`on wt/${key}${local || published ? ' (existing: a card back from review keeps its branch)' : ` from ${remote}/${tgt}`}`);
  },

  publish() {
    const key = rest[0] ?? fail('publish <KEY>');
    const r = ctx.git(['push', ctx.config.remote, `refs/heads/wt/${key}:refs/heads/wt/${key}`]);
    if (r.status !== 0) fail(r.stderr.trim());
    console.log(`published wt/${key}`);
  },

  integrate() {
    const [key, step] = rest;
    if (!key || !['merge', 'push', 'abort'].includes(step)) fail('integrate <KEY> merge|push|abort');
    const r = integration[step](ctx.git, { remote: ctx.config.remote, target: target(), key });
    if (r.code === integration.EXIT.conflict) {
      out(r, [
        `CONFLICT in ${r.files.length} file(s). Resolve them on the control branch, keeping every card's intent:`,
        ...r.files.map((f) => `  ${f}  ${r.cards[f]?.length ? `(cards: ${r.cards[f].join(', ')})` : ''}`),
        `Then: git add <files> && git commit --no-edit, re-run the card's checks, and \`integrate ${key} push\`.`,
      ].join('\n'));
    } else if (r.code === integration.EXIT.ok) {
      out(r, step === 'push' ? `integrated ${key} into ${target()} (${r.attempts} attempt(s)), now ${r.head}` : step === 'merge' ? `merged ${r.source} at ${r.sha}: re-run the card's checks on this tree, then \`integrate ${key} push\`` : 'aborted; the worktree is on the control branch tip');
    } else {
      out(r, r.error);
    }
    process.exit(r.code);
  },

  target() {
    const s = state();
    const { sprint } = opt;
    if (sprint !== undefined) {
      if (s && s.source !== 'template') fail(`The control branch was chosen by the person (${s.source}); a sprint does not move it.`, 5);
      const r = resolveTarget({ config: { ...ctx.config, target: undefined }, sprint, projectTag: projectTag(ctx) });
      if (r.error) fail(r.error, 2);
      const round = currentRound(ctx, r.branch);
      r.branch = round.branch;
      if (round.after?.length) console.error([`Commits made after the last round merged, to carry to ${r.branch}:`, ...round.after.map((l) => `  ${l}`)].join('\n'));
      ensureRemoteBranch(ctx, r.branch);
      writeAtomic(ctx.fs(`${ctx.stateDir}/control.json`), { ...(readJsonSafe(ctx.fs(`${ctx.stateDir}/control.json`)) ?? {}), target: r.branch, source: 'template' });
      return out(r, `control branch -> ${r.branch}; sessions started from now on use it`);
    }
    const tgt = target();
    if (!opt.check) return out({ target: tgt, source: s?.source }, tgt);
    const verdict = checkSpent(ctx, tgt);
    if (!verdict.spent) return out({ target: tgt, spent: false, unknown: verdict.unknown }, `ok ${tgt}${verdict.unknown ? ` (could not ask the forge: ${verdict.unknown})` : ''}`);
    const next = onSpent(s?.source ?? 'flag');
    out({ target: tgt, ...verdict, ...next }, [`SPENT ${tgt}: PR #${verdict.pr} merged at ${verdict.mergedAt}.`, ...(verdict.after.length ? ['Commits made after the merge, to carry to the next control branch:', ...verdict.after.map((l) => `  ${l}`)] : []), next.say].join('\n'));
    process.exit(5);
  },

  done: () => finish.done(worker),
  relaunch: () => finish.relaunch(worker),
  idle: () => finish.idle(worker),
};

const run = commands[command];
if (!run) fail(`Unknown command ${command ?? '(none)'}. See the header of ${SCRIPT}.`);
await run();
