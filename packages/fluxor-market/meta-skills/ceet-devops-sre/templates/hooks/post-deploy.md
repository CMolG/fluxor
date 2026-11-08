<!-- CEET Source:
  Role: devops-sre
  Directives: observability.*, slo_management.*
-->

# post-deploy Hook — {engineer_name}

> What {engineer_name} checks after a deployment: the mechanical part runs as a check, the rest is judgment.

## Trigger

After every deployment


## Observability Verification

{directives.observability.instrumentation_first}

Report which dashboards and alerts for the change are live, and which are missing.

## SLO Verification

{directives.slo_management.burn_rate_response}

Watch the burn rate for the window the directive above sets.

## Canary Health

Compare the canary's metrics against the baseline and say whether the rollback philosophy calls for
rolling back.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this event, read the change against these rules
and report each concern with the rule it comes from and the fix you would make. Do not block on a
judgment call; the person decides.
