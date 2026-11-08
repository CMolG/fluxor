// The liaison: with two or more slots, the supervisor itself (no model, no session) runs the
// project's `liaison.command` on a clock, on behalf of one slot, and opens the URL it asks for.
// Everything here is pure; the supervisor does the I/O.
import { withWslenv } from './context.mjs';

/** The slot the liaison speaks for: the lowest-numbered one that is not disabled. */
export function liaisonSlot(slots) {
  const live = slots.filter((s) => !s.disabled).map((s) => s.n);
  return live.length ? Math.min(...live) : null;
}

/** Whether the loop has a liaison at all: a command is configured and 2 or more slots run. */
export const enabled = (config, slots) => Boolean(config.liaison?.command) && slots.length >= 2;

/** True when the last run is older than `pollSeconds` (default 60), or there has been none. */
export function due(last, config, now) {
  if (!last?.at) return true;
  return now - last.at >= (config.liaison?.pollSeconds ?? 60) * 1000;
}

/**
 * The command's stdout: ONE JSON line `{pending, open, summary}`. `pending` is a non-negative
 * integer, `open` an http(s) URL or null, `summary` a short string. Anything else is garbage: null.
 */
export function parse(stdout) {
  const lines = String(stdout ?? '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length !== 1) return null;
  let v;
  try {
    v = JSON.parse(lines[0]);
  } catch {
    return null;
  }
  if (!v || typeof v !== 'object' || !Number.isInteger(v.pending) || v.pending < 0) return null;
  let open = null;
  if (v.open !== undefined && v.open !== null) {
    try {
      const u = new URL(String(v.open));
      if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
      open = u.href;
    } catch {
      return null;
    }
  }
  return { pending: v.pending, open, summary: typeof v.summary === 'string' ? v.summary.slice(0, 200) : '' };
}

/**
 * `[file, args]` that opens `url` in the person's default browser, never through a shell.
 * `WSL_DISTRO_NAME` set on Linux means WSL, where the Windows side opens it.
 */
export function openCommand(platform, env, url) {
  if (!/^https?:\/\//i.test(url)) throw new Error('only http(s) URLs are opened');
  if (platform === 'win32') return ['rundll32', ['url.dll,FileProtocolHandler', url]];
  if (platform === 'darwin') return ['open', [url]];
  if (env?.WSL_DISTRO_NAME) return ['explorer.exe', [url]];
  return ['xdg-open', [url]];
}

/**
 * `[file, args, options]` that runs the project's command line from the project root. Behind a
 * distro the root is a UNC path Windows cannot use as a cwd, so it goes through `wsl.exe` (a login
 * shell, as `setup` does) and `env` crosses by WSLENV; otherwise `sh -c` in the root.
 */
export function liaisonSpawn(ctx, command, env, processEnv) {
  const base = { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, timeout: 30_000 };
  if (ctx.distro) {
    return [
      'wsl.exe',
      ['-d', ctx.distro, '--cd', ctx.root, '--', 'bash', '-lc', command],
      { ...base, env: withWslenv({ ...processEnv, ...env }, Object.keys(env)) },
    ];
  }
  return ['sh', ['-c', command], { ...base, cwd: ctx.fs(ctx.root), env: { ...processEnv, ...env } }];
}
