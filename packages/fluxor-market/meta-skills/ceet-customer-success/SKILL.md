---
name: ceet-customer-success
description: Use this skill to interview a customer success practitioner (CSM, CS leader, or account manager who owns existing customers) and turn their own judgment into a portable AI setup. It covers how they read account health, run QBRs, handle escalations, save at-risk accounts, and plan renewals and expansion. Trigger when that person, or someone with their consent, wants their CS thinking "cloned", extracted or captured: "interview me about retention", "clone our top CSM", "build an AI that preps QBRs like me", "capture my churn playbook". The interviewee must be a CS practitioner who is present and consenting. Do not use for interviewing other roles (analysts, engineers, sales reps) even about churn topics. Do not use for choosing between CEET roles, for everyday CS work (drafting a QBR agenda, onboarding plans, ranking CSMs), or for prospecting and closing new business (that is ceet-sales). Output works with any AI tool.
---

# CEET — Customer Success

## What this skill does

Interviews a customer success manager, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that onboards, reads account health, runs QBRs, saves at-risk accounts and renews the way they do. The pack goes to the project
(`.harness/packs/customer-success-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that writes customer-facing communication in their voice.
- A CS leader wants a top CSM's judgment captured and scaled.
- A founder wants retention instincts preserved as CS hiring starts.
- The user wants a portable artifact they can reuse across AI tools.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a customer success manager (a pack never serves evaluation, hiring or task allocation),
or cloning someone who is not in the conversation (that is `ceet-impersonator`, with its own rules).

## Run order

Follow the shared protocol in
[`../ceet-core/references/interview-protocol.md`](../ceet-core/references/interview-protocol.md);
the role's form is [`interview/form.json`](interview/form.json) (read as
[`interview/questions.md`](interview/questions.md)).

1. **Consent** before the first question (`interview.py statement`, then `interview.py start`).
2. **Held-out decisions**, if the person wants the clone's fidelity measured: 20–40 real past
   decisions set aside before the interview ([fidelity](../ceet-core/references/fidelity.md)).
3. **Core interview**, then **real decisions** (required), then the **depth modules** the person
   has time for; `interview.py next` picks the next question, `interview.py answer` records it verbatim.
4. **Synthesize** `cognitive-profile.json` following the
   [synthesis rules](../ceet-core/references/synthesis-rules.md), and the decisions into
   `examples/decisions.json`.
5. **Teachback**: the person accepts, edits or rejects every directive (`render_pack.py teachback`).
6. **Render** with `render_pack.py render <pack>`, show the person the dry run, then `--write`;
   `validate_pack.py` must pass. Offer the adapters for the tools they use.

## CS-specific things to listen for

These are the cognitive signals that distinguish a senior customer success manager from a textbook one. Use them
as probes when the interview drifts generic:

- **Health scoring instincts.** Signals they trust beyond the dashboard.
- **Onboarding philosophy.** First-value milestone, time-to-value target, checklist vs. flexible.
- **Adoption framework.** How they think about rollout, stakeholder alignment, internal champion.
- **QBR voice.** Format, cadence, attendee criteria, what they refuse to put in.
- **At-risk playbook.** Signals, escalation path, exec sponsor pattern, trade offers.
- **Renewal motion.** How early they start, discount posture, multi-year stance.
- **Expansion triggers.** Who they upsell, when, how they avoid poisoning the relationship.
- **Escalation handling.** How they absorb anger, when they loop in exec / product.
- **Handoff from sales.** What they wish sales would stop promising.
- **Advocate creation.** How they spot and cultivate references.

Escalation narration is high-signal: ask for one verbatim.

## Synthesis guardrails

- Capture their **customer archetypes** (e.g. "lukewarm exec, excited champion, skeptical admin") and how they treat each.
- Include their **QBR skeleton** verbatim if they have one.
- Preserve **escalation vocabulary** (the words they use when a customer is angry).
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never call that account green", re-interview that section and re-render.
