# Interview — Backend Engineer

<!-- Generated from form.json by `python3 tools/marketplace.py forms`. Edit form.json, then regenerate. -->

Record consent first (ceet-core references/consent.md). Then ask one question at a time, in order, and dig into vague answers: a recent example, a number, the exception. Record every answer verbatim with `interview.py answer`. The core and the real decisions are required; the depth modules are optional, and `interview.py next` suggests the questions that fill the profile's gaps.

| Module | Questions | Minutes, required questions | Minutes, all | |
| --- | --- | --- | --- | --- |
| Core interview | 22 | ~36 | ~56 | required |
| Real decisions | 6 | ~35 | ~35 | required |
| Depth: storage, APIs and performance | 14 | — | ~49 | optional |
| Depth: operations and resilience | 12 | — | ~45 | optional |
| Depth: security | 4 | — | ~13 | optional |
| Depth: code, tests and tools | 9 | — | ~32 | optional |
| Depth: working with others | 8 | — | ~23 | optional |

## Core interview

Who the person is and how they reason: enough evidence for the always-on core and the most consequential directives.

### A. Context

**Q1.** Walk me through what you own end-to-end. What systems or services?

<sub>~3 min · feeds `identity.cognitive_signature`, `directives.architecture.decomposition_philosophy`</sub>

**Q2.** What's your primary stack (language, DB, queue, cache, hosting)?

<sub>~2 min · feeds `identity.cognitive_signature`</sub>

**Q3.** How big is your team, and what's your seniority position inside it?

<sub>~1 min · optional · feeds `identity.cognitive_signature`, `directives.code_review.mentoring_voice`</sub>

**Q4.** What scale are you operating at (rps, rows, events/day, p99 SLO)?

<sub>~2 min · feeds `identity.cognitive_signature`, `directives.performance.latency_standards`</sub>

- Probe: What number would you put on it?

### B. Mental models

**Q5.** When you sit down to design a new service, what's the first thing you sketch — data model, API, sequence diagram, or something else? Why that first?

<sub>~3 min · feeds `identity.decision_framework`, `directives.architecture.decomposition_philosophy`</sub>

**Q6.** Do you think of your services more as "state machines," "pipelines," "event streams," or something else? Any analogy you'd use to explain your system to a new hire?

<sub>~3 min · feeds `identity.cognitive_signature`, `directives.architecture.state_management_rules`</sub>

**Q7.** What's a concept you use to reason about backend work that you don't think most engineers use?

<sub>~3 min · optional · feeds `identity.cognitive_signature`, `identity.core_values`</sub>

- Probe: Give me a recent, concrete example.

### C. Data integrity & correctness

**Q8.** Give me an example where you explicitly designed for *partial failure*. What did you do differently than the "happy path" version?

<sub>~4 min · captures decisions · feeds `directives.resilience.graceful_degradation`, `directives.resilience.retry_strategy`</sub>

**Q9.** How do you think about idempotency — do you retrofit it or design it in upfront? When is it overkill?

<sub>~3 min · feeds `directives.resilience.idempotency_approach`</sub>

- Probe: When does that rule break, and when does it never break?

**Q10.** When you see a new write path, what invariants do you immediately look for?

<sub>~3 min · optional · feeds `directives.code_review.blocking_criteria`, `directives.database.consistency_philosophy`</sub>

### G. Code review & quality

**Q24.** When you open a teammate's PR, what are the first three things your eye goes to?

<sub>~3 min · feeds `directives.code_review.philosophy`</sub>

**Q25.** What makes you say "this needs a refactor" — what's the trigger?

<sub>~2 min · optional · feeds `directives.code_review.refactoring_stance`</sub>

- Probe: Give me a recent, concrete example.

**Q26.** What's something you consistently flag in reviews that most engineers don't?

<sub>~3 min · feeds `directives.code_review.blocking_criteria`, `directives.code_review.nitpick_policy`</sub>

**Q27.** What's the difference between code you'd ship to prod vs. code you'd ship to a hackathon demo?

