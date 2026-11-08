// How a worker ends its session, by one of three markers the supervisor watches for. `done` ends
// a card: it frees the slot's claims and writes the done marker, and the next session starts clean.
// With the config's `doneCheck` (2026-11-03), `done` is refused while the card's unit still has work for this
// session (the tracker would hand it straight back): on 2026-11-03 two sweeps in a row ended after one commit, and
// each next session paid a start to go on. A forced exit names its reason from a closed list.
// `relaunch` keeps the card: it only asks for the same slot to restart on another model and effort,
// and the new session resumes the card through `RESUME`. `idle` says there was no card to take:
// the slot is parked, and a new session looks again once the retry is due.
import { mkdirSync, writeFileSync } from 'node:fs';
import * as claims from './claims.mjs';
import { EFFORTS } from './pick-run.mjs';
import { writeAtomic } from './supervisor.mjs';
import { TIERS } from './tiers.mjs';


/**
 * The exits a `done` may force past the gate: Claude Code killed the run it waited on twice (`run-killed`), the machine
 * cannot run what the unit needs and its wall is raised (`environment`), or the context is spent past compaction
 * (`context`). A closed list, so a habit cannot argue its way out (ADR 0031's send-back reasons are the model).
 */
export const FORCED = ['run-killed', 'environment', 'context'];

/** `h` is what the CLI already has: {ctx, fail, slotId, claimsDir, ttlMs, state, opt, ask}. */
export function done(h) {
  const { ctx, fail, opt } = h;
  const forced = opt.forced;
  if (forced !== undefined && !FORCED.includes(forced)) fail(`--forced takes one of: ${FORCED.join(', ')}.`, 2);
  const branch = ctx.git(['branch', '--show-current']).stdout.trim();
  if (ctx.git(['status', '--porcelain', '--untracked-files=no']).stdout.trim()) fail('Uncommitted changes: commit (and publish) or discard them before `done`.');
  if (ctx.git(['rev-parse', '-q', '--verify', 'MERGE_HEAD']).status === 0) fail('A merge is in progress: push it or `integrate <KEY> abort` first.');
  const { remote } = ctx.config;
  if (branch.startsWith('wt/')) {
    ctx.git(['fetch', '-q', remote, branch]);
    const unpublished = ctx.git(['rev-list', '--count', `${remote}/${branch}..HEAD`]);
    if (unpublished.status !== 0 || unpublished.stdout.trim() !== '0') fail(`${branch} has commits its reviewer cannot see: \`publish ${branch.slice(3)}\` first.`);
  }
  const slot = h.slotId();
  const held = claims.list(h.claimsDir(), { ttlMs: h.ttlMs() }).filter((c) => c.slot === slot).map((c) => c.key);
  const verdict = gate(h, held, forced);
  if (verdict.refused) fail(verdict.refused, 7);
  if (verdict.warning) console.error(verdict.warning);
  for (const key of held) claims.release(h.claimsDir(), key, { slot });
  // Park the worktree on the control branch's tip, so the next session in this slot finds
  // nothing to resume.
  const tgt = process.env.AUTOLOOP_TARGET || h.state()?.target;
  if (tgt) {
    ctx.git(['fetch', '-q', remote, tgt]);
    ctx.git(['switch', '--detach', `${remote}/${tgt}`]);
  }
  const marker = ctx.fs(`${ctx.root}/${ctx.config.doneMarker}`);
  mkdirSync(ctx.fs(`${ctx.root}/${ctx.config.doneMarker.split('/').slice(0, -1).join('/')}`), { recursive: true });
  writeFileSync(marker, `${new Date().toISOString()}${forced ? ` forced:${forced}` : ''}\n`);
  console.log(`done${forced ? ` (forced: ${forced})` : ''}: the supervisor recycles this session once the turn ends (${ctx.config.doneMarker}).`);
}

/**
 * The done gate: the config's `doneCheck` command, asked once with the held keys (`AUTOLOOP_CARD`), prints ONE JSON
 * line `{"open", "key", "reason"}`. `open: true` refuses the `done`, unless it is forced. A check that cannot answer
 * never traps a session: the `done` goes through with a warning.
 */
