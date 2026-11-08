// Two sessions racing for the same card: exactly one takes it, the other works a different one.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs, { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { claimFirst, list, refresh, release } from '../scripts/lib/claims.mjs';

const LIB = new URL('../scripts/lib/claims.mjs', import.meta.url).href;
const dir = () => join(mkdtempSync(join(tmpdir(), 'claims-')), 'claims');

/** N processes claim from the same priority list at the same instant. */
function race(claims, slots, keys) {
  const go = Date.now() + 400; // everyone loaded, then everyone at once
  const script = `
    import { claimFirst } from ${JSON.stringify(LIB)};
    while (Date.now() < ${go}) {}
    const r = claimFirst(${JSON.stringify(claims)}, ${JSON.stringify(keys)}, { slot: process.argv[1] });
    console.log(JSON.stringify(r.key));`;
  return Promise.all(
    slots.map(
      (slot) =>
        new Promise((resolve, reject) => {
          const p = spawn(process.execPath, ['--input-type=module', '-e', script, String(slot)]);
          let out = '';
          p.stdout.on('data', (d) => (out += d));
          p.on('error', reject);
          p.on('close', () => resolve(JSON.parse(out.trim())));
        }),
    ),
  );
}

/**
 * Runs `fn`, and once, right after its first read of a `claim.json`, runs `between`: what another
 * session does in the moment between a read and the write or rename that acts on it.
 */
function afterFirstClaimRead(between, fn) {
  const original = fs.readFileSync;
  const restore = () => {
    fs.readFileSync = original;
    syncBuiltinESMExports();
  };
  fs.readFileSync = function (path, ...rest) {
    const out = original.call(this, path, ...rest);
    if (String(path).endsWith('claim.json')) {
      restore();
      between();
    }
    return out;
  };
  syncBuiltinESMExports();
  try {
    return fn();
  } finally {
    restore();
  }
}

