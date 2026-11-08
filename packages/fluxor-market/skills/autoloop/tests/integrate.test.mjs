// The review's integration, on a scratch repository with a bare remote: a conflict resolved on the
// control branch, a push another slot beat that is retried by merging, and never a force.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runner } from '../scripts/lib/context.mjs';
import { abort, EXIT, merge, push } from '../scripts/lib/integrate.mjs';

const scratch = mkdtempSync(join(tmpdir(), 'autoloop-git-'));
const gitconfig = join(scratch, 'gitconfig');
writeFileSync(gitconfig, '[user]\n\tname = Loop Test\n\temail = loop@example.com\n[init]\n\tdefaultBranch = main\n');
const env = { ...process.env, GIT_CONFIG_GLOBAL: gitconfig, GIT_CONFIG_NOSYSTEM: '1' };
const run = runner(null);

function repo(dir) {
  const git = (args) => run('git', args, { cwd: dir, env });
  const must = (args) => {
    const r = git(args);
    assert.equal(r.status, 0, `git ${args.join(' ')}: ${r.stderr}`);
    return r.stdout.trim();
  };
  const commit = (file, text, subject) => {
    writeFileSync(join(dir, file), text);
    must(['add', file]);
    must(['commit', '-q', '-m', subject]);
  };
  return { dir, git, must, commit };
}

function world() {
  const base = mkdtempSync(join(scratch, 'w-'));
  const bare = join(base, 'remote.git');
  run('git', ['init', '-q', '--bare', bare], { env });
  const clone = (name) => {
    run('git', ['clone', '-q', bare, join(base, name)], { env });
    return repo(join(base, name));
  };
  const seed = repo(join(base, 'seed'));
  run('git', ['init', '-q', seed.dir], { env });
  seed.commit('a.txt', 'one\ntwo\nthree\n', 'Start');
  seed.must(['remote', 'add', 'origin', bare]);
  seed.must(['push', '-q', 'origin', 'main', 'main:cb']);
  return { bare, seed, clone };
}