<sub>~2 min · optional · feeds `directives.personality.quality_calibration`</sub>

### I. Heuristics & principles

**Q31.** What's a rule of thumb you apply that's *not* in a textbook?

<sub>~3 min · feeds `identity.decision_framework`, `identity.core_values`</sub>

- Probe: When does that rule break, and when does it never break?

**Q32.** Finish the sentence: "Most backend engineers get X wrong, and the fix is Y."

<sub>~2 min · feeds `identity.core_values`, `directives.personality.primary_frustration`</sub>

**Q33.** What's the shortest-worded piece of advice you'd give to a mid-level engineer joining your team?

<sub>~2 min · optional · feeds `directives.code_review.mentoring_voice`, `identity.core_values`</sub>

### J. Vocabulary & voice

**Q34.** Are there words or phrases you deliberately avoid when writing docs or PR descriptions?

<sub>~2 min · feeds `identity.communication_voice`</sub>

**Q35.** Are there terms you insist on (your team's local vocabulary for something standard)?

<sub>~2 min · optional · feeds `identity.communication_voice`</sub>

**Q36.** When you write a postmortem, what's the tone — clinical, narrative, blameless?

<sub>~2 min · optional · feeds `directives.debugging.rca_process`, `identity.communication_voice`</sub>

### L. Anti-patterns

**Q39.** What's the thing you refuse to do, no matter the pressure? (And what's the story behind the line?)

<sub>~3 min · feeds `identity.core_values`, `directives.code_review.blocking_criteria`</sub>

**Q40.** What's a pattern that looks clever but you've learned to distrust?

<sub>~3 min · optional · feeds `directives.coding_style.paradigm_rules`, `directives.personality.novelty_stance`</sub>

## Real decisions

Cognitive task analysis on the person's own cases: an incident walk-through, a knowledge audit, a simulation on a real artifact, a contrast and a decision with partial information. The answers become the pack's examples.

### M. Real decisions

**Q41.** Pick a hard technical decision from the last few months, one where reasonable engineers would have disagreed. Walk me through it from the first signal: what you noticed, the options you had, what you chose, and what made the difference.

<sub>~8 min · incident · captures decisions · feeds `identity.decision_framework`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q28.** Tell me about an incident that permanently changed how you code.

<sub>~6 min · incident · captures decisions · feeds `directives.debugging.rca_process`, `directives.meta_cognition.crisis_personality`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?
- Probe: What would someone less experienced have done at that point?
- Probe: What would have changed your mind?

**Q42.** Think of a change to a write path in your system: a new field, a new consumer, a new retry. What would a capable mid-level engineer miss when reviewing it that you would catch? List the cues you look for.

<sub>~5 min · knowledge-audit · captures decisions · feeds `directives.code_review.blocking_criteria`, `directives.resilience.idempotency_approach`</sub>

- Probe: Why does that cue matter here?
- Probe: How would you teach someone to see it?

**Q43.** Bring a real pull request or design document you reviewed recently. Walk through it the way you did: where you slowed down, what you flagged, what you let go, and what you wrote.

<sub>~8 min · simulation · captures decisions · feeds `directives.code_review.philosophy`, `directives.code_review.nitpick_policy`, `directives.code_review.pr_size_policy`, `directives.code_review.mentoring_voice`</sub>

- Probe: Why did you let that one go?
- Probe: What would have made you block it?

**Q44.** Think of two proposals for the same kind of problem, one you approved and one you pushed back on (or build the pair now from your stack). What exactly made the difference?

<sub>~4 min · contrastive · captures decisions · feeds `identity.decision_framework`</sub>

- Probe: Which detail would flip your verdict?

**Q45.** Here is all you get: p99 latency doubled twenty minutes after a deploy, the error rate is unchanged, and no alert fired. What do you do first, and what is the one extra piece of information you ask for?

<sub>~4 min · limited-information · captures decisions · feeds `directives.debugging.silent_failure_protocol`, `directives.performance.latency_standards`, `directives.infrastructure.deployment_philosophy`</sub>

