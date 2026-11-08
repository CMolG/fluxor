# commit-changes: Safe Commit Step

A single step that records one finished unit of work (one task, one iteration) as one commit on the flow's own branch, staging only the paths that unit touched.

## What this step does

- Confirms that the current branch is the one the flow created for this run (`flow/<flow-id>/...`, checked out in place or in its own worktree), never the branch the user was on.
- Stages exactly the paths the unit of work modified, created or deleted: `git add -- <paths>`, and `git rm -- <path>` for a deleted file.
- Compares `git diff --cached --name-only` with that list, then commits with the message format the flow defines.

## Contract

- **Input:** the list of paths the unit of work touched, the verification verdict when the flow has one (from `run-tests`), and the commit message.
- **Output:** one commit on the flow branch, and its short hash.
- **Capabilities:** `git` (declared in the manifest's `requires`).

## Rules

- Never `git add -A`, `git add .` or `git commit -a`, and never stage a path the unit of work did not touch, including the flow's own logs (for example a `results.tsv`).
- One unit of work per commit: never mix two tasks or two iterations in one commit.
- Never `git reset --hard`, `git checkout -- .`, `git clean` or `git stash`; never amend, rebase, push, force-push or merge. A committed unit that must be undone is reverted with `git revert --no-edit <commit>` on the flow branch.
- Never bypass hooks (`--no-verify`): a failing hook is a failed commit.
- Do not commit a unit whose verification verdict is `fail`.
- The branch name and the message format come from the flow. The one convention this step adds: when the unit of work comes from a backlog card, the message ends with the card trailer `Card: card://<KEY>` (the backlog skill's reference format), one line per card.

## When it stops

After one commit. It stops without committing, and reports why, when the current branch is not the flow's, when the staged set differs from the unit's paths, when there is nothing to commit, when the verdict is `fail`, or when a hook fails.
