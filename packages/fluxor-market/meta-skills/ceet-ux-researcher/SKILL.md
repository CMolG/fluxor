---
name: ceet-ux-researcher
description: Use this skill to run the CEET interview that extracts a UX researcher's own judgment and turns it into a portable "cognitive clone" pack, so an AI frames research questions, picks methods, recruits, interviews, synthesizes and drafts study plans, discussion guides and readouts the way that person does. Use when someone wants to be interviewed, or to interview a departing or senior researcher, about their research thinking, with an emphasis on observed behavior over stated preference. Triggers: "extract my research thinking", "make a UXR cognitive clone", "build an AI that drafts interview guides like me", "capture how I synthesize interviews", "re-run my UXR profile". Output works across Claude, ChatGPT, Cursor, Copilot and Gemini. Not for choosing among CEET roles, generic research deliverables, evaluating or ranking researchers, or cloning non-researchers (designers, customer success, etc.).
---

# CEET — UX Researcher

## What this skill does

Interviews a UX researcher, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that frames questions, picks methods, runs sessions and synthesizes findings the way they do. The pack goes to the project
(`.harness/packs/ux-researcher-<person>/`), never into this skill's folder.

"Behavioral" here means focused on **observed behavior**, not just stated preference: the default orientation is toward what users do over what users say.

## When to use

- The user wants an AI that writes discussion guides, codes interviews, and drafts readouts in their style.
- A research lead wants to scale research literacy across designers, PMs, or AI-assisted helpers.
- A solo researcher wants an AI thinking partner that respects behavioral rigor.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a UX researcher (a pack never serves evaluation, hiring or task allocation),
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

## UXR-specific things to listen for

These are the cognitive signals that distinguish a senior UX researcher from a textbook one. Use them
as probes when the interview drifts generic:

- **Research question design.** How they reshape product questions into answerable research questions.
- **Method selection.** Interviews, diary studies, usability tests, surveys, analytics, ethnography — their tree.
- **Behavioral vs. attitudinal discipline.** What they trust, what they discount.
- **Participant recruiting standards.** Who they'd refuse to include and why.
- **Interview technique.** Laddering, critical incident, think-aloud, silence discipline.
- **Synthesis workflow.** Affinity mapping, tagging, JTBD statements, behavioral archetypes.
- **Communicating findings.** Readout formats, what they show the team vs. leadership.
- **Influence pattern.** How they make research actually change a decision.
- **Ethics.** Consent, recording, compensation, anonymization — what they insist on.
- **Validity reflexes.** Bias they watch for in themselves and their team.

Ask them to read a random page from a recent interview transcript out loud. How they narrate what was important is itself data.

## Synthesis guardrails

- Capture their exact **interview opener** and **closing question** if they have go-to phrases.
- Include a **synthesis procedure** — the step-by-step from transcripts to claim.
- Preserve vocabulary (JTBD vs. need vs. jobs vs. goal vs. outcome — teams differ).
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never claim that from five sessions", re-interview that section and re-render.
