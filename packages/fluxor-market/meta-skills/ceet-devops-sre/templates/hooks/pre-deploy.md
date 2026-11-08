<!-- CEET Source:
  Role: devops-sre
  Directives: change_management.*, slo_management.*
-->

# pre-deploy Hook — {engineer_name}

> What {engineer_name} checks before a deployment: the mechanical part runs as a check, the rest is judgment.

## Trigger

Before every deployment


## Deployment Strategy

{directives.change_management.deployment_default}

{directives.change_management.canary_rules}

## SLO Check

{directives.slo_management.error_budget_policy}

Report whether the error budget allows this deployment, with the numbers.

## Rollback Plan

{directives.change_management.rollback_philosophy}

Say how this change rolls back, or that it cannot.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this event, read the change against these rules
and report each concern with the rule it comes from and the fix you would make. Do not block on a
judgment call; the person decides.
