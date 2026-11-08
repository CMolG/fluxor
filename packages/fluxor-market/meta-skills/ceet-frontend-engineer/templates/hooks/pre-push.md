<!-- CEET Source:
  Role: frontend-engineer
  Directives: testing.*, performance.*, accessibility.*
-->

# pre-push Hook — {engineer_name}

> What {engineer_name} checks at pre-push: the mechanical part runs as a check, the rest is judgment.

## Trigger

Before every push


## Test Suite

{directives.testing.unit_component_e2e_mix}

{directives.testing.coverage_expectations}

Run the test suite and report against the coverage expectations above.

## a11y Scan

{directives.accessibility.testing_approach}

## Performance Budget

{directives.performance.web_vitals_priority}

{directives.performance.bundle_strategy}

If a bundle or performance budget exists, report what goes over it.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this git event, read the change against these
rules and report each concern with the rule it comes from and the fix you would make. Do not block
on a judgment call; the person decides.
