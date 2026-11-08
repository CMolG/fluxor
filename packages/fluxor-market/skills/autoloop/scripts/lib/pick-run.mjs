// The run a slot's next session starts on: the supervisor itself (no model, no session) runs the
// project's `pickRun.command` before each launch, and starts the session on the model and effort it prints. The
// skill stays tracker-agnostic: the command is the project's (the backlog skill's `officium-next-run.mjs` on
// Officium). Pure; the supervisor does the I/O.
import { TIERS } from './tiers.mjs';

/** The efforts a session runs with: `relaunch` and `pickRun` accept these and no others. */
export const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max'];

/** A tracker's card key, as the session is told it: `PROJ-123`. */
const CARD_KEY = /^[A-Za-z][A-Za-z0-9]*-\d+$/;

/**
 * The command's stdout: ONE JSON line `{"model", "effort"}`, and optionally `"toolTier"` and `"key"`, the card the run
 * is for (the session is told it, so it takes that card instead of ranking the backlog again). Anything
 * else, a null field, or a tier that is not one of the tiers, is no run: null. A key that is no card key is left out.
 */
export function parseRun(stdout) {
  const lines = String(stdout ?? '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length !== 1) return null;
  let v;
  try {
    v = JSON.parse(lines[0]);
  } catch {
    return null;
  }
  const model = typeof v?.model === 'string' ? v.model.trim() : '';
  if (!model || !EFFORTS.includes(v.effort)) return null;
  if (v.toolTier !== undefined && !TIERS.includes(v.toolTier)) return null;
  const card = typeof v.key === 'string' && CARD_KEY.test(v.key.trim()) ? { card: v.key.trim() } : {};
  return { model, effort: v.effort, ...(v.toolTier === undefined ? {} : { toolTier: v.toolTier }), ...card };
}
