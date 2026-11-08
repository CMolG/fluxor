// Integration is the end of the review cycle: the reviewer (never the author) merges the card's
// branch into the control branch, resolves conflicts ON the control branch, re-runs the card's
// checks on the merged result, and pushes. Other slots push to the same branch at the same time,
// so a rejected push fetches, merges the new tip and tries again. It never forces: published
// history is never rewritten.

export const EXIT = Object.freeze({ ok: 0, error: 1, conflict: 3, exhausted: 4 });

const CARD = /\b[A-Z][A-Z0-9]*-\d+\b/g;
const REJECTED = /\[rejected\]|non-fast-forward|fetch first|failed to update ref|cannot lock ref|stale info/i;

const lines = (s) => s.split('\n').map((l) => l.trim()).filter(Boolean);
const has = (git, ref) => git(['rev-parse', '-q', '--verify', ref]).status === 0;

function conflicts(git, theirs) {
  const files = lines(git(['diff', '--name-only', '--diff-filter=U']).stdout);
  // The cards whose commits touched each conflicted file on the other side: read them (by key)
  // before resolving, so the resolution keeps both intents.
  const base = git(['merge-base', 'HEAD', theirs]).stdout.trim();
  const cards = {};
  for (const f of files) {
    const subjects = git(['log', '--format=%s', `${base}..${theirs}`, '--', f]).stdout;
    const head = git(['log', '--format=%s', `${base}..HEAD`, '--', f]).stdout;
    cards[f] = [...new Set([...`${subjects}\n${head}`.matchAll(CARD)].map((m) => m[0]))];
  }
  return { code: EXIT.conflict, files, cards };
}

function clean(git) {
  return git(['status', '--porcelain', '--untracked-files=no']).stdout.trim() === '';
}

const short = (git, ref) => git(['rev-parse', '--short', ref]).stdout.trim();

// What gets integrated is what the author PUBLISHED, because that is what was
// reviewed. Every slot shares one repository, so a local wt/<key> left by any worktree can lag
// behind it; one with commits the remote lacks was never reviewed, so it is refused, not merged.
// The local branch is used only when nothing is published.
function pick(git, { remote, key }) {
  const branch = `wt/${key}`;
  const tracking = `refs/remotes/${remote}/${branch}`;
  // An explicit refspec, and its exit code as the answer: a tracking ref left by a branch since
  // deleted on the remote must not count as published.
  const published = git(['fetch', '-q', remote, `+refs/heads/${branch}:${tracking}`]).status === 0;
  const local = has(git, `refs/heads/${branch}`);
  if (!published && !local) return { error: `No branch ${branch}, here or on ${remote}: the author has not published it.` };
  if (!published) return { source: branch, sha: short(git, branch) };
  if (local && git(['merge-base', '--is-ancestor', `refs/heads/${branch}`, tracking]).status !== 0) {
    return {
      error:
        `The local ${branch} (${short(git, `refs/heads/${branch}`)}) has commits ${remote}/${branch} (${short(git, tracking)}) does not: ` +
        `they were never published, so never reviewed. The author publishes them, or the stale local branch is deleted.`,
    };
  }
  return { source: `${remote}/${branch}`, sha: short(git, tracking) };
}

/** Merges the published `wt/<key>` (the local one when none is) into the control branch's tip, detached. Exit 3 leaves the conflicts to resolve. */
export function merge(git, { remote, target, key }) {
  if (!clean(git)) return { code: EXIT.error, error: 'The worktree has uncommitted changes: commit or discard them first.' };
  git(['config', 'rerere.enabled', 'true']);
  git(['config', 'rerere.autoUpdate', 'true']);
  const fetched = git(['fetch', '-q', remote, target]);
  if (fetched.status !== 0) return { code: EXIT.error, error: fetched.stderr.trim() };
  const chosen = pick(git, { remote, key });
  if (chosen.error) return { code: EXIT.error, error: chosen.error };
  const { source, sha } = chosen;
  const sw = git(['switch', '--detach', `${remote}/${target}`]);
  if (sw.status !== 0) return { code: EXIT.error, error: sw.stderr.trim() };
  const m = git(['merge', '--no-ff', '-m', `Merge wt/${key} into ${target} (${key})`, source]);
  if (m.status === 0) return { code: EXIT.ok, source, sha };
  if (has(git, 'MERGE_HEAD')) return { ...conflicts(git, source), source };
  return { code: EXIT.error, error: (m.stderr || m.stdout).trim() };
}

/** Pushes the merged HEAD to the control branch; on a rejection, merges the new tip and retries. */
export function push(git, { remote, target, key, retries = 5 }) {
  if (has(git, 'MERGE_HEAD')) return { code: EXIT.error, error: 'A merge is in progress: resolve, `git add`, `git commit --no-edit`, re-run the checks, then push again.' };
  if (!clean(git)) return { code: EXIT.error, error: 'The worktree has uncommitted changes.' };
  for (let attempt = 1; attempt <= retries; attempt++) {
    const p = git(['push', remote, `HEAD:refs/heads/${target}`]);
    if (p.status === 0) {
      // The card's branch is merged: tidy it. Failing here changes nothing that matters.
      git(['push', '-q', remote, '--delete', `wt/${key}`]);
      git(['branch', '-d', `wt/${key}`]);
      return { code: EXIT.ok, attempts: attempt, head: git(['rev-parse', 'HEAD']).stdout.trim() };
    }
    if (!REJECTED.test(p.stderr)) return { code: EXIT.error, error: p.stderr.trim() };
    // Another slot integrated first. Take its work in and try again: a merge, never a rebase or a force.
    git(['fetch', '-q', remote, target]);
    const m = git(['merge', '--no-ff', '-m', `Merge ${target} into the integration of ${key} (${key})`, `${remote}/${target}`]);
    if (m.status !== 0) {
      if (has(git, 'MERGE_HEAD')) return conflicts(git, `${remote}/${target}`);
      return { code: EXIT.error, error: (m.stderr || m.stdout).trim() };
    }
  }
  return { code: EXIT.exhausted, error: `Still rejected after ${retries} attempts.` };
}

/** Gives up on an integration: the worktree goes back to the control branch's tip, untouched. */
export function abort(git, { remote, target }) {
  if (has(git, 'MERGE_HEAD')) git(['merge', '--abort']);
  if (!clean(git)) return { code: EXIT.error, error: 'The worktree still has changes after aborting: look at `git status`.' };
  git(['fetch', '-q', remote, target]);
  const sw = git(['switch', '--detach', `${remote}/${target}`]);
  return sw.status === 0 ? { code: EXIT.ok } : { code: EXIT.error, error: sw.stderr.trim() };
}
