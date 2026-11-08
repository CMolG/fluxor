#!/usr/bin/env node
// The model and effort the autoloop starts a slot's next session on (JAVA-1587), for its `pickRun.command`: it asks
// `GET /officium/v1/projects/<id>/autoloop/next-run` with the account's heartbeat token and prints ONE JSON line,
// whatever happens:
//
//   {"model": "<model>" | null, "effort": "<effort>" | null}
//
// and `"toolTier": "<read|comment|write>"` beside them when the card's roles name one: the widest of its eligible
// roles' tiers, which holds the session to the tools its roles may use. `"key"` names the card the run is for: the
// supervisor tells the session, which takes that card instead of ranking the backlog again (JAVA-1808).
//
// With AUTOLOOP_MACHINE, the server first ends the sessions that machine still shows live and answers the slot's own
// unfinished unit before the pick (JAVA-2004).
//
// The run the card `cards.next` would hand out asks for. Starting the session on it spares the session that would
// only read the card and relaunch itself onto another model (28% of a loop's spend, measured 2026-10-18). A failure
// prints nulls (the slot keeps the run it had) and exits 1 with the reason on stderr; the token never reaches argv or
// the output. Token, API and project id are read as officium-summons.mjs reads them.
import { fileURLToPath } from 'node:url';
import { readConfig, readToken, UUID } from './officium-summons.mjs';

const fail = (reason) => ({ ok: false, model: null, effort: null, reason });
// The tool tiers a role may declare, narrowest first: the autoloop's list, kept here because a skill ships alone.
const TOOL_TIERS = ['read', 'comment', 'write'];

/**
 * Runs once and returns the run to print. `fetchImpl` is injectable. `AUTOLOOP_CARD` asks for the run of that card (a
 * slot that holds its claim); `AUTOLOOP_EXCLUDE` (comma-separated keys) leaves out the cards other slots hold;
 * `AUTOLOOP_PHASES` (the loop's `--phases`) answers only a card of those phases.
 */
export async function nextRun({ env = process.env, fetchImpl = fetch } = {}) {
  const token = readToken(env);
  if (!token) return fail("no heartbeat token on this machine (run the backlog's heartbeat.setup once)");
  const projectId = readConfig(env)?.project?.id;
  if (!UUID.test(projectId ?? '')) return fail('no project id in the backlog config');
  const api = (env.OFFICIUM_API_URL || 'https://javadaba.com/api').replace(/\/+$/, '');
  const query = new URLSearchParams();
  if (env.AUTOLOOP_CARD?.trim()) query.set('card', env.AUTOLOOP_CARD.trim());
  const exclude = (env.AUTOLOOP_EXCLUDE ?? '').split(',').map((k) => k.trim()).filter(Boolean);
  if (exclude.length) query.set('exclude', exclude.join(','));
  // card://JAVA-1890: a loop run with --phases starts only on a card of those phases.
  if (env.AUTOLOOP_PHASES?.trim()) query.set('phases', env.AUTOLOOP_PHASES.trim());
  // card://JAVA-2004: the slot's machine, so the server ends what it left live (stale: the slot has no session while
  // the supervisor asks) and answers its own unfinished unit before the pick, as the worker resumes it.
  if (env.AUTOLOOP_MACHINE?.trim()) query.set('machine', env.AUTOLOOP_MACHINE.trim());
  const search = query.size ? `?${query}` : '';
  let res;
  try {
    res = await fetchImpl(`${api}/officium/v1/projects/${projectId}/autoloop/next-run${search}`, {
      headers: { authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return fail('network error');
  }
  if (res.status === 401 || res.status === 403) return fail(`refused (${res.status}): check the heartbeat token`);
  if (res.status === 404) return fail('next-run not found (404): is the API this release?');
  if (!res.ok) return fail(`server answered ${res.status}`);
  let body;
  try {
    body = await res.json();
  } catch {
    return fail('the server answered no JSON');
  }
  const text = (v) => (typeof v === 'string' && v.trim() ? v.trim() : null);
  const toolTier = text(body?.toolTier);
  // The widest tier of the card's eligible roles (JAVA-1445). A tier this picker does not know is a failure, so the
  // slot keeps the run it had instead of starting a session on a tier it cannot read.
  if (toolTier && !TOOL_TIERS.includes(toolTier)) return fail(`the server named an unknown tool tier: ${toolTier}`);
  const key = text(body?.key);
  return {
    ok: true,
    model: text(body?.model),
    effort: text(body?.effort),
    ...(toolTier ? { toolTier } : {}),
    ...(key ? { key } : {}),
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { ok, model, effort, toolTier, key, reason } = await nextRun();
  console.log(JSON.stringify({ model, effort, ...(toolTier ? { toolTier } : {}), ...(key ? { key } : {}) }));
  if (!ok) {
    console.error(reason);
    process.exitCode = 1;
  }
}