describe('claims', () => {
  test('of eight sessions racing for one card, exactly one gets it', async () => {
    const won = await race(dir(), [1, 2, 3, 4, 5, 6, 7, 8], ['JAVA-1']);
    assert.equal(won.filter((k) => k === 'JAVA-1').length, 1);
    assert.equal(won.filter((k) => k === null).length, 7);
  });

  test('two sessions with the same priority list end on different cards', async () => {
    const won = await race(dir(), [1, 2], ['JAVA-10', 'JAVA-11', 'JAVA-12']);
    assert.deepEqual([...won].sort(), ['JAVA-10', 'JAVA-11']);
  });

  test('the slot that holds a card gets it again: a replacement session resumes it', () => {
    const d = dir();
    assert.equal(claimFirst(d, ['JAVA-2'], { slot: 1 }).key, 'JAVA-2');
    assert.equal(claimFirst(d, ['JAVA-2'], { slot: 2 }).key, null);
    assert.equal(claimFirst(d, ['JAVA-2'], { slot: 1 }).key, 'JAVA-2');
  });

  test('a stale claim, with no supervisor refreshing it, is taken over', () => {
    const d = dir();
    claimFirst(d, ['JAVA-3'], { slot: 1, now: 1_000 });
    assert.equal(claimFirst(d, ['JAVA-3'], { slot: 2, now: 1_000 + 60_000, ttlMs: 120_000 }).key, null);
    const r = claimFirst(d, ['JAVA-3'], { slot: 2, now: 1_000 + 180_000, ttlMs: 120_000 });
    assert.equal(r.key, 'JAVA-3');
    assert.equal(list(d)[0].slot, '2');
  });

  test('refresh keeps a live slot\'s claims fresh', () => {
    const d = dir();
    claimFirst(d, ['JAVA-4'], { slot: 1, now: 1_000 });
    refresh(d, [1], 500_000);
    assert.equal(claimFirst(d, ['JAVA-4'], { slot: 2, now: 550_000, ttlMs: 120_000 }).key, null);
  });

  test('refresh skips a claim whose directory is gone when it writes (JAVA-669)', () => {
    const d = dir();
    mkdirSync(join(d, 'JAVA-7'), { recursive: true });
    // The listing sees JAVA-7, but the write targets JAVA-8's directory, which does not exist:
    // the same ENOENT a worker's `done` causes by releasing the claim mid-beat.
    writeFileSync(join(d, 'JAVA-7', 'claim.json'), JSON.stringify({ key: 'JAVA-8', slot: '1', time: 0 }));
    assert.doesNotThrow(() => refresh(d, [1], 1_000));
  });

  // card://JAVA-566: the beat acted on a listing made earlier and wrote slot 1 over slot 2's claim.
  test('refresh never overwrites a claim another slot took after its listing', () => {
    const d = dir();
    claimFirst(d, ['JAVA-20'], { slot: 1, session: 's1', now: 1_000 });
    afterFirstClaimRead(
      () => {
        release(d, 'JAVA-20', { slot: 1 });
        claimFirst(d, ['JAVA-20'], { slot: 2, session: 's2', now: 2_000 });
      },
      () => refresh(d, [1], 500_000),
    );
    const [c] = list(d, { now: 500_000, ttlMs: 120_000 });
    assert.equal(c.slot, '2');
    assert.equal(c.session, 's2');
    assert.equal(c.stale, true, "slot 1's beat does not keep slot 2's claim alive");
  });

  test('refresh survives a release between its listing and its write', () => {
    const d = dir();
    claimFirst(d, ['JAVA-21'], { slot: 1, now: 1_000 });
    afterFirstClaimRead(
      () => release(d, 'JAVA-21', { slot: 1 }),
      () => assert.doesNotThrow(() => refresh(d, [1], 5_000)),
    );
    assert.equal(existsSync(join(d, 'JAVA-21')), false, 'a released claim is not brought back');
  });

  // card://JAVA-566: B read the stale claim, A took it over, and B's rename then moved A's claim.
  test('two racers taking over one stale claim: exactly one wins', () => {
    const d = dir();
    claimFirst(d, ['JAVA-22'], { slot: 3, now: 1_000 });
    const late = 1_000 + 3_600_000;
    let a;
    const b = afterFirstClaimRead(
      () => (a = claimFirst(d, ['JAVA-22'], { slot: 1, now: late })),
      () => claimFirst(d, ['JAVA-22'], { slot: 2, now: late }),
    );
    assert.equal(a.key, 'JAVA-22');
    assert.equal(b.key, null);
    assert.equal(list(d, { now: late })[0].slot, '1');
  });

  test('of eight sessions racing to take over one stale claim, exactly one gets it', async () => {
    const d = dir();
    claimFirst(d, ['JAVA-23'], { slot: 9, now: 0 });
    const won = await race(d, [1, 2, 3, 4, 5, 6, 7, 8], ['JAVA-23']);
    assert.equal(won.filter((k) => k === 'JAVA-23').length, 1);
  });

  test('only its own slot releases a claim, unless told to', () => {
    const d = dir();
    claimFirst(d, ['JAVA-5'], { slot: 1 });
    assert.throws(() => release(d, 'JAVA-5', { slot: 2 }), /held by slot 1/);
    assert.equal(release(d, 'JAVA-5', { slot: 2, any: true }), true);
    assert.equal(release(d, 'JAVA-5', { slot: 1 }), false);
  });

  // The key is a path under the claims directory: a path-like key must never reach rmSync, whoever asks.
  test('release takes only a card key, never a path that leaves the claims directory', () => {
    const d = dir();
    claimFirst(d, ['JAVA-7'], { slot: 1 });
    const victim = join(d, '..', 'victim');
    mkdirSync(join(victim, 'sub'), { recursive: true });
    writeFileSync(join(victim, 'sub', 'f.txt'), 'keep');
    for (const key of ['../victim', '..', '.', 'a/b', '/abs', 'JAVA-1^', 'JAVA-7/..']) {
      assert.throws(() => release(d, key, { slot: 1, any: true }), /not a card key/, key);
    }
    assert.equal(existsSync(join(victim, 'sub', 'f.txt')), true, 'the directory outside the claims survives');
    assert.equal(existsSync(join(d, 'JAVA-7')), true, 'the real claim survives');
  });

  test('a claim being written by its winner counts as fresh', () => {
    const d = dir();
    claimFirst(d, ['JAVA-6'], { slot: 1 });
    writeFileSync(join(d, 'JAVA-6', 'claim.json'), '{not json');
    assert.equal(claimFirst(d, ['JAVA-6'], { slot: 2, now: Date.now() + 10 * 3_600_000 }).key, null);
  });

  test('anything that is not a card key is refused', () => {
    assert.throws(() => claimFirst(dir(), ['../etc'], { slot: 1 }), /not a card key/);
  });
});
