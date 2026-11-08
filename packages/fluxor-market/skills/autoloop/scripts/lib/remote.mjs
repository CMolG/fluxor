// The remote switch: the supervisor itself (no model, no session) runs the project's `remoteSwitch.command` on a clock,
// telling the tracker whether the loop runs or stands by, and applies the order the command prints back: `start`
// leaves standby, `stop` stops every session and stands by, as `/autoloop stop` does without exiting. The skill
// stays tracker-agnostic: the command is the project's (the backlog skill's `officium-autoloop.mjs` on Officium).
// Everything here is pure; the supervisor does the I/O.

/** Whether the loop has a remote switch: a command is configured. Any number of slots. */
export const remoteEnabled = (config) => Boolean(config.remoteSwitch?.command);

/** True when the last beat is older than `pollSeconds` (default 20), or there has been none. */
export function dueRemote(last, config, now) {
  if (!last?.at) return true;
  return now - last.at >= (config.remoteSwitch?.pollSeconds ?? 20) * 1000;
}

/** A tracker's stop reason, as the log and `status` show it: trimmed, at most this many characters. */
const MAX_REASON = 500;

/** The command's stdout: ONE JSON line `{"command": "start" | "stop" | null, "reason"?: string, "gate"?: object}`. Anything else is garbage: null. */
export function parseOrder(stdout) {
  const lines = String(stdout ?? '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length !== 1) return null;
  let v;
  try {
    v = JSON.parse(lines[0]);
  } catch {
    return null;
  }
  if (!v || typeof v !== 'object' || !('command' in v)) return null;
  if (v.command !== null && v.command !== 'start' && v.command !== 'stop') return null;
  const reason = typeof v.reason === 'string' && v.reason.trim() ? v.reason.trim().slice(0, MAX_REASON) : null;
  const gate = v.gate && typeof v.gate === 'object' && !Array.isArray(v.gate) ? v.gate : null;
  return { command: v.command, ...(reason ? { reason } : {}), ...(gate ? { gate } : {}) };
}

/** Whether the loop stands by after `command`: start leaves standby, stop enters it, nothing keeps it. */
export function standbyAfter(standby, command) {
  if (command === 'start') return false;
  if (command === 'stop') return true;
  return standby;
}

/** The variables the command runs with: the loop's state, its machine, its slots and its control branch. */
export function remoteEnv(state, standby, slots) {
  return {
    AUTOLOOP_STATE: standby ? 'idle' : 'running',
    AUTOLOOP_MACHINE: state.machine ?? '',
    AUTOLOOP_SLOTS: String(slots.length),
    AUTOLOOP_TARGET: state.target ?? '',
  };
}
