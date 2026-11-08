<!-- CEET Source:
  Role: backend-engineer
  Directives: testing.*, security.*, performance.latency_standards
-->

# pre-push Hook — {engineer_name}

> What {engineer_name} checks at pre-push: the mechanical part runs as a check, the rest is judgment.

## Trigger

Before every push


## Test Requirements

{directives.testing.tdd_reality}

{directives.testing.coverage_expectations}

Run the test suite and report against the coverage expectations above.

## Security Scan

{directives.security.cve_response_plan}

{directives.security.web_security_defaults}

Run security scanning. Handle CVE findings per the CVE response plan above.

## Performance Check

{directives.performance.latency_standards}

If performance tests exist, report endpoints that miss the latency thresholds above.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this git event, read the change against these
rules and report each concern with the rule it comes from and the fix you would make. Do not block
on a judgment call; the person decides.
