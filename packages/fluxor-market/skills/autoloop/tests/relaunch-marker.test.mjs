// The relaunch marker a worker leaves, read back by the supervisor (JAVA-1445): a held slot keeps its hold through a
// marker that names no tier, and a marker naming a tier the supervisor does not know starts nothing.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DEFAULTS } from '../scripts/lib/context.mjs';
import { liveDeps } from '../scripts/lib/supervisor.mjs';

const MARKER = '.claude/autoloop.relaunch';
const setup = (marker) => {
  const worktree = mkdtempSync(join(tmpdir(), 'relaunch-marker-'));
  mkdirSync(join(worktree, '.claude'), { recursive: true });
  writeFileSync(join(worktree, MARKER), JSON.stringify(marker));
  const ctx = { config: { ...DEFAULTS, relaunchMarker: MARKER }, fs: (p) => p };
  return { deps: liveDeps(ctx), slot: (run) => ({ n: 1, worktree, run }) };
};

describe('the relaunch marker a worker leaves', () => {
  test('a marker with no tier keeps the hold the slot runs under', () => {
    const { deps, slot } = setup({ model: 'claude-haiku-5-5', effort: 'medium' });
    const held = deps.relaunchMarker(slot({ model: 'claude-sonnet-5-5', effort: 'high', toolTier: 'comment' }));
    assert.deepEqual(held, { model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'comment' });
  });

  test('a marker with no tier on a slot that runs unheld stays unheld', () => {
    const { deps, slot } = setup({ model: 'claude-haiku-5-5', effort: 'medium' });
    assert.deepEqual(deps.relaunchMarker(slot({ model: 'claude-sonnet-5-5', effort: 'high' })),
      { model: 'claude-haiku-5-5', effort: 'medium' });
  });

  test('a marker naming an unknown tier starts nothing', () => {
    const { deps, slot } = setup({ model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'admin' });
    assert.equal(deps.relaunchMarker(slot({ model: 'claude-sonnet-5-5', effort: 'high', toolTier: 'comment' })), null);
  });
});
