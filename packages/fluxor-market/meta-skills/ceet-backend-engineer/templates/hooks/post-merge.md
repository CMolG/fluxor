<!-- CEET Source:
  Role: backend-engineer
  Directives: debugging.dependency_resolution, infrastructure.ideal_pipeline
-->

# post-merge Hook — {engineer_name}

> What {engineer_name} checks at post-merge: the mechanical part runs as a check, the rest is judgment.

## Trigger

After every merge


## Dependency Check

{directives.debugging.dependency_resolution}

After merge, verify all dependencies are consistent.

## Pipeline Verification

{directives.infrastructure.ideal_pipeline}

Verify the pipeline is executing as expected.

## Post-Merge Actions

1. Run dependency installation/lock file update
2. Check for new environment variables or secrets needed
3. Run smoke tests if available
4. Report any drift from the pipeline definition

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this git event, read the change against these
rules and report each concern with the rule it comes from and the fix you would make. Do not block
on a judgment call; the person decides.
