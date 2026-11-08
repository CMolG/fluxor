<!-- CEET Source:
  Role: frontend-engineer
  Directives: performance.bundle_strategy
-->

# post-merge Hook — {engineer_name}

> What {engineer_name} checks at post-merge: the mechanical part runs as a check, the rest is judgment.

## Trigger

After every merge


## Bundle Size Check

{directives.performance.bundle_strategy}

Report any bundle size regression the merge introduced.

## Visual Regression

{directives.testing.visual_regression}

Run visual regression tests if available and report the differences.

## Dependency Update

Check for new dependencies, verify lock file consistency, run smoke tests.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this git event, read the change against these
rules and report each concern with the rule it comes from and the fix you would make. Do not block
on a judgment call; the person decides.