- Probe: Why that piece of information and not another?
- Probe: When would you roll back without knowing more?

## Depth: storage, APIs and performance (optional)

Data modeling, API shape, performance and data at scale.

### D. Storage & API choice

**Q11.** Where do you prefer to enforce constraints: database, application, message broker, or the UI? Why?

<sub>~3 min · optional · feeds `directives.database.consistency_philosophy`, `directives.security.validation_philosophy`</sub>

**Q12.** Walk me through your decision tree for Postgres vs. something else (DynamoDB, Mongo, Redis, Kafka, S3, etc.).

<sub>~4 min · optional · feeds `directives.architecture.persistence_philosophy`, `identity.decision_framework`</sub>

**Q13.** REST vs. RPC vs. event-driven — what's your default, and what pushes you off the default?

<sub>~3 min · optional · feeds `directives.architecture.decomposition_philosophy`, `directives.architecture.api_design_rules`</sub>

**Q14.** How do you version APIs? What's your stance on breaking changes?

<sub>~3 min · optional · feeds `directives.architecture.api_design_rules`</sub>

- Probe: When does that rule break, and when does it never break?

**Q15.** What's your default approach to pagination, filtering, and search? What smell makes you reject a proposed API shape?

<sub>~3 min · optional · feeds `directives.architecture.api_design_rules`</sub>

### E. Performance & scale

**Q16.** When a service is slow, what's the first thing you check? Second?

<sub>~3 min · optional · feeds `directives.performance.latency_standards`</sub>

**Q17.** Describe a time you picked *latency* over *consistency* (or vice versa) — what made the call?

<sub>~4 min · optional · captures decisions · feeds `directives.database.consistency_philosophy`, `identity.decision_framework`</sub>

**Q18.** What's your instinct around caching — where do you reach for it, where do you refuse to?

<sub>~3 min · optional · feeds `directives.performance.caching_rules`</sub>

**Q19.** How do you decide when a query needs an index vs. a rewrite vs. a denormalization?

<sub>~3 min · optional · feeds `directives.database.indexing_instincts`, `directives.performance.n_plus_one_prevention`</sub>

### N. Data at scale

**Q46.** Walk me through the last schema migration you ran on a table that could not go down. Which steps, in what order, and what would have made you stop?

<sub>~5 min · incident · optional · captures decisions · feeds `directives.database.migration_playbook`</sub>

**Q47.** How do you store and compute time and money? Give the rule you learned the hard way.

<sub>~3 min · optional · feeds `directives.database.time_and_money_rules`</sub>

**Q48.** When do you drop the ORM and write SQL by hand? When did you last do it?

<sub>~3 min · optional · feeds `directives.database.orm_threshold`</sub>

**Q49.** A table outgrows one node or one index. What is your sequence (archive, partition, shard, rethink), and what number triggers each step?

<sub>~4 min · optional · feeds `directives.database.partitioning_rules`</sub>

- Probe: What number would you put on it?

**Q50.** Tell me about a memory problem you chased: a leak, garbage-collection pauses, an out-of-memory kill. What did you look at, in what order?

<sub>~5 min · incident · optional · feeds `directives.performance.memory_leak_playbook`, `directives.performance.gc_philosophy`</sub>

## Depth: operations and resilience (optional)

Observability, delivery, failure handling and debugging.

### F. Observability & ops

**Q20.** What do you instrument *before* shipping a new endpoint?

<sub>~3 min · optional · feeds `directives.debugging.logging_philosophy`, `directives.infrastructure.alerting_rules`</sub>

**Q21.** What metric or dashboard do you watch after a deploy?

<sub>~2 min · optional · feeds `directives.infrastructure.deployment_philosophy`</sub>

**Q22.** What's your stance on log levels, structured logging, and what belongs in traces?

<sub>~3 min · optional · feeds `directives.debugging.logging_philosophy`</sub>

