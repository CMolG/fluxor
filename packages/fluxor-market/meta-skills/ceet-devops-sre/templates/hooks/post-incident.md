<!-- CEET Source:
  Role: devops-sre
  Directives: postmortem.*
-->

# post-incident Hook — {engineer_name}

> What {engineer_name} checks once an incident is resolved: the mechanical part runs as a check, the rest is judgment.

## Trigger

After every incident resolution


## Postmortem Trigger

{directives.postmortem.blameless_definition}

Propose the postmortem, with its owner and date.

## Action Items

{directives.postmortem.action_tracking}

List the action items with an owner each, ready to track.

## Communication

Draft the incident summary for stakeholders, following the comms ownership rules.

## Checks and judgment

The rules above that are not judgment calls (a credential in the diff, the commit message format, a
pattern I ban outright) run as executable checks from `hooks/checks.json`, wired only when their
bench is green. Everything else here is judgment: at this event, read the change against these rules
and report each concern with the rule it comes from and the fix you would make. Do not block on a
judgment call; the person decides.
