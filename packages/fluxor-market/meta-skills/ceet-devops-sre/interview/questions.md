# Interview — DevOps / SRE

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 23 | ~38 | ~61 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: incidents and postmortems | 7 | — | ~21 | optional |
| Depth: toil, platform, security and cost | 14 | — | ~33 | optional |
| Depth: voice and working with others | 7 | — | ~16 | optional |

## Core interview

Who the person is and how they reason about reliability and change: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** What do you own — cloud accounts, clusters, pipelines, platform abstractions? Describe the surface area.

<sub>~3 min · feeds `identity.cognitive_signature`</sub>

**Q2.** What's your stack (cloud, orchestrator, IaC tool, CI, observability)?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.iac.tool_choice`</sub>

**Q3.** What's your team shape (embedded SRE, platform team, solo)?

<sub>~2 min · optional · feeds `identity.cognitive_signature`</sub>

**Q4.** What scale & reliability targets are you operating against (SLOs, uptime, MTTR)?

<sub>~3 min · feeds `identity.cognitive_signature`, `directives.slo_management.slo_selection`</sub>

- Probe: What number would you put on it?

### B. Mental models

**Q5.** How do you mentally represent your system — as a topology, a dependency graph, a flow of requests, a set of control loops? Why that one?

<sub>~3 min · feeds `identity.decision_framework`, `identity.cognitive_signature`</sub>

**Q6.** What's the analogy you use to explain reliability to non-engineers?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q7.** What do you believe about reliability that most teams get wrong?

<sub>~3 min · feeds `identity.core_values`</sub>

### C. SLOs & error budgets

**Q8.** Do you run on SLOs? If so, how do you pick them? If not, what do you use instead?

<sub>~3 min · feeds `directives.slo_management.slo_selection`</sub>

- Probe: What number would you put on it?

**Q9.** When an error budget burns, what changes in your week?

<sub>~3 min · feeds `directives.slo_management.error_budget_policy`, `directives.slo_management.burn_rate_response`</sub>

- Probe: Give me a recent, concrete example.

**Q10.** How do you negotiate reliability vs. feature velocity with product?

<sub>~3 min · optional · feeds `directives.slo_management.error_budget_policy`</sub>

- Probe: Give me a recent, concrete example.

### D. Observability

**Q11.** Logs / metrics / traces / profiles / events — what do you instrument first on a new service?

<sub>~3 min · feeds `directives.observability.instrumentation_first`</sub>

**Q12.** What's the one dashboard you open during an incident? What's on it?

<sub>~2 min · optional · feeds `directives.observability.dashboard_philosophy`</sub>

**Q13.** What alert rule have you found most false-positive-prone, and how did you fix it?

<sub>~3 min · optional · feeds `directives.observability.false_positive_policy`</sub>

**Q14.** What's the difference between a page, a ticket, and a log-only event in your world?

<sub>~3 min · feeds `directives.observability.page_vs_ticket`</sub>

- Probe: When does that rule break, and when does it never break?

### E. Change & release

**Q15.** Canary / blue-green / feature flags / progressive rollout — which is your default and when do you deviate?

<sub>~3 min · feeds `directives.change_management.deployment_default`, `directives.change_management.canary_rules`, `directives.change_management.feature_flag_policy`</sub>

- Probe: When does that rule break, and when does it never break?

**Q16.** How do you think about deploy risk, and what's your pre-deploy checklist?

<sub>~3 min · optional · feeds `directives.change_management.deployment_default`</sub>

**Q17.** What change do you require a second reviewer for, no exceptions?

<sub>~2 min · optional · feeds `directives.change_management.deployment_default`, `directives.security.refused_shortcuts`</sub>

**Q18.** What's your rollback philosophy — always possible, practiced, or last resort?

<sub>~3 min · feeds `directives.change_management.rollback_philosophy`</sub>

- Probe: Give me a recent, concrete example.

### M. Heuristics

**Q42.** "If a service doesn't have X, I don't let it go to prod."

<sub>~3 min · feeds `identity.decision_framework`, `directives.observability.instrumentation_first`</sub>

- Probe: When does that rule break, and when does it never break?

**Q43.** "When my pager goes off for Y, I immediately check Z."

<sub>~2 min · optional · feeds `directives.incident_response.first_five_minutes`</sub>

**Q44.** "When someone says 'we just need to add more instances', my first question is…"

<sub>~2 min · optional · feeds `directives.cost.cost_traps`, `identity.decision_framework`</sub>

### N. Anti-patterns

**Q45.** What pattern do you see shops do that makes you wince?

<sub>~3 min · feeds `identity.core_values`, `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

**Q46.** What's something that looked like best practice 5 years ago that you now avoid?

<sub>~2 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### O. Real decisions

**Q47.** Pick a hard infrastructure or reliability decision from the last few months, one where reasonable engineers would have disagreed: a migration, a platform choice, an SLO, a change freeze. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q22.** Name one incident that permanently changed how you think. What's the story?

<sub>~6 min · incident · captures decisions · feeds `directives.meta_cognition.crisis_personality`, `directives.incident_response.war_room_rules`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q48.** Think of a change to your pipeline or your infrastructure code: a new service account, a Terraform module bump, a new deploy stage. What would a capable mid-level engineer miss when reviewing it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.change_management.canary_rules`, `directives.iac.versioning_policy`, `directives.security.least_privilege`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q49.** Bring a real postmortem or runbook you wrote or reviewed recently. Walk through it the way you did: what you kept, what you rewrote, what you sent back, and why.

<sub>~8 min · simulation · captures decisions · feeds `directives.postmortem.mandatory_sections`, `directives.postmortem.blameless_definition`, `directives.postmortem.action_tracking`</sub>