**Q23.** What alert would you never page on? What alert do you think everyone under-uses?

<sub>~3 min · optional · feeds `directives.infrastructure.alerting_rules`</sub>

### H. Failure & scar tissue

**Q29.** What's a bug you've shipped that you still think about?

<sub>~4 min · incident · optional · captures decisions · feeds `directives.debugging.rca_process`</sub>

**Q30.** What's a class of bug you've become allergic to, and how do you prevent it now?

<sub>~3 min · optional · feeds `directives.code_review.blocking_criteria`, `directives.coding_style.error_handling_rules`</sub>

### O. Delivery & resilience

**Q51.** Describe your ideal path from merge to production: what runs, what gates it, how you roll out, and how you roll back.

<sub>~4 min · optional · feeds `directives.infrastructure.ideal_pipeline`, `directives.infrastructure.deployment_philosophy`</sub>

**Q52.** Infrastructure as code and preview environments: what do you insist on, and what do you consider overkill?

<sub>~3 min · optional · feeds `directives.infrastructure.iac_stance`, `directives.infrastructure.ephemeral_env_policy`</sub>

**Q53.** A downstream dependency starts timing out or rate-limiting you. What does your code do: retries, backoff, circuit breaking, dead letters, degrading? Which numbers do you pick?

<sub>~5 min · optional · feeds `directives.resilience.retry_strategy`, `directives.resilience.dlq_handling`, `directives.resilience.rate_limit_adaptation`, `directives.resilience.graceful_degradation`</sub>

- Probe: What number would you put on it?

**Q54.** Tell me about a concurrency problem you designed around: two writers, a race, an ordering bug. What did you reach for: locks, queues, optimistic concurrency, something else?

<sub>~5 min · incident · optional · captures decisions · feeds `directives.architecture.concurrency_rules`</sub>

**Q55.** Tell me about a bug you could not reproduce, or a failure that raised no error at all. How did you find it?

<sub>~6 min · incident · optional · captures decisions · feeds `directives.debugging.ghost_bug_methodology`, `directives.debugging.silent_failure_protocol`</sub>

- Probe: What did you notice first, and what did it tell you?
- Probe: What options did you have, and which did you rule out quickly?

**Q56.** A dependency upgrade, or a CVE in one, breaks or threatens production. What is your sequence?

<sub>~4 min · optional · feeds `directives.debugging.dependency_resolution`, `directives.security.cve_response_plan`</sub>

## Depth: security (optional)

Trust boundaries, secrets, defaults and validation.

### P. Security

**Q57.** A call from another service inside your own network reaches your API. What do you require before you trust it?

<sub>~3 min · optional · feeds `directives.security.zero_trust_stance`</sub>

- Probe: When does that rule break, and when does it never break?

**Q58.** Where do secrets live in your systems, and what do you do in the first hour after one leaks into a commit or a log?

<sub>~3 min · optional · feeds `directives.security.secret_management_rules`</sub>

**Q59.** What security defaults do you set on every new web-facing service without being asked (headers, sessions, CORS, password hashing, encryption in transit and at rest)? Name the settings.

<sub>~4 min · optional · feeds `directives.security.web_security_defaults`, `directives.security.cryptography_defaults`</sub>

**Q60.** Where does input get validated in your services, and what happens to input that fails?

<sub>~3 min · optional · feeds `directives.security.validation_philosophy`</sub>

## Depth: code, tests and tools (optional)

Code style, testing, local setup and git habits.

### K. Taste

**Q37.** What does a "beautiful" backend codebase look like to you? Name a real example if you have one.

<sub>~3 min · optional · feeds `directives.coding_style.file_organization_rules`, `directives.coding_style.naming_rules`</sub>

**Q38.** What's something you do purely out of taste that you can't fully justify, but you'd fight to keep?

<sub>~2 min · optional · feeds `directives.coding_style.paradigm_rules`, `identity.core_values`</sub>

### Q. Code, tests & tools

**Q61.** Show me how you handle an error from a downstream call in your code, and tell me how strict you are with types. What would you block in a pull request on either?

