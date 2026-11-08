#!/usr/bin/env node
// Summons the person to what waits on them in Officium (JAVA-1145), for the autoloop's liaison
// (`liaison.command`). It sends `POST /officium/v1/projects/<id>/summons {machine}` with the
// account's heartbeat token and prints ONE JSON line, whatever happens:
//
//   {"pending": <integer>, "open": <http(s) URL or null>, "summary": "<text>"}
//
// `open` is set only when no open tab got the summons live: the loop's machine then opens it. The
// server owns every no-spam rule, so this is safe to run every minute. It prints fixed words and
// validated fields, never text the server sent, and the token never reaches argv or the output.
//
// Machine: --machine, else AUTOLOOP_MACHINE, else OFFICIUM_MACHINE. Token: OFFICIUM_HEARTBEAT_TOKEN,
// else the file OFFICIUM_HEARTBEAT_TOKEN_FILE (default ~/.config/officium/heartbeat-token). API:
// OFFICIUM_API_URL, else https://javadaba.com/api. Project id and boardUrl: the backlog config,
// `.harness/config/backlog.json` (or OFFICIUM_BACKLOG_CONFIG).
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The first line of the token file, or null. */
export const readToken = (env) => {
  const direct = (env.OFFICIUM_HEARTBEAT_TOKEN ?? '').replace(/\s/g, '');
  if (direct) return direct;
  try {
    const file = env.OFFICIUM_HEARTBEAT_TOKEN_FILE || join(homedir(), '.config', 'officium', 'heartbeat-token');
    return readFileSync(file, 'utf8').split(/\r?\n/)[0].replace(/\s/g, '') || null;
  } catch {
    return null;
  }
};

export const readConfig = (env) => {
  const here = dirname(fileURLToPath(import.meta.url));
  try {
    return JSON.parse(readFileSync(env.OFFICIUM_BACKLOG_CONFIG || join(here, '..', '..', '..', 'config', 'backlog.json'), 'utf8'));
  } catch {
    return null;
  }
};

/** The browser URL: the board's origin plus the path the server gave, http(s) only. */
export function browserUrl(boardUrl, openPath) {
  if (typeof openPath !== 'string' || !openPath.startsWith('/')) return null;
  try {
    const board = new URL(boardUrl);
    if (board.protocol !== 'http:' && board.protocol !== 'https:') return null;
    return new URL(openPath, board.origin).href;
  } catch {
    return null;
  }
}

const line = (pending, open, summary) => ({ pending, open, summary });

/** Runs once and returns the line to print. `fetchImpl` is injectable. */
export async function summon({ env = process.env, argv = [], fetchImpl = fetch } = {}) {
  const at = argv.indexOf('--machine');
  const machine = (at >= 0 ? argv[at + 1] : env.AUTOLOOP_MACHINE || env.OFFICIUM_MACHINE || '').trim();
  if (!machine) return { ok: false, ...line(0, null, 'no machine: pass --machine or set AUTOLOOP_MACHINE') };
  const token = readToken(env);
  if (!token) return { ok: false, ...line(0, null, 'no heartbeat token') };
  const config = readConfig(env);
  const projectId = config?.project?.id;
  if (!UUID.test(projectId ?? '')) return { ok: false, ...line(0, null, 'no project id in the backlog config') };
  const api = (env.OFFICIUM_API_URL || 'https://javadaba.com/api').replace(/\/+$/, '');
  let res;
  try {
    res = await fetchImpl(`${api}/officium/v1/projects/${projectId}/summons`, {
      method: 'POST',
      headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
      body: JSON.stringify({ machine }),
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return { ok: false, ...line(0, null, 'network error') };
  }
  if (res.status === 401 || res.status === 403) return { ok: false, ...line(0, null, `refused (${res.status}): check the heartbeat token`) };
  if (res.status === 404) return { ok: false, ...line(0, null, 'summons not found (404): is the API this release?') };
  if (!res.ok) return { ok: false, ...line(0, null, `server answered ${res.status}`) };
  let body;
  try {
    body = await res.json();
  } catch {
    return { ok: false, ...line(0, null, 'the server answered no JSON') };
  }
  const items = Array.isArray(body?.summons?.items) ? body.summons.items.length : 0;
  const state = ['closed', 'none', 'delivered', 'open', 'unchanged'].includes(body?.state) ? body.state : 'unknown';
  const open = state === 'open' ? browserUrl(config?.boardUrl ?? '', body?.openPath) : null;
  return { ok: true, ...line(items, open, `${state}: ${items} pending`) };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { ok, pending, open, summary } = await summon({ argv: process.argv.slice(2) });
  console.log(JSON.stringify(line(pending, open, summary)));
  process.exitCode = ok ? 0 : 1;
}
