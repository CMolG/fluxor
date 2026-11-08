// What the supervisor decides about one slot, and how the slot changes once it has done it. Both
// are pure: everything they need is in their arguments, so a test needs no session and no clock.

/**
 * What to do with one slot now.
 *   slot  {id, launchedAt, seen, disabled, setup, run, parkedUntil}
 *   obs   {session (from `claude agents`, or null), marker, relaunch ({model, effort} or null),
 *          idle, activity (ms, or null), stop}
 */
export function decide(slot, obs, cfg, now) {
  if (obs.stop) return slot.id ? 'stop' : 'none';
  if (slot.disabled) return 'none';
  if (slot.setup === 'pending') return 'setup';
  if (slot.setup === 'running') return 'none';
  // A parked slot found nothing to claim: a new session before the retry would find nothing too.
  if (!slot.id) return slot.parkedUntil && now < slot.parkedUntil ? 'none' : 'launch';
  const age = now - slot.launchedAt;
  const starting = age < cfg.startTimeoutSeconds * 1000;
  if (!obs.session) {
    if (!slot.seen) return starting ? 'none' : 'failed-start';
    // Gone on its own. Right after starting, that is a start that failed (an auth error, a bad
    // flag); later, it is a session that ended: start the next one, which resumes its card.
    return starting ? 'failed-start' : 'forget';
  }
  // Every marker waits for an idle session: one still writing its last message is not stopped. A
  // finished card wins over the others, since its slot is about to start clean anyway; nothing
  // left to claim wins over a model to claim it with.
  if (obs.marker && obs.session.status === 'idle') return 'recycle';
  if (obs.idle && obs.session.status === 'idle') return 'park';
  if (obs.relaunch && obs.session.status === 'idle') return 'relaunch';
  // The marker alone is not "finished": a Stop hook may send the session back to work, and then
  // it is busy again, and that writes to the transcript. A finished session that stays busy with
  // a silent transcript is one holding something armed (a Monitor on `tail -F`): `done` already
  // released its claims and parked the worktree, so nothing it does later can land on the card.
  if (obs.marker && now - (obs.activity ?? slot.launchedAt) >= cfg.doneGraceSeconds * 1000) return 'recycle';
  // Silence is: no transcript write for idleMinutes means nobody is working.
  if (now - (obs.activity ?? slot.launchedAt) >= cfg.idleMinutes * 60_000) return 'recycle-silent';
  return 'none';
}

/** The slot after `action` ran, given the result of running it. Pure. */
export function transition(slot, action, result, cfg, now) {
  switch (action) {
    case 'launch':
      return result.id
        ? { ...slot, id: result.id, launchedAt: now, seen: false, parkedUntil: null, keepRun: false }
        : failedStart(slot, cfg, result.error ?? 'claude --bg printed no session id');
    case 'park':
      // No card was finished, and none is held: the next session starts once the retry is due.
      return { ...slot, id: null, failedStarts: 0, parkedUntil: now + cfg.idleRetryMinutes * 60_000 };
    case 'failed-start':
      return failedStart({ ...slot, id: null }, cfg, 'the session ended before it started working');
    case 'forget':
      return { ...slot, id: null, failedStarts: 0 };
    case 'recycle':
      return { ...slot, id: null, failedStarts: 0, cards: (slot.cards ?? 0) + 1 };
    case 'relaunch':
      // Same card, other model: no card was finished, and `run` stays for every later session.
      return { ...slot, id: null, failedStarts: 0, keepRun: true,
        run: { model: result.run.model, effort: result.run.effort, ...(result.run.toolTier ? { toolTier: result.run.toolTier } : {}) } };
    case 'recycle-silent':
    case 'stop':
      return { ...slot, id: null };
    case 'setup':
      return { ...slot, setup: result.ok === false ? 'failed' : 'running', ...(result.ok === false ? { disabled: true, reason: result.error } : {}) };
    default:
      return slot;
  }
}

function failedStart(slot, cfg, why) {
  const failedStarts = (slot.failedStarts ?? 0) + 1;
  const disabled = failedStarts >= cfg.maxFailedStarts;
  return { ...slot, id: null, failedStarts, disabled, reason: disabled ? `${failedStarts} failed starts in a row: ${why}` : why };
}
