---
name: ceet-people-ops
description: Cognitive Extraction Engine for People and HR leaders: hiring, performance, comp, culture and policy design. Use whenever a user wants to "clone" a People leader's judgment about hiring bars, interview rubrics, leveling, performance processes, difficult conversations and policy, or build a personalized AI environment that drafts rubrics, policies and conversation plans in their style. Trigger on phrases like "extract my people ops thinking", "clone our head of people", "build an AI that drafts review templates like me", "interview me about culture", "capture my hiring rubric", or "make a people-ops cognitive clone". Never for evaluating, scoring or ranking candidates or employees. Outputs are tool-agnostic (Claude, ChatGPT, Cursor, Copilot, Gemini, etc.).
---

# CEET — People Ops / HR

> **Note:** The outputs of this CEET describe *one person's reasoning* about People practices; they are not HR, employment-law or compliance advice. A pack **never evaluates employees or candidates**: it drafts and reviews processes, documents and conversations, and never scores, ranks or recommends a hiring, pay, promotion, performance-plan or termination decision about a person. That use would make it a high-risk AI system under the EU AI Act (Annex III, employment). Every pack states both boundaries in its communication standards, which every agent, skill and command inherits.

## What this skill does

Interviews a People leader, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that designs hiring loops, rubrics, performance processes, policies and hard conversations the way they do. The pack goes to the project
(`.harness/packs/people-ops-<person>/`), never into this skill's folder.

## When to use

- The user wants AI help with job descriptions, rubrics, review templates, conversation plans and policy drafts, in their voice.
- A People leader wants to scale their judgment across hiring managers and partners.
- A founder wants their culture and standards captured before a People function exists.
- The user wants a portable artifact they can reuse across AI tools.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a People leader (a pack never serves evaluation, hiring or task allocation),
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

## People-Ops-specific things to listen for

These are the cognitive signals that distinguish a senior People leader from a textbook one. Use them
as probes when the interview drifts generic:

- **Hiring bar.** What they hire on, what they refuse to compromise on.
- **Rubric design.** Signal vs. noise in interviews. Scorecard discipline.
- **Leveling & comp.** Framework, bands, transparency stance.
- **Performance philosophy.** Continuous feedback, formal reviews, calibration, ratings vs. narratives.
- **PIP stance.** When, how, and what they refuse to do.
- **Difficult conversations.** Framing, openers, preparation.
- **Culture diagnosis.** How they read a team — signals, not surveys.
- **Policy voice.** Formal, warm, terse, example-rich?
- **Org design.** Span of control, layers, when to split a team.
- **DEI posture.** What they measure, what they refuse to reduce to metrics.

How they narrate the departure is usually where the real values show.

## Synthesis guardrails

- Capture their **interview rubric** structure verbatim if they have one.
- Include their **performance review template** or skeleton.
- Preserve the **tone** they use in sensitive written communication.
- Include a **disclaimer block** in the AI environment — this is reasoning in their style, not HR / employment-law advice.
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
If they say "close, but I'd never start a performance plan without written feedback", re-interview that section and re-render.
