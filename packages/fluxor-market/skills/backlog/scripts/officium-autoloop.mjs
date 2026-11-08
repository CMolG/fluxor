#!/usr/bin/env node
// The autoloop's beat to Officium (JAVA-1528), for its remote switch (`remoteSwitch.command`): it sends
// `POST /officium/v1/projects/<id>/autoloop/heartbeat {machine, state, slots, target}` with the account's
// heartbeat token and prints ONE JSON line, whatever happens:
//
//   {"command": "start" | "stop" | null, "reason"?: string, "gate"?: object}
//
// `reason` and `gate` are the tracker's explanation of a stop (for example an integration gate asking a person to
// merge the control branch), passed through when the server sends them; old servers answer only `command`.
//
// `command` is the order the board's Start/Stop Autoloop button queued, delivered once. A failure prints
// `null` (the loop keeps doing what it does) and exits 1 with the reason on stderr; the token never reaches
// argv or the output. State: AUTOLOOP_STATE (`running` or `idle`). Machine: AUTOLOOP_MACHINE, else
// OFFICIUM_MACHINE. Token, API and project id are read as officium-summons.mjs reads them.
import { fileURLToPath } from 'node:url';
import { readConfig, readToken, UUID } from './officium-summons.mjs';

const fail = (reason) => ({ ok: false, command: null, reason });

/** Runs once and returns the order to print. `fetchImpl` is injectable. */
export async function beat({ env = process.env, fetchImpl = fetch } = {}) {
  const machine = (env.AUTOLOOP_MACHINE || env.OFFICIUM_MACHINE || '').trim();
  if (!machine) return fail('no machine: set AUTOLOOP_MACHINE');
  const state = env.AUTOLOOP_STATE;
  if (state !== 'running' && state !== 'idle') return fail('AUTOLOOP_STATE must be running or idle');
  const token = readToken(env);
  if (!token) return fail('no heartbeat token');
  const projectId = readConfig(env)?.project?.id;
  if (!UUID.test(projectId ?? '')) return fail('no project id in the backlog config');
  const slots = Number.parseInt(env.AUTOLOOP_SLOTS ?? '', 10);
  const api = (env.OFFICIUM_API_URL || 'https://javadaba.com/api').replace(/\/+$/, '');
  let res;
  try {
    res = await fetchImpl(`${api}/officium/v1/projects/${projectId}/autoloop/heartbeat`, {
      method: 'POST',
      headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
      body: JSON.stringify({
        machine,
        state,
        ...(Number.isInteger(slots) ? { slots } : {}),
        ...(env.AUTOLOOP_TARGET ? { target: env.AUTOLOOP_TARGET } : {}),
      }),
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return fail('network error');
  }
  if (res.status === 401 || res.status === 403) return fail(`refused (${res.status}): check the heartbeat token`);
  if (res.status === 404) return fail('autoloop heartbeat not found (404): is the API this release?');
  if (!res.ok) return fail(`server answered ${res.status}`);
  let body;
  try {
    body = await res.json();
  } catch {
    return fail('the server answered no JSON');
  }
  const command = body?.command === 'start' || body?.command === 'stop' ? body.command : null;
  const reason = typeof body?.reason === 'string' && body.reason.trim() ? body.reason.trim().slice(0, 500) : null;
  const gate = body?.gate && typeof body.gate === 'object' && !Array.isArray(body.gate) ? body.gate : null;
  return { ok: true, command, ...(reason ? { reason } : {}), ...(gate ? { gate } : {}) };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { ok, command, reason, gate } = await beat();
  console.log(JSON.stringify(ok ? { command, ...(reason ? { reason } : {}), ...(gate ? { gate } : {}) } : { command }));
  if (!ok) {
    console.error(reason);
    process.exitCode = 1;
  }
}
