// Control branch resolution: --target, then the config, then the sprint template; a spent target
// moves to the next sprint under the template and stops the loop otherwise.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { currentRound, onSpent, resolveTarget, roundName, roundsOf, spentFrom } from '../scripts/lib/target.mjs';

test('the flag wins over the config, the config over the template', () => {
  const config = { target: 'feat/mine' };
  assert.deepEqual(resolveTarget({ flag: 'feat/flag', config, sprint: 3, projectTag: 'java' }), { branch: 'feat/flag', source: 'flag' });
  assert.deepEqual(resolveTarget({ config, sprint: 3, projectTag: 'java' }), { branch: 'feat/mine', source: 'config' });
  assert.deepEqual(resolveTarget({ config: {}, sprint: 3, projectTag: 'java' }), { branch: 'feat/cb-java-sprint-3', source: 'template' });
});

test('a custom template, and no sprint at all', () => {
  assert.equal(resolveTarget({ config: { targetTemplate: 'cb/{projectTag}/{sprint}' }, sprint: '12', projectTag: 'x' }).branch, 'cb/x/12');
  assert.match(resolveTarget({ config: {}, projectTag: 'x' }).error, /--sprint/);
});

test('spent = a merged pull request, the latest one', () => {
  assert.deepEqual(spentFrom([]), { spent: false });
  assert.deepEqual(spentFrom([{ number: 1, mergedAt: null }]), { spent: false });
  const v = spentFrom([{ number: 3, mergedAt: '2026-09-01T00:00:00Z' }, { number: 9, mergedAt: '2026-09-30T00:00:00Z' }], ['abc late']);
  assert.deepEqual(v, { spent: true, pr: 9, mergedAt: '2026-09-30T00:00:00Z', after: ['abc late'] });
});

test('spent under the template moves on; a branch the person chose stops the loop', () => {
  assert.equal(onSpent('template').action, 'next-sprint');
  assert.equal(onSpent('flag').action, 'stop');
  assert.equal(onSpent('config').action, 'stop');
});

// card://JAVA-2004: a sprint outlives its control branch's pull request, so the template names the sprint and the round
// is found on the remote: <base> is the first, <base>-<n> the n-th.
test('rounds are the base and its numbered successors, never another sprint', () => {
  const heads = ['refs/heads/main', 'refs/heads/feat/cb-java-sprint-4', 'refs/heads/feat/cb-java-sprint-4-7',
    'refs/heads/feat/cb-java-sprint-4-2', 'refs/heads/feat/cb-java-sprint-40', 'refs/heads/feat/cb-java-sprint-4-x'];
  assert.deepEqual(roundsOf(heads, 'feat/cb-java-sprint-4'), [1, 2, 7]);
  assert.equal(roundName('feat/cb-java-sprint-4', 1), 'feat/cb-java-sprint-4');
  assert.equal(roundName('feat/cb-java-sprint-4', 8), 'feat/cb-java-sprint-4-8');
});

const remote = (heads, merged) => ({
  config: { remote: 'origin', baseBranch: 'main' },
  root: '/repo',
  git: (args) => args[0] === 'ls-remote'
    ? { status: 0, stdout: heads.map((h) => `abc\trefs/heads/${h}`).join('\n') }
    : { status: 0, stdout: '' },
  run: (cmd, args) => ({ status: 0, stdout: JSON.stringify(merged.includes(args[3]) ? [{ number: 1, mergedAt: '2026-11-03T17:58:08Z' }] : []), stderr: '' }),
});

test('the live round is the latest unspent one, and a spent latest opens the next', () => {
  const heads = ['feat/cb-java-sprint-4', 'feat/cb-java-sprint-4-6', 'feat/cb-java-sprint-4-7'];
  assert.deepEqual(currentRound(remote(heads, ['feat/cb-java-sprint-4-6']), 'feat/cb-java-sprint-4'),
    { branch: 'feat/cb-java-sprint-4-7', round: 7, opened: false });
  const next = currentRound(remote(heads, ['feat/cb-java-sprint-4-7']), 'feat/cb-java-sprint-4');
  assert.equal(next.branch, 'feat/cb-java-sprint-4-8');
  assert.equal(next.opened, true);
  assert.deepEqual(currentRound(remote([], []), 'feat/cb-java-sprint-5'), { branch: 'feat/cb-java-sprint-5', round: 1, opened: true });
});
