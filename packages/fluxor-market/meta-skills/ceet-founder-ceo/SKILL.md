---
name: ceet-founder-ceo
description: Cognitive Extraction Engine for founders and CEOs. Use whenever a user wants to "clone" an executive's judgment about strategy, capital and fundraising, attention, hiring, decisions under ambiguity, the board and the company's narrative, or build a personalized AI environment that drafts board updates, stress-tests strategy and plans their week the way they do. Trigger on phrases like "extract my founder thinking", "clone my CEO style", "build an AI that drafts board updates like me", "interview me about strategy", "capture my decision-making framework", or "make a founder cognitive clone". Not for a finance lead's models, forecasts and budgets (that is ceet-financial). Outputs are tool-agnostic (Claude, ChatGPT, Cursor, Copilot, Gemini, etc.).
---

# CEET — Founder / CEO

## What this skill does

Interviews a founder or CEO, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that sets strategy, allocates capital and attention, decides under ambiguity and tells the story the way they do. The pack goes to the project
(`.harness/packs/founder-ceo-<person>/`), never into this skill's folder.

## When to use

- The founder wants AI help with board updates, all-hands, investor emails, org decisions, and strategic memos in their own voice.
- A scaling org wants the founder's judgment made accessible to leaders via AI context.
- An incoming CEO wants to codify their working philosophy up front.
- The user wants a portable artifact they can reuse across AI tools.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a founder or CEO (a pack never serves evaluation, hiring or task allocation),
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

## Founder-specific things to listen for

These are the cognitive signals that distinguish a senior founder or CEO from a textbook one. Use them
as probes when the interview drifts generic:

- **Strategic frame.** The one-sentence theory of the business and how they stress-test it.
- **Capital allocation.** How they think about fundraising, dilution, runway, ROI on cash.
- **Attention allocation.** What they protect vs. delegate. How they manage their calendar.
- **Hiring bar.** What they hire on for the first 20 vs. 100 vs. 500 employees.
- **Narrative voice.** Board memo, investor update, customer email, all-hands — same person, different register.
- **Decision posture.** When they decide fast, when they wait, when they reverse.
- **Communication rituals.** How information flows up and down in their org.
- **Board relationship.** What they share, when, how they handle pressure.
- **Crisis reflexes.** What they do when things are on fire.
- **Personal operating system.** Calendar, journaling, reading, coaching.

The "hard call under ambiguity" narration is the single highest-signal answer in this entire interview.

## Synthesis guardrails

- Capture their **board update skeleton** verbatim if they have one.
- Include their **decision procedure for ambiguous calls** (e.g. "When I can't decide, I ask X, then Y, then commit").
- Preserve tone across audiences — investors, team, customers.
- Include the founder's **narrative style** — how they compress a quarter into two paragraphs.
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
If they say "close, but I'd never tell the board that before the team", re-interview that section and re-render.
