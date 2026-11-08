// JAVA-1445: the tools a session gets from the tool tier its role declares.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { TIERS, toolSurface } from '../scripts/lib/tiers.mjs';
import { parseRun } from '../scripts/lib/pick-run.mjs';

const on = { enabled: true };
const denied = ['--disallowedTools', 'Edit Write NotebookEdit PowerShell'];

describe('toolSurface', () => {
  test('a read or comment session loses the file-writing tools and carries its tier to the guard', () => {
    assert.deepEqual(toolSurface('read', on), { args: denied, env: { AUTOLOOP_TOOL_TIER: 'read' } });
    assert.deepEqual(toolSurface('comment', on), { args: denied, env: { AUTOLOOP_TOOL_TIER: 'comment' } });
  });

  test('a write session, a role with no tier and tiers switched off launch exactly as today', () => {
    assert.deepEqual(toolSurface('write', on), { args: [], env: {} });
    assert.deepEqual(toolSurface(undefined, on), { args: [], env: {} });
    assert.deepEqual(toolSurface('read', { enabled: false }), { args: [], env: {} });
    assert.deepEqual(toolSurface('read', undefined), { args: [], env: {} });
  });

  test('an unknown tier is refused, never launched as write', () => {
    assert.throws(() => toolSurface('admin', on), /read, comment, write/);
  });

  test('the tiers are listed narrowest first', () => {
    assert.deepEqual(TIERS, ['read', 'comment', 'write']);
  });
});

describe('parseRun with a tier', () => {
  test('a run may name its tier; the tier is kept when it is a known one', () => {
    assert.deepEqual(parseRun('{"model":"claude-haiku-5-5","effort":"medium","toolTier":"comment"}'),
      { model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'comment' });
  });

  test('a run without a tier is still a run, with no tier', () => {
    assert.deepEqual(parseRun('{"model":"claude-haiku-5-5","effort":"medium"}'), { model: 'claude-haiku-5-5', effort: 'medium' });
  });

  test('an unknown tier makes the run no run at all: a session never starts on a tier it cannot read', () => {
    assert.equal(parseRun('{"model":"claude-haiku-5-5","effort":"medium","toolTier":"admin"}'), null);
  });

  test('the card the run is for is kept as `card` when it is a card key, and left out otherwise (JAVA-1808)', () => {
    assert.deepEqual(parseRun('{"model":"claude-haiku-5-5","effort":"medium","toolTier":"write","key":"JAVA-1808"}'),
      { model: 'claude-haiku-5-5', effort: 'medium', toolTier: 'write', card: 'JAVA-1808' });
    assert.deepEqual(parseRun('{"model":"claude-haiku-5-5","effort":"medium","key":"rm -rf"}'), { model: 'claude-haiku-5-5', effort: 'medium' });
    assert.deepEqual(parseRun('{"model":"claude-haiku-5-5","effort":"medium","key":null}'), { model: 'claude-haiku-5-5', effort: 'medium' });
  });
});
