---
name: ceet-devops-sre
description: Cognitive Extraction Engine for DevOps and SRE practitioners. Use when a user wants to clone the judgment of an infrastructure, platform, or reliability engineer — how they think about CI/CD, observability, incident response, capacity planning, on-call, and reliability tradeoffs. Trigger on phrases like "extract my SRE thinking", "clone our platform engineer", "build an AI ops assistant that thinks like our oncall", "interview me about infrastructure", "capture how I run postmortems", or any request to distill DevOps/SRE judgment into a reusable AI configuration. Outputs are tool-agnostic.
---

# CEET — DevOps / SRE

## What this skill does

Interviews a platform, infrastructure or reliability engineer, with their consent, and turns the
answers into a **pack**: their cognitive profile, a short always-on core, their real decisions as
examples, and the agents, skills, commands, rules and hooks rendered from the profile, with adapters
for Claude Code, Cursor, Copilot, `AGENTS.md` and Agent Skills. The pack goes to the project
(`.harness/packs/devops-sre-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that reviews Terraform, Kubernetes, Helm or pipeline code with their specific
  standards.
- The user wants incident response, postmortems and runbooks written in their voice.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking an engineer (a pack never serves evaluation, hiring or task allocation),
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

## SRE-specific things to listen for

These are the cognitive signals that distinguish a senior SRE from a textbook one. Use them as
probes when the interview drifts generic:

- **Error-budget thinking.** Do they run on SLOs? What changes in their week when a budget burns, and
  how do they negotiate with product?
- **Blast radius.** When changing infrastructure, how do they bound the worst case?
- **Page vs. ticket.** What deserves waking someone up, and what never does.
- **The first five minutes.** SRE judgment is overwhelmingly shaped by incidents; the real-decisions
  module asks for them. Get the cues they noticed, not only the story.
- **Postmortem voice.** Blameless in practice, the sections they require, the phrases they ban.
- **Observability layering.** Logs, metrics, traces, profiles: what they instrument first.
- **Change management.** Canary, blue-green, flags, progressive delivery: their defaults and their
  rollback discipline.
- **Toil.** What they call toil, what they automate, and what they deliberately leave manual.
- **IaC taste.** Terraform, Pulumi, Crossplane, CDK: opinions, module structure and where click-ops
  is tolerated.
- **Cost and security reflexes.** Least privilege, secrets, and when they push back on a bill.

## Synthesis guardrails

- Keep the person's **own vocabulary**, and specific vendor and tool names when they matter (they
  often do in this role).
- Include at least one **runbook-style decision procedure** ("when the latency SLO burns, I…"), and
  the page / no-page criteria explicitly: they shape the AI's alerting advice.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a commit message pattern, a banned construct in a
  manifest) also goes into `checks` with the question it came from, so it can run as a hook once its
  bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never page on that," re-interview that section and re-render.
