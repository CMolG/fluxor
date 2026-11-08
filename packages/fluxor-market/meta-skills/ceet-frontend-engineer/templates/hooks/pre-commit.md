<!-- CEET Source:
  Role: frontend-engineer
  Directives: typescript.*, styling.*, git_workflow.*
-->

# pre-commit Hook — {engineer_name}

> What {engineer_name} checks at pre-commit: the mechanical part runs as a check, the rest is judgment.

## Trigger

Before every commit


## Commit Message Format

{directives.git_workflow.commit_message_format}

Example:
{directives.git_workflow.commit_message_example}

The format check runs from `hooks/checks.json` when the format is precise enough to be one; otherwise,
point out a message that does not follow it and propose one that does.

## TypeScript Check

{directives.typescript.strictness_level}

{directives.typescript.any_policy}

Run the type checker at the strictness above and report what violates these rules.

## Styling Lint

{directives.styling.methodology}

## a11y Lint

{directives.accessibility.pre_merge_checklist}

## Secrets

The secret check blocks credentials in a diff; also flag anything secret-like it could miss, such as
an API key shipped in a client bundle.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this git event, read the change against these
rules and report each concern with the rule it comes from and the fix you would make. Do not block
on a judgment call; the person decides.
