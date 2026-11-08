---
name: ceet-legal-compliance
description: Cognitive Extraction Engine for in-house legal counsel and compliance leads in software companies. Use whenever a user wants to "clone" a legal or compliance operator's judgment about risk posture, contract redlines, escalation, privacy, policy and incidents, or build a personalized AI environment that does first-pass contract review, policy drafting and regulatory triage in their style. Trigger on phrases like "extract my legal thinking", "clone our GC", "build an AI that reviews contracts like me", "interview me about compliance", "capture my risk framework", or "make a legal cognitive clone". The output is a reasoning style, never legal advice. Outputs are tool-agnostic (Claude, ChatGPT, Cursor, Copilot, Gemini, etc.).
---

# CEET — Legal / Compliance

> **Note:** The outputs of this CEET describe *how one person reasons about legal and compliance work*; they are not, and must not be used as, legal advice. Every pack carries that disclaimer in its communication standards, which every agent, skill and command inherits, and flags final decisions for human counsel.

## What this skill does

Interviews a counsel or compliance lead, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that reviews contracts, weighs risk, drafts policy and triages regulatory questions the way they do. The pack goes to the project
(`.harness/packs/legal-compliance-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that does *first-pass* contract review, policy drafting, or regulatory triage in their voice.
- A GC wants their judgment scaled across a team or product partners.
- A founder wants legal instincts captured before hiring in-house.
- The user wants a portable artifact they can reuse across AI tools.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a counsel or compliance lead (a pack never serves evaluation, hiring or task allocation),
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

## Legal-specific things to listen for

These are the cognitive signals that distinguish a senior counsel or compliance lead from a textbook one. Use them
as probes when the interview drifts generic:

- **Risk posture.** Where on the paranoid↔business-enabling spectrum.
- **Contract playbook.** Standard markup positions on liability, indemnity, IP, warranty, termination, auto-renewal.
- **Escalation criteria.** What they handle, what goes to outside counsel, what must go to a partner.
- **Regulatory frameworks in scope.** GDPR, CCPA, HIPAA, SOC 2, DORA, AI Act, state-by-state US.
- **Privacy stance.** Data minimization, consent, DPAs, sub-processor discipline.
- **Policy drafting voice.** Terse, narrative, example-driven?
- **Risk register approach.** What risks get tracked, how often revisited.
- **Business partnership stance.** How they frame "no" as "yes, if…"
- **IP hygiene.** Open-source license review, employee IP, customer data use.
- **Disputes & incident response.** Breach notification, security incident legal flow.

Have them redline a fake one-page MSA live. The way they narrate each change is gold.

## Synthesis guardrails

- Capture their **standard redline positions** as a reusable playbook.
- Include a **disclaimer block** in the AI environment — the AI is reasoning in their style, not providing legal advice.
- Note the jurisdictions they actually practice in and where they *don't* opine.
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
If they say "close, but I'd never concede that cap", re-interview that section and re-render.
