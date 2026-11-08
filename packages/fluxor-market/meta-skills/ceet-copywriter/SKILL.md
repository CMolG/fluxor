---
name: ceet-copywriter
description: Cognitive Extraction Engine for copywriters, UX writers and content designers. Use whenever a user wants to "clone" a writer's voice, editorial judgment and conversion instincts, or build a personalized AI environment that drafts and edits landing pages, emails, ads and microcopy in their voice. Trigger on phrases like "extract my copy voice", "clone our copywriter", "build an AI that writes in my tone", "interview me about writing", "capture my brand voice", or "make a copywriter cognitive clone". Not for campaign strategy, channels or positioning (that is ceet-marketing). Outputs are tool-agnostic (Claude, ChatGPT, Cursor, Copilot, Gemini, etc.).
---

# CEET — Copywriter

## What this skill does

Interviews a copywriter, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that writes and edits in their voice, with their judgment about structure, persuasion and words. The pack goes to the project
(`.harness/packs/copywriter-<person>/`), never into this skill's folder.

## When to use

- The user wants AI that writes landing pages, emails, product copy, or microcopy in their voice.
- A brand wants to codify editorial standards for AI-assisted writing across teams.
- A solo writer wants reusable rules beyond a "brand voice doc."
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a copywriter (a pack never serves evaluation, hiring or task allocation),
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

## Copywriter-specific things to listen for

These are the cognitive signals that distinguish a senior copywriter from a textbook one. Use them
as probes when the interview drifts generic:

- **Voice principles.** Not "friendly and professional" — the specific shape (contractions? semicolons? sentence length? rhythm?).
- **Hook & structure.** How they open a landing page / email / ad. Their AIDA-or-not.
- **Audience empathy.** How they imagine the reader. What they assume about attention.
- **Persuasion stance.** Proof, story, feature-benefit, provocation — which they favor.
- **Editing craft.** Ruthless cutting, cadence checks, reading aloud.
- **Conversion instincts.** CTAs, urgency, framing — where they go hard, where they refuse.
- **Brand voice codification.** Voice axes (serious↔playful, formal↔casual, reverent↔irreverent).
- **Banned words.** The list.
- **Dialogue with design.** How they work with visuals, where copy and design blend.
- **Heroes.** Writers / brands / ads they measure against.

Voice is hard to articulate but easy to recognize. End with a "write a headline for this fake product" and let them narrate their choices.

## Synthesis guardrails

- Capture **do/don't pairs** (preferred vs. avoided phrases).
- Include their **sentence-level taste**: rhythm preferences, sentence length variance, punctuation choices.
- Include at least 3 **before/after examples** they walk you through — edits narrate voice better than rules.
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never open an email that way", re-interview that section and re-render.
