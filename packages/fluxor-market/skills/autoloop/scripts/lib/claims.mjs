// Per-card claims: first wins. A claim is a directory, `<state>/claims/<KEY>`, because `mkdir` is
// atomic on every filesystem a worktree lives on: of N sessions racing for one card, exactly one
// creates it. The tracker cannot do this yet (it accepts a second session on the same card), so
// the claim is local to the machine; a server-side claim is the tracker's own card.
//
// A claim belongs to a SLOT, not to a session: the session that replaces a dead one in the same
// slot resumes its card with the claim still held. The supervisor refreshes its slots' claims on
// every poll, so a claim whose `time` is older than the TTL has no live supervisor behind it and
// may be taken over.
//
// Every write acts on a read made earlier, and a directory NAME is all two claims share, so nothing
// here rewrites or moves another session's claim by name: the beat is a file of its own slot
// (`beat-<slot>`), and only the holder of a key's takeover lock moves a stale claim aside.
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const KEY = /^[A-Za-z][A-Za-z0-9]*-\d+$/;
const DEAD_LOCK_MS = 60_000; // a takeover is a few sync calls: a lock this old has a dead holder

/** The claim, its `time` the later of its own and its slot's last beat. */
function info(dir, key) {
  let claim;
  try {
    claim = JSON.parse(readFileSync(join(dir, key, 'claim.json'), 'utf8'));
  } catch {
    return null; // just created by its winner, not written yet: fresh by definition
  }
  try {
    const beat = Number(readFileSync(join(dir, key, `beat-${claim.slot}`), 'utf8'));
    if (beat > claim.time) return { ...claim, time: beat };
  } catch {
    /* not beaten yet */
  }
  return claim;
}

function write(dir, key, claim) {
  const tmp = join(dir, key, `claim.json.${process.pid}`);
  writeFileSync(tmp, JSON.stringify(claim));
  renameSync(tmp, join(dir, key, 'claim.json'));
}

export const isStale = (claim, now, ttlMs) => claim !== null && now - claim.time > ttlMs;

/**
 * Claims the first free card of `keys`, in the order given (the caller's priority order).
 * Returns {key, claim} for the one won (or already held by this slot), or {key: null, taken}.
 */
export function claimFirst(dir, keys, { slot, session = '', now = Date.now(), ttlMs = 15 * 60_000 }) {
  mkdirSync(dir, { recursive: true });
  const taken = [];
  for (const key of keys) {
    if (!KEY.test(key)) throw new Error(`not a card key: ${key}`);
    const mine = { key, slot: String(slot), session, time: now };
    let held = null;
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        mkdirSync(join(dir, key));
        write(dir, key, mine);
        return { key, claim: mine };
      } catch (e) {
        if (e.code !== 'EEXIST') throw e;
      }
      held = info(dir, key);
      if (held && held.slot === String(slot)) {
        write(dir, key, { ...held, session: session || held.session, time: now });
        return { key, claim: held };
      }
      if (!isStale(held, now, ttlMs)) break;
      // Stale: whoever moves it aside, every racer retries the mkdir, and the first wins as usual.
      takeOver(dir, key, now, ttlMs);
    }
    taken.push(held ?? { key, slot: '?' });
  }
  return { key: null, taken };
}

/**
 * Moves a stale claim aside, if this racer holds the key's takeover lock and the claim is STILL
 * stale under it: a racer that read the stale claim earlier must not move the fresh claim that
 * replaced it, and a rename moves whatever holds the name now.
 */
function takeOver(dir, key, now, ttlMs) {
  const lock = join(dir, `.takeover-${key}`);
  try {
    mkdirSync(lock);
  } catch (e) {
    if (e.code !== 'EEXIST') throw e;
    try {
      if (Date.now() - statSync(lock).mtimeMs > DEAD_LOCK_MS) rmSync(lock, { recursive: true, force: true });
    } catch {
      /* released meanwhile */
    }
    return; // another racer is taking it over
  }
  try {
    if (!isStale(info(dir, key), now, ttlMs)) return;
    const aside = join(dir, `.stale-${key}-${process.pid}-${now}`);
    renameSync(join(dir, key), aside);
    rmSync(aside, { recursive: true, force: true });
  } catch (e) {
    if (e.code !== 'ENOENT') throw e; // released meanwhile: nothing to move
  } finally {
    rmSync(lock, { recursive: true, force: true });
  }
}

/** Frees a card. Only its own slot frees it unless `any` (a person clearing a dead claim). */
export function release(dir, key, { slot, any = false } = {}) {
  if (!KEY.test(key)) throw new Error(`not a card key: ${key}`); // the key becomes a path that is removed recursively
  if (!existsSync(join(dir, key))) return false;
  const held = info(dir, key);
  if (!any && held && held.slot !== String(slot)) throw new Error(`${key} is held by slot ${held.slot}, not ${slot}`);
  rmSync(join(dir, key), { recursive: true, force: true });
  return true;
}

export function list(dir, { now = Date.now(), ttlMs = 15 * 60_000 } = {}) {
  let names;
  try {
    names = readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }
  return names
    .filter((e) => e.isDirectory() && KEY.test(e.name))
    .map((e) => {
      const c = info(dir, e.name) ?? { key: e.name, slot: '?', time: now };
      return { ...c, stale: isStale(c, now, ttlMs) };
    });
}

/**
 * The supervisor's beat: every claim of a live slot gets a fresh time, in its slot's own beat file.
 * If the claim was released and another slot took the card after this listing, the beat lands in
 * that slot's directory under the wrong slot's name, and nobody reads it.
 */
export function refresh(dir, slots, now = Date.now()) {
  const live = new Set(slots.map(String));
  for (const c of list(dir, { now })) {
    if (!live.has(c.slot)) continue;
    const beat = join(dir, c.key, `beat-${c.slot}`);
    try {
      writeFileSync(`${beat}.${process.pid}`, String(now));
      renameSync(`${beat}.${process.pid}`, beat);
    } catch (e) {
      // Released between the listing and the write: a worker's `done` removes the directory, and
      // on 2026-10-01 that race killed the supervisor. A released claim needs no beat.
      if (e.code !== 'ENOENT') throw e;
    }
  }
}
