// The control branch: where every slot's reviewed work is integrated, and what a person merges
// into the main branch by hand, never the loop. Chosen by the person (`--target`, then the config),
// else derived from the active sprint (`targetTemplate`). Its pull request merged = spent: the
// loop never integrates into a spent branch.

/** {branch, source} from the flag, the config or the sprint template, in that order; else {error}. */
export function resolveTarget({ flag, config = {}, sprint, projectTag }) {
  if (flag) return { branch: flag, source: 'flag' };
  if (config.target) return { branch: config.target, source: 'config' };
  if (sprint === undefined || sprint === null || sprint === '') {
    return { error: 'No control branch: pass --target <branch>, set "target" in the config, or pass --sprint <n> (the active sprint).' };
  }
  const template = config.targetTemplate ?? 'feat/cb-{projectTag}-sprint-{sprint}';
  return { branch: template.replaceAll('{projectTag}', projectTag).replaceAll('{sprint}', String(sprint)), source: 'template' };
}

/**
 * Whether a branch is spent, from `gh pr list --head <branch> --state merged --json number,mergedAt`
 * output. `after` is the list of commits on the branch made after that merge: work that reached the
 * branch too late and has to be carried to the next one.
 */
export function spentFrom(prs, after = []) {
  const merged = (prs ?? []).filter((p) => p.mergedAt).sort((a, b) => b.mergedAt.localeCompare(a.mergedAt))[0];
  if (!merged) return { spent: false };
  return { spent: true, pr: merged.number, mergedAt: merged.mergedAt, after };
}

/** What the loop does once its target is spent: move on with the template, stop otherwise. */
export function onSpent(source) {
  return source === 'template'
    ? { action: 'next-sprint', say: "The control branch's pull request merged. Resolve the active sprint and run `target --sprint <n>`: it moves to that sprint's next round." }
    : { action: 'stop', say: 'The control branch the person chose is spent (its pull request merged). The loop stops: ask the person for the next one.' };
}

/**
 * A sprint's control branch in rounds (2026-11-03): `<base>` is its first, `<base>-<n>` its n-th. A sprint
 * outlives the pull request of its control branch (one sprint had seven, each named by hand, and a config left
 * pointing at a spent one refused to start), so the template names the sprint and the round is found on the
 * remote: its latest, or the next one once the latest has merged.
 */
export function roundsOf(heads, base) {
  const rounds = [];
  for (const head of heads) {
    const name = head.replace(/^refs\/heads\//, '');
    if (name === base) rounds.push(1);
    else if (name.startsWith(`${base}-`) && /^\d+$/.test(name.slice(base.length + 1))) rounds.push(Number(name.slice(base.length + 1)));
  }
  return rounds.sort((a, b) => a - b);
}

export const roundName = (base, round) => (round <= 1 ? base : `${base}-${round}`);

/** {branch, round, opened}: the sprint's live round, opening the next one when the latest is spent. */
export function currentRound(ctx, base) {
  const heads = ctx.git(['ls-remote', '--heads', ctx.config.remote]);
  if (heads.status !== 0) throw new Error(`cannot reach ${ctx.config.remote}: ${heads.stderr.trim()}`);
  const rounds = roundsOf(heads.stdout.split('\n').map((line) => line.split('\t')[1]).filter(Boolean), base);
  if (!rounds.length) return { branch: base, round: 1, opened: true };
  const latest = rounds.at(-1);
  const spent = checkSpent(ctx, roundName(base, latest));
  return spent.spent
    ? { branch: roundName(base, latest + 1), round: latest + 1, opened: true, after: spent.after ?? [] }
    : { branch: roundName(base, latest), round: latest, opened: false };
}

export function checkSpent(ctx, branch) {
  const r = ctx.run('gh', ['pr', 'list', '--head', branch, '--state', 'merged', '--json', 'number,mergedAt', '--limit', '5'], { cwd: ctx.root });
  if (r.status !== 0) return { spent: false, unknown: r.stderr.trim() || 'gh failed' };
  const verdict = spentFrom(JSON.parse(r.stdout || '[]'));
  if (verdict.spent) {
    const { remote, baseBranch } = ctx.config;
    ctx.git(['fetch', '-q', remote, baseBranch, branch]);
    const log = ctx.git(['log', '--format=%h %s', `--since=${verdict.mergedAt}`, `${remote}/${baseBranch}..${remote}/${branch}`]);
    verdict.after = log.stdout.split('\n').filter(Boolean);
  }
  return verdict;
}

/** Makes sure the control branch exists on the remote: created from the base branch, never tracking it. */
export function ensureRemoteBranch(ctx, branch) {
  const { remote, baseBranch } = ctx.config;
  const heads = ctx.git(['ls-remote', '--heads', remote, branch]);
  if (heads.status !== 0) throw new Error(`cannot reach ${remote}: ${heads.stderr.trim()}`);
  if (heads.stdout.trim()) {
    ctx.git(['fetch', '-q', remote, branch]);
    return { created: false };
  }
  const fetch = ctx.git(['fetch', '-q', remote, baseBranch]);
  if (fetch.status !== 0) throw new Error(fetch.stderr.trim());
  // A remote ref straight from the base branch's remote ref: no local branch, so nothing can be
  // left tracking the base branch (an IDE pushes to a branch's upstream).
  const push = ctx.git(['push', remote, `refs/remotes/${remote}/${baseBranch}:refs/heads/${branch}`]);
  if (push.status !== 0) throw new Error(push.stderr.trim());
  ctx.git(['fetch', '-q', remote, branch]);
  return { created: true };
}
