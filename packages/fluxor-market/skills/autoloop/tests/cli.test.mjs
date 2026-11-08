// The worker's side of the CLI, end to end on a scratch repository: two slots claim different
// cards, an author publishes and parks, a reviewer integrates.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const CLI = fileURLToPath(new URL('../scripts/autoloop.mjs', import.meta.url));
const base = mkdtempSync(join(tmpdir(), 'autoloop-cli-'));
const gitconfig = join(base, 'gitconfig');
writeFileSync(gitconfig, '[user]\n\tname = Loop Test\n\temail = loop@example.com\n[init]\n\tdefaultBranch = main\n');
const env = { ...process.env, GIT_CONFIG_GLOBAL: gitconfig, GIT_CONFIG_NOSYSTEM: '1', AUTOLOOP_TARGET: 'cb' };
delete env.CLAUDE_PROJECT_DIR;
delete env.AUTOLOOP_SLOT;

const git = (cwd, ...args) => {
  const r = spawnSync('git', args, { cwd, env, encoding: 'utf8' });
  assert.equal(r.status, 0, `git ${args.join(' ')}: ${r.stderr}`);
  return r.stdout.trim();
};
const cli = (cwd, slot, ...args) => spawnSync(process.execPath, [CLI, ...args], { cwd, env: { ...env, AUTOLOOP_SLOT: String(slot) }, encoding: 'utf8' });

test('help needs no repository', () => {
  const r = spawnSync(process.execPath, [CLI, '--help'], { cwd: base, encoding: 'utf8' });
  assert.equal(r.status, 0);
  assert.match(r.stdout, /integrate <KEY> merge\|push\|abort/);
});

test('claim, begin, publish, done, integrate', () => {
  const bare = join(base, 'remote.git');
  spawnSync('git', ['init', '-q', '--bare', bare], { env });
  const seed = join(base, 'seed');
  git(base, 'init', '-q', seed);
  writeFileSync(join(seed, 'a.txt'), 'one\n');
  git(seed, 'add', 'a.txt');
  git(seed, 'commit', '-q', '-m', 'Start');
  git(seed, 'remote', 'add', 'origin', bare);
  git(seed, 'push', '-q', 'origin', 'main', 'main:cb');

  const slot1 = join(base, 'loop-1');
  git(base, 'clone', '-q', bare, slot1);
  git(slot1, 'worktree', 'add', '-q', '--detach', join(base, 'loop-2'), 'origin/cb');
  const slot2 = join(base, 'loop-2');

  // Both slots offer the same candidates in the same order: they end on different cards.
  assert.match(cli(slot1, 1, 'claim', 'K-1', 'K-2').stdout, /claimed K-1/);
  assert.match(cli(slot2, 2, 'claim', 'K-1', 'K-2').stdout, /claimed K-2/, 'the claims dir is shared by the worktrees');
  const refused = cli(slot2, 2, 'claim', 'K-1');
  assert.equal(refused.status, 1);
  // A slot variable that disagrees with the worktree is refused, never trusted: on 2026-10-01 a
  // daemon handed slot 1's environment to slot 2, and both claimed one card.
  const wrong = cli(slot2, 1, 'claim', 'K-3');
  assert.equal(wrong.status, 6);
  assert.match(wrong.stderr, /worktree is slot 2/);
  assert.match(cli(slot1, 1, 'slot').stdout, /RESUME/);

  assert.equal(cli(slot1, 1, 'begin', 'K-1').status, 0);
  assert.equal(git(slot1, 'branch', '--show-current'), 'wt/K-1');
  writeFileSync(join(slot1, 'b.txt'), 'by K-1\n');
  git(slot1, 'add', 'b.txt');
  git(slot1, 'commit', '-q', '-m', 'Add b (K-1)');
  const early = cli(slot1, 1, 'done');
  assert.equal(early.status, 1);
  assert.match(early.stderr, /publish K-1/);
  assert.equal(cli(slot1, 1, 'publish', 'K-1').status, 0);
  const done = cli(slot1, 1, 'done');
  assert.equal(done.status, 0, done.stderr);
  assert.ok(existsSync(join(slot1, '.claude/autoloop.done')));
  assert.equal(git(slot1, 'branch', '--show-current'), '', 'parked detached on the control branch');
  assert.doesNotMatch(cli(slot1, 1, 'claims').stdout, /K-1/);
  assert.doesNotMatch(cli(slot1, 1, 'slot').stdout, /RESUME/);

  // Slot 2 reviews K-1 and integrates it.
  const merged = cli(slot2, 2, 'integrate', 'K-1', 'merge');
  assert.equal(merged.status, 0, merged.stdout + merged.stderr);
  assert.match(merged.stdout, /merged origin\/wt\/K-1 at [0-9a-f]{7,}/);
  const pushed = cli(slot2, 2, 'integrate', 'K-1', 'push');
  assert.equal(pushed.status, 0, pushed.stdout + pushed.stderr);
  git(seed, 'fetch', '-q', 'origin');
  assert.equal(git(seed, 'show', 'origin/cb:b.txt'), 'by K-1');
});

