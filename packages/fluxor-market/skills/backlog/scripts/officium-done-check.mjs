#!/usr/bin/env node
// The autoloop's done gate on Officium (card://JAVA-2004), for its `doneCheck.command`: whether the unit of each card
// a slot holds (`AUTOLOOP_CARD`, comma-separated) still has work a session can do now, which the tracker would hand
// straight back to the next session. It asks `GET /officium/v1/projects/<id>/autoloop/unit?card=<KEY>` with the
// account's heartbeat token and prints ONE JSON line, whatever happens:
//
//   {"open": true | false | null, "key": "<KEY>", "reason": "<why>"}
//
// The first held card whose unit is open answers; none open answers `open: false`. A failure prints `open: null` and
// exits 1 with the reason on stderr: the autoloop then lets `done` through, since a gate that cannot answer must never
// trap a session. The token never reaches argv or the output; token, API and project id are read as
// officium-summons.mjs reads them.
import { fileURLToPath } from 'node:url';
import { readConfig, readToken, UUID } from './officium-summons.mjs';

const fail = (reason) => ({ ok: false, open: null, reason });

/** Runs once and returns the verdict to print. `fetchImpl` is injectable. */
export async function doneCheck({ env = process.env, fetchImpl = fetch } = {}) {
  const keys = (env.AUTOLOOP_CARD ?? '').split(',').map((k) => k.trim()).filter(Boolean);
  if (!keys.length) return { ok: true, open: false, reason: 'this slot holds no card' };
  const token = readToken(env);
  if (!token) return fail("no heartbeat token on this machine (run the backlog's heartbeat.setup once)");
  const projectId = readConfig(env)?.project?.id;
  if (!UUID.test(projectId ?? '')) return fail('no project id in the backlog config');
  const api = (env.OFFICIUM_API_URL || 'https://javadaba.com/api').replace(/\/+$/, '');
  for (const key of keys) {
    let res;
    try {
      res = await fetchImpl(`${api}/officium/v1/projects/${projectId}/autoloop/unit?card=${encodeURIComponent(key)}`, {
        headers: { authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(20_000),
      });
    } catch {
      return fail('network error');
    }
    if (res.status === 401 || res.status === 403) return fail(`refused (${res.status}): check the heartbeat token`);
    if (res.status === 404) return fail('the unit check was not found (404): is the API this release?');
    if (!res.ok) return fail(`server answered ${res.status}`);
    let body;
    try {
      body = await res.json();
    } catch {
      return fail('the server answered no JSON');
    }
    if (typeof body?.open !== 'boolean') return fail('the server answered no verdict');
    if (body.open) return { ok: true, open: true, key: body.key ?? key, reason: body.reason ?? null };
  }
  return { ok: true, open: false, key: keys[0], reason: 'no held unit has work left for this session' };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { ok, open, key, reason } = await doneCheck();
  console.log(JSON.stringify({ open, ...(key ? { key } : {}), ...(reason ? { reason } : {}) }));
  if (!ok) {
    console.error(reason);
    process.exitCode = 1;
  }
}