export function gate(h, held, forced) {
  const command = h.ctx.config.doneCheck?.command;
  if (!command || !held.length || forced) return {};
  const answer = h.ask(command, { AUTOLOOP_CARD: held.join(',') });
  if (!answer || typeof answer.open !== 'boolean') {
    return { warning: 'done: the doneCheck could not answer, so this `done` goes through unchecked.' };
  }
  if (!answer.open) return {};
  return {
    refused: `${answer.key ?? held[0]} still has work for this session: ${answer.reason ?? 'the tracker would hand it '
      + 'straight back'}. Keep working it; \`done\` ends a session once its unit has left its phase (a sweep, once it `
      + `names no checkpoint to build or only a person's answer is left). A forced exit names its reason: \`done `
      + `--forced ${FORCED.join('|')}\`.`,
  };
}

/**
 * Writes the idle marker: this slot found no card to claim in the loop's phases. Refused while
 * the slot has anything to resume, which `done` finishes and an idle slot would leave stranded.
 */
export function idle(h) {
  const { ctx, fail, opt } = h;
  const slot = h.slotId();
  const mine = claims.list(h.claimsDir(), { ttlMs: h.ttlMs() }).filter((c) => c.slot === slot).map((c) => c.key);
  if (mine.length) fail(`This slot holds ${mine.join(', ')}: finish it and \`done\`, never idle on a card.`);
  const branch = ctx.git(['branch', '--show-current']).stdout.trim();
  if (branch.startsWith('wt/')) fail(`This worktree is on ${branch}: a card branch is finished and \`done\`, never left idle.`);
  if (ctx.git(['status', '--porcelain', '--untracked-files=no']).stdout.trim()) fail('Uncommitted changes: a slot with work in it is not idle.');
  if (ctx.git(['rev-parse', '-q', '--verify', 'MERGE_HEAD']).status === 0) fail('A merge is in progress: push it or `integrate <KEY> abort` first.');
  writeAtomic(ctx.fs(`${ctx.root}/${ctx.config.idleMarker}`), { reason: opt.reason ?? null, at: new Date().toISOString() });
  console.log(`idle: the supervisor parks this slot for ${ctx.config.idleRetryMinutes} min once the turn ends, then a new session looks again; end it now.`);
}

/** Writes the relaunch marker. Claims, branch and the done marker stay exactly as they are. */
export function relaunch(h) {
  const { ctx, fail, opt } = h;
  const model = opt.model?.trim();
  if (!model) fail('relaunch --model <model> --effort <effort>: the model is missing.', 2);
  if (!EFFORTS.includes(opt.effort)) fail(`--effort must be one of ${EFFORTS.join(', ')} (got ${opt.effort ?? 'nothing'}).`, 2);
  if (opt.tier !== undefined && !TIERS.includes(opt.tier)) fail(`--tier must be one of ${TIERS.join(', ')} (got ${opt.tier}).`, 2);
  // A session held to a tier cannot widen it: a relaunch from it names a tier no wider than its own. Only the
  // supervisor widens one, from the card's roles, so the guard and this refusal close the same way out.
  const heldTier = process.env.AUTOLOOP_TOOL_TIER;
  if (heldTier && (opt.tier === undefined || TIERS.indexOf(opt.tier) > TIERS.indexOf(heldTier))) {
    fail(`this session holds the tool tier ${heldTier}: relaunch --tier must name ${heldTier} or a narrower tier (got ${opt.tier ?? 'none'}).`, 2);
  }
  const tier = opt.tier === undefined ? {} : { toolTier: opt.tier };
  writeAtomic(ctx.fs(`${ctx.root}/${ctx.config.relaunchMarker}`), { model, effort: opt.effort, ...tier, at: new Date().toISOString() });
  const held = opt.tier === undefined ? '' : ` with tier ${opt.tier}`;
  console.log(`relaunch: the supervisor restarts this slot on ${model} (effort ${opt.effort})${held} once the turn ends; end it now. The new session resumes this card.`);
}