- Probe: What did you change in it, and why?
- Probe: What would you never let through in one?

**Q50.** Think of two changes that were ready to go out on a Friday afternoon, one you let ship and one you held (or build the pair now from your systems). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `directives.change_management.deployment_default`, `identity.decision_framework`</sub>

- Probe: Which detail would flip your verdict?

**Q51.** Here is all you get: since 03:10, 2% of requests get a 502 from the load balancer, the service's own error metric is flat, and the last deploy was yesterday afternoon. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.incident_response.first_five_minutes`, `directives.observability.dashboard_philosophy`, `directives.change_management.rollback_philosophy`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you roll back without knowing more?

## Depth: incidents and postmortems (optional)

Running an incident, classifying it, and writing it up.

### F. Incident response

**Q19.** Walk me through the first 5 minutes of a sev-1 in your system.

<sub>~4 min · optional · feeds `directives.incident_response.first_five_minutes`</sub>

**Q20.** Who owns the comms vs. the fix? How do you run the incident channel?

<sub>~3 min · optional · feeds `directives.incident_response.comms_ownership`, `directives.incident_response.war_room_rules`</sub>

**Q21.** What's a rule you apply in incidents that junior engineers routinely violate?

<sub>~2 min · optional · feeds `directives.incident_response.war_room_rules`</sub>

**Q52.** How do you decide an incident's severity? Give the thresholds you use, and a case you classified wrong.

<sub>~3 min · optional · feeds `directives.incident_response.severity_classification`</sub>

- Probe: What number would you put on it?

### G. Postmortems

**Q23.** Blameless — what does that actually mean in your writing?

<sub>~3 min · optional · feeds `directives.postmortem.blameless_definition`</sub>

**Q24.** Mandatory sections in your postmortems? Forbidden phrases?

<sub>~3 min · optional · feeds `directives.postmortem.mandatory_sections`, `directives.postmortem.forbidden_phrases`</sub>

**Q25.** How do you track action items after they're written — and what % actually get done?

<sub>~3 min · optional · feeds `directives.postmortem.action_tracking`</sub>

- Probe: What number would you put on it?

## Depth: toil, platform, security and cost (optional)

Automation, infrastructure as code, git habits, security defaults and cost.

### H. Toil & automation

**Q26.** What do you consider toil, and what's your team's policy on it?

<sub>~3 min · optional · feeds `directives.toil.toil_definition`, `directives.toil.automation_policy`</sub>

**Q27.** What's a task you deliberately haven't automated, and why?

<sub>~2 min · optional · feeds `directives.toil.deliberate_non_automation`</sub>

**Q28.** What's a manual workaround you've done 3+ times that you *should* have automated sooner?

<sub>~2 min · optional · feeds `directives.toil.automation_policy`</sub>

### I. IaC & platform taste

**Q29.** Terraform / Pulumi / Crossplane / CDK — what's your stack and honest opinions?

<sub>~3 min · optional · feeds `directives.iac.tool_choice`</sub>

**Q30.** How do you structure modules / workspaces / state? What's your versioning story?

<sub>~3 min · optional · feeds `directives.iac.module_structure`, `directives.iac.versioning_policy`</sub>

**Q31.** Where do you allow "click-ops," and where do you refuse?

<sub>~2 min · optional · feeds `directives.iac.click_ops_stance`</sub>

- Probe: When does that rule break, and when does it never break?

**Q32.** What's your stance on internal developer platforms (Backstage, Humanitec, etc.) — golden path vs. paved road vs. optional?

<sub>~2 min · optional · feeds `identity.decision_framework`</sub>

**Q55.** How do you branch and write commit messages for infrastructure and pipeline changes? Paste a real commit message of yours that you would call a good one.

<sub>~3 min · optional · feeds `directives.git_workflow.branching_strategy`, `directives.git_workflow.commit_message_format`, `directives.git_workflow.commit_message_example`</sub>

### J. Security

**Q33.** Secret management — vault, sops, cloud native? Why?

<sub>~2 min · optional · feeds `directives.security.secret_management`</sub>

**Q34.** What least-privilege pattern do you insist on?

<sub>~2 min · optional · feeds `directives.security.least_privilege`</sub>

**Q35.** What's a security shortcut you see often and always reject?

<sub>~2 min · optional · feeds `directives.security.refused_shortcuts`</sub>

### K. Cost

**Q36.** How much does cost enter your daily thinking?

<sub>~2 min · optional · feeds `directives.cost.daily_cost_awareness`</sub>

**Q37.** What's a cost optimization that's worth it, and one that's a trap?

<sub>~3 min · optional · feeds `directives.cost.optimization_wins`, `directives.cost.cost_traps`</sub>

**Q38.** How do you explain a surprise bill to finance?

<sub>~2 min · optional · feeds `identity.communication_voice`, `directives.cost.daily_cost_awareness`</sub>

## Depth: voice and working with others (optional)

Vocabulary, uncertainty, quality bar, focus and frustration.

### L. Vocabulary & voice

**Q39.** Any local words your team uses for services, environments, or deploy stages?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q40.** What tone do you write runbooks in — imperative, narrative, checklist?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q41.** What postmortem phrase do you ban ("human error")?

<sub>~2 min · optional · feeds `directives.postmortem.forbidden_phrases`</sub>

### P. Working with others

**Q53.** When you are unsure or stuck, in an incident or outside one, how do you say so, and at what point do you escalate or pull someone in? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q54.** What is the difference between a script you would run once by hand and one you would hand to the on-call rotation? Show me the last one you promoted.

<sub>~3 min · optional · feeds `directives.personality.quality_calibration`</sub>

**Q56.** When do you do your best work, and how do you protect it from interrupts and on-call? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q57.** What reliably frustrates you in a platform or in a team's habits?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