test('idle is refused on a slot with a card, and parks an empty one', () => {
  const repo = join(base, 'idle', 'loop-1');
  git(base, 'init', '-q', repo);
  writeFileSync(join(repo, 'a.txt'), 'one\n');
  git(repo, 'add', 'a.txt');
  git(repo, 'commit', '-q', '-m', 'Start');
  assert.match(cli(repo, 1, 'claim', 'K-7').stdout, /claimed K-7/);
  const held = cli(repo, 1, 'idle');
  assert.equal(held.status, 1);
  assert.match(held.stderr, /holds K-7/);
  cli(repo, 1, 'release', 'K-7');
  git(repo, 'switch', '-q', '-c', 'wt/K-7');
  assert.match(cli(repo, 1, 'idle').stderr, /on wt\/K-7/);
  git(repo, 'switch', '-q', '--detach');
  writeFileSync(join(repo, 'a.txt'), 'changed\n');
  assert.match(cli(repo, 1, 'idle').stderr, /Uncommitted changes/);
  git(repo, 'checkout', '-q', '--', 'a.txt');
  assert.ok(!existsSync(join(repo, '.claude/autoloop.idle')), 'nothing is written for a refused call');

  const ok = cli(repo, 1, 'idle', '--reason', 'no card in review');
  assert.equal(ok.status, 0, ok.stderr);
  assert.match(ok.stdout, /parks this slot for 30 min/);
  const marker = JSON.parse(readFileSync(join(repo, '.claude/autoloop.idle'), 'utf8'));
  assert.equal(marker.reason, 'no card in review');
  assert.ok(!existsSync(join(repo, '.claude/autoloop.done')), 'idle is not done');
});

