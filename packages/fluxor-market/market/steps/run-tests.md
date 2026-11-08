# run-tests: Verification Run Step

A single step that runs the project's own verification (its test suite, plus the build, lint and type-check commands the project defines) against the current working tree and reports the verdict. It observes; it does not fix.

## What this step does

- Finds the verification commands, in this order: the commands the flow names, the commands the project's configuration names, then the project's own scripts (for example a `test`, `build`, `lint` or `typecheck` script, a `Makefile` target, or the commands its CI workflow runs). It uses the project's commands as they are and never invents a runner.
- Runs the full suite. A flow may ask for a narrower run first (the tests of the changed module), but a narrower run never replaces the full run before a commit.
- Reports every command with its exit status, and for each failure the failing test or check, the file and line when the output gives one, and the relevant excerpt of the output.

## Contract

- **Input:** the working tree to verify (usually the change the previous step made) and, optionally, the commands or scope the flow names.
- **Output:** a verdict: `pass`, `fail`, or `no-tests` when the project defines no tests, with the commands that ran and the failures found. A suite that cannot run (a missing dependency, a broken configuration) is `fail`, never `pass`.
- **Capabilities:** `shell`, `test-runner` (declared in the manifest's `requires`).

## Rules

- Do not modify code, tests, snapshots or configuration in this step.
- Never make the run greener than the code: no skipping, disabling or deleting tests, no filters that leave failing tests out, no flags that tolerate failures, no lowered coverage thresholds.
- A test that fails and then passes on one rerun is reported as flaky, not as a pass.
- `no-tests` is not `pass`: the flow decides what an unverified change means for it.

## When it stops

After one verification run and its report. Fixing a failure belongs to the flow's next step (or to a revert of the change), not to this one.