<sub>~4 min · optional · feeds `directives.coding_style.error_handling_rules`, `directives.coding_style.typing_rules`</sub>

**Q62.** Open a file you are proud of. How is it organized, how are things named, where do comments go and where do they never go? Objects, functions, or a mix, and why?

<sub>~5 min · optional · feeds `directives.coding_style.file_organization_rules`, `directives.coding_style.naming_rules`, `directives.coding_style.commenting_rules`, `directives.coding_style.paradigm_rules`</sub>

**Q63.** Take the last feature you shipped. Which tests did you write first, which did you skip, and why?

<sub>~4 min · optional · captures decisions · feeds `directives.testing.tdd_reality`, `directives.testing.test_priority_rationale`</sub>

**Q64.** When do you mock, and when do you insist on a real database or service in tests? What coverage, if any, do you hold people to?

<sub>~4 min · optional · feeds `directives.testing.mocking_philosophy`, `directives.testing.coverage_expectations`, `directives.tooling.mocking_vs_staging`</sub>

- Probe: What number would you put on it?

**Q65.** How is your local setup for a service: what runs locally, what is faked, what goes to a shared environment? What have you automated that others still do by hand?

<sub>~4 min · optional · feeds `directives.tooling.local_environment`, `directives.tooling.automation_instincts`, `directives.tooling.mocking_vs_staging`</sub>

**Q66.** How do you branch, and how do you write commit messages? Paste a real commit message of yours that you would call a good one.

<sub>~3 min · optional · feeds `directives.git_workflow.branching_strategy`, `directives.git_workflow.commit_message_format`, `directives.git_workflow.commit_message_example`</sub>

**Q67.** How big is too big for a pull request, and what do you do with style nitpicks, yours and other people's?

<sub>~3 min · optional · feeds `directives.code_review.pr_size_policy`, `directives.code_review.nitpick_policy`</sub>

- Probe: What number would you put on it?

## Depth: working with others (optional)

Pushback, handover, uncertainty, focus and how the person has changed.

### R. Working with others

**Q68.** A product manager asks you to ship by Friday something you think is unsafe. What do you say, in your own words?

<sub>~3 min · optional · feeds `directives.stress_responses.pm_pushback_style`</sub>

**Q69.** You leave for two weeks tomorrow. What do you hand over, to whom, and how?

<sub>~3 min · optional · feeds `directives.stress_responses.handover_plan`</sub>

**Q70.** When you are unsure or stuck, how do you say so, and at what point do you escalate or ask for help? Give a recent example.

<sub>~3 min · optional · feeds `directives.meta_cognition.uncertainty_voice`, `directives.meta_cognition.escalation_protocol`</sub>

**Q71.** What engineering belief did you hold firmly three years ago and have dropped since? What changed your mind?

<sub>~3 min · optional · feeds `directives.meta_cognition.knowledge_evolution`</sub>

**Q72.** When do you do your best work? Describe a good focus block and what breaks it.

<sub>~2 min · optional · feeds `directives.personality.focus_preference`, `directives.personality.flow_state_description`</sub>

**Q73.** What reliably frustrates you in a codebase or in a team's habits?

<sub>~2 min · optional · feeds `directives.personality.primary_frustration`, `identity.frustration_triggers`</sub>

**Q74.** You inherit a ten-year-old service nobody understands. How do you treat the code, and the people who wrote it?

<sub>~3 min · optional · feeds `directives.personality.legacy_code_empathy`, `directives.code_review.refactoring_stance`</sub>

**Q75.** The last time you chose between building something and adopting a library or service, or between a proven and a new technology: what tipped it?

<sub>~4 min · optional · captures decisions · feeds `directives.architecture.build_vs_buy_rules`, `directives.personality.novelty_stance`</sub>

---

*Synthesize the profile, then run the teachback: show each directive with the questions it came from and let the person accept, edit or reject it. If they do not recognize themselves, re-interview that section.*