test('status prints the tracker\x27s stop reason and its gate while standing by', () => {
  const repo = join(base, 'status', 'loop-1');
  git(base, 'init', '-q', repo);
  const dir = join(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'), 'autoloop');
  mkdirSync(dir, { recursive: true });
  const gate = { branch: 'feat/x', compareUrl: 'https://example.com/compare', wallCard: 'PROJ-9' };
  writeFileSync(join(dir, 'state.json'), JSON.stringify({ slots: [], target: 'cb', source: 't', updatedAt: 0, standby: true, remoteSwitch: { stopReason: 'merge the branch', gate } }));
  const out = cli(repo, 1, 'status').stdout;
  assert.match(out, /^Stopped by the tracker: merge the branch$/m);
  assert.match(out, /^ {2}branch feat\/x · https:\/\/example.com\/compare$/m);
  assert.match(out, /^ {2}merge card PROJ-9$/m);
});

test('start refuses an unknown phase before touching anything', () => {
  const repo = join(base, 'phases');
  git(base, 'init', '-q', repo);
  const r = cli(repo, 0, 'start', '1', '--target', 'cb', '--phases', 'review,doing');
  assert.equal(r.status, 2);
  assert.match(r.stderr, /Unknown phase\(s\) doing: use review, ready, todo, refine, or all/);
});

test('start --standby refuses a loop with no remote switch before touching anything', () => {
  const repo = join(base, 'standby');
  git(base, 'init', '-q', repo);
  const r = cli(repo, 0, 'start', '1', '--target', 'cb', '--standby');
  assert.equal(r.status, 2);
  assert.match(r.stderr, /--standby needs a remote switch/);
});

test('start refuses to start when pickRun fails on this machine, before touching anything', () => {
  const repo = join(base, 'pickrun');
  git(base, 'init', '-q', repo);
  mkdirSync(join(repo, '.harness', 'config'), { recursive: true });
  writeFileSync(join(repo, '.harness', 'config', 'autoloop.json'),
    JSON.stringify({ pickRun: { command: "echo 'no heartbeat token on this machine' >&2; exit 1" } }));
  const r = cli(repo, 0, 'start', '1', '--target', 'cb');
  assert.equal(r.status, 6);
  assert.match(r.stderr, /pickRun failed on this machine: no heartbeat token on this machine\. Every session would start on an unknown run/);
  assert.equal(existsSync(join(repo, '.git', 'autoloop', 'state.json')), false);
});

test('relaunch carries a known tier into the marker and refuses an unknown one', () => {
  const repo = join(base, 'relaunch-tier', 'loop-1');
  git(base, 'init', '-q', repo);
  const refused = cli(repo, 1, 'relaunch', '--model', 'claude-haiku-5-5', '--effort', 'medium', '--tier', 'admin');
  assert.equal(refused.status, 2);
  assert.match(refused.stderr, /read, comment, write/);
  assert.ok(!existsSync(join(repo, '.claude/autoloop.relaunch')), 'nothing is written for a refused tier');

  const ok = cli(repo, 1, 'relaunch', '--model', 'claude-haiku-5-5', '--effort', 'medium', '--tier', 'comment');
  assert.equal(ok.status, 0, ok.stderr);
  assert.equal(JSON.parse(readFileSync(join(repo, '.claude/autoloop.relaunch'), 'utf8')).toolTier, 'comment');
});

test('a session held to a tier cannot widen it by relaunching', () => {
  const repo = join(base, 'relaunch-held', 'loop-1');
  git(base, 'init', '-q', repo);
  const held = (...args) => spawnSync(process.execPath, [CLI, ...args], {
    cwd: repo, env: { ...env, AUTOLOOP_SLOT: '1', AUTOLOOP_TOOL_TIER: 'comment' }, encoding: 'utf8',
  });
  const model = ['--model', 'claude-haiku-5-5', '--effort', 'medium'];
  for (const tierArgs of [['--tier', 'write'], []]) {
    const r = held('relaunch', ...model, ...tierArgs);
    assert.equal(r.status, 2, `held relaunch ${tierArgs.join(' ') || 'with no tier'} is refused`);
    assert.match(r.stderr, /holds the tool tier comment/);
  }
  assert.ok(!existsSync(join(repo, '.claude/autoloop.relaunch')), 'nothing is written for a widening');
  assert.equal(held('relaunch', ...model, '--tier', 'read').status, 0, 'a narrower tier is allowed');
});

test('relaunch writes the marker, keeps the claims, and refuses a bad effort', () => {
  const repo = join(base, 'relaunch', 'loop-1');
  git(base, 'init', '-q', repo);
  assert.match(cli(repo, 1, 'claim', 'K-9').stdout, /claimed K-9/);
  const bad = cli(repo, 1, 'relaunch', '--model', 'claude-sonnet-5-5', '--effort', 'turbo');
  assert.equal(bad.status, 2);
  assert.match(bad.stderr, /low, medium, high, xhigh, max/);
  assert.equal(cli(repo, 1, 'relaunch', '--effort', 'low').status, 2, 'a model is required');
  assert.ok(!existsSync(join(repo, '.claude/autoloop.relaunch')), 'nothing is written for a refused call');

  const ok = cli(repo, 1, 'relaunch', '--model', 'claude-sonnet-5-5', '--effort', 'medium');
  assert.equal(ok.status, 0, ok.stderr);
  const marker = JSON.parse(readFileSync(join(repo, '.claude/autoloop.relaunch'), 'utf8'));
  assert.equal(marker.model, 'claude-sonnet-5-5');
  assert.equal(marker.effort, 'medium');
  assert.ok(!Number.isNaN(Date.parse(marker.at)));
  assert.ok(!existsSync(join(repo, '.claude/autoloop.done')), 'the done marker is not written');
  assert.match(cli(repo, 1, 'claims').stdout, /K-9/, 'the claim is still held');
});