describe('integrate', () => {
  test('a conflict is resolved on the control branch, and a push another slot beat is retried', () => {
    const { seed, clone } = world();
    const author = clone('author');
    author.must(['switch', '-q', '--no-track', '-c', 'wt/K-1', 'origin/cb']);
    author.commit('a.txt', 'one\ntwo by K-1\nthree\n', 'Change two (K-1)');
    author.must(['push', '-q', 'origin', 'wt/K-1']);

    seed.must(['fetch', '-q', 'origin']);
    seed.must(['switch', '-q', '-c', 'cb', 'origin/cb']);
    seed.commit('a.txt', 'one\ntwo by K-2\nthree\n', 'Change two too (K-2)');
    seed.must(['push', '-q', 'origin', 'cb']);

    const reviewer = clone('reviewer');
    const m = merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-1' });
    assert.equal(m.code, EXIT.conflict);
    assert.deepEqual(m.files, ['a.txt']);
    assert.deepEqual(m.cards['a.txt'].sort(), ['K-1', 'K-2']);
    assert.equal(push(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-1' }).code, EXIT.error, 'no push mid-merge');

    writeFileSync(join(reviewer.dir, 'a.txt'), 'one\ntwo by K-1 and K-2\nthree\n');
    reviewer.must(['add', 'a.txt']);
    reviewer.must(['commit', '-q', '--no-edit']);

    // Meanwhile another slot integrates something else.
    seed.commit('b.txt', 'other\n', 'Another card (K-3)');
    seed.must(['push', '-q', 'origin', 'cb']);
    const beaten = seed.must(['rev-parse', 'HEAD']);

    const p = push(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-1' });
    assert.equal(p.code, EXIT.ok, p.error);
    assert.equal(p.attempts, 2);

    const check = clone('check');
    check.must(['switch', '-q', 'cb']);
    assert.equal(readFileSync(join(check.dir, 'a.txt'), 'utf8'), 'one\ntwo by K-1 and K-2\nthree\n');
    assert.equal(readFileSync(join(check.dir, 'b.txt'), 'utf8'), 'other\n');
    assert.equal(check.git(['merge-base', '--is-ancestor', beaten, 'HEAD']).status, 0, 'history only grew');
    assert.match(check.must(['log', '--format=%s', '-1', '--first-parent', 'HEAD~1']) + check.must(['log', '--format=%s']), /Merge wt\/K-1 into cb \(K-1\)/);
    assert.equal(check.git(['ls-remote', '--exit-code', '--heads', 'origin', 'wt/K-1']).status, 2, 'the merged card branch is tidied away');
  });

  test('a clean merge pushes in one attempt', () => {
    const { clone } = world();
    const author = clone('author');
    author.must(['switch', '-q', '--no-track', '-c', 'wt/K-4', 'origin/cb']);
    author.commit('c.txt', 'new\n', 'Add c (K-4)');
    author.must(['push', '-q', 'origin', 'wt/K-4']);
    const reviewer = clone('reviewer');
    assert.equal(merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-4' }).code, EXIT.ok);
    assert.equal(push(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-4' }).attempts, 1);
  });

  test('abort leaves the worktree on the control branch tip, and an unpublished card is refused', () => {
    const { seed, clone } = world();
    const author = clone('author');
    author.must(['switch', '-q', '--no-track', '-c', 'wt/K-5', 'origin/cb']);
    author.commit('a.txt', 'x\n', 'Rewrite (K-5)');
    author.must(['push', '-q', 'origin', 'wt/K-5']);
    seed.commit('a.txt', 'y\n', 'Rewrite too (K-6)');
    seed.must(['push', '-q', 'origin', 'main:cb']); // a fast-forward: cb was main's tip
    const reviewer = clone('reviewer');
    assert.equal(merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-5' }).code, EXIT.conflict);
    assert.equal(abort(reviewer.git, { remote: 'origin', target: 'cb' }).code, EXIT.ok);
    assert.equal(reviewer.must(['rev-parse', 'HEAD']), reviewer.must(['rev-parse', 'origin/cb']));
    assert.equal(merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-404' }).code, EXIT.error);
  });

  // Every slot shares one repository, so a local wt/<KEY> some worktree left
  // behind used to shadow the published branch, and an older round than the reviewed one merged.
  test('the published branch is merged, not a stale local one behind it', () => {
    const { clone } = world();
    const author = clone('author');
    author.must(['switch', '-q', '--no-track', '-c', 'wt/K-7', 'origin/cb']);
    author.commit('d.txt', 'first round\n', 'First round (K-7)');
    author.must(['push', '-q', 'origin', 'wt/K-7']);
    const reviewer = clone('reviewer');
    reviewer.must(['branch', 'wt/K-7', 'origin/wt/K-7']);
    author.commit('d.txt', 'reviewed round\n', 'The test the review asked for (K-7)');
    author.must(['push', '-q', 'origin', 'wt/K-7']);
    const reviewed = author.must(['rev-parse', 'HEAD']);

    const m = merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-7' });
    assert.equal(m.code, EXIT.ok, m.error);
    assert.equal(m.source, 'origin/wt/K-7');
    assert.equal(m.sha, reviewed.slice(0, m.sha.length));
    assert.equal(reviewer.git(['merge-base', '--is-ancestor', reviewed, 'HEAD']).status, 0, 'the reviewed round is in');
  });

  test('with nothing published, the local branch is merged', () => {
    const { clone } = world();
    const reviewer = clone('reviewer');
    reviewer.must(['switch', '-q', '--no-track', '-c', 'wt/K-8', 'origin/cb']);
    reviewer.commit('e.txt', 'local\n', 'Local only (K-8)');
    const local = reviewer.must(['rev-parse', 'HEAD']);
    reviewer.must(['switch', '-q', '--detach', 'origin/cb']);
    const m = merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-8' });
    assert.equal(m.code, EXIT.ok, m.error);
    assert.equal(m.source, 'wt/K-8');
    assert.equal(reviewer.git(['merge-base', '--is-ancestor', local, 'HEAD']).status, 0);
  });

  for (const shape of ['ahead of', 'diverged from']) {
    test(`a local branch ${shape} the published one is refused, naming both, worktree untouched`, () => {
      const { clone } = world();
      const author = clone('author');
      author.must(['switch', '-q', '--no-track', '-c', 'wt/K-9', 'origin/cb']);
      author.commit('f.txt', 'published\n', 'Published (K-9)');
      author.must(['push', '-q', 'origin', 'wt/K-9']);
      const reviewer = clone('reviewer');
      reviewer.must(['switch', '-q', '--no-track', '-c', 'wt/K-9', 'origin/wt/K-9']);
      if (shape === 'diverged from') reviewer.must(['reset', '-q', '--hard', 'origin/cb']);
      reviewer.commit('f.txt', 'unpublished\n', 'Not published (K-9)');
      const local = reviewer.must(['rev-parse', '--short', 'HEAD']);
      const published = reviewer.must(['rev-parse', '--short', 'origin/wt/K-9']);
      reviewer.must(['switch', '-q', '--detach', 'origin/cb']);
      const before = reviewer.must(['rev-parse', 'HEAD']);

      const m = merge(reviewer.git, { remote: 'origin', target: 'cb', key: 'K-9' });
      assert.equal(m.code, EXIT.error);
      assert.match(m.error, new RegExp(local));
      assert.match(m.error, new RegExp(published));
      assert.equal(reviewer.must(['rev-parse', 'HEAD']), before);
      assert.equal(reviewer.must(['status', '--porcelain']), '');
    });
  }

  test('the integration never forces a push', () => {
    const source = readFileSync(new URL('../scripts/lib/integrate.mjs', import.meta.url), 'utf8');
    const pushes = [...source.matchAll(/git\(\['push'[^\]]*\]/g)].map((m) => m[0]);
    assert.ok(pushes.length >= 2);
    for (const p of pushes) assert.doesNotMatch(p, /force|'-f'|'\+/);
  });
});
