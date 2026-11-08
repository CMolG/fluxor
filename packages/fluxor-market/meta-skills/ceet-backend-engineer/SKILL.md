---
name: ceet-backend-engineer
description: Cognitive Extraction Engine for backend engineers. Use whenever a user wants to "clone" a backend engineer's judgment, capture how a senior server/API/data engineer thinks, build a personalized AI coding environment for backend work, or produce a portable cognitive profile of a backend practitioner. Trigger on phrases like "extract my backend style", "build an AI setup that codes like our staff backend engineer", "interview me about backend engineering", "make me a backend cognitive clone", or any request to distill backend engineering judgment into a reusable AI configuration. Outputs are tool-agnostic (Claude, ChatGPT, Cursor, Copilot, Gemini, etc.).
---

# CEET — Backend Engineer

## What this skill does

Interviews a backend engineer, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands, rules and hooks rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The pack goes to the project (`.harness/packs/backend-engineer-<person>/`),
never into this skill's folder.

## When to use

- The user says "build a backend cognitive clone", "extract how I think about backend", or "interview
  me so any AI can code like me".
- The user wants an AI assistant to work on their backend codebase in *their* style, not a generic one.
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

## Backend-specific things to listen for

These are the cognitive signals that distinguish a senior backend engineer from a textbook one. Use
them as probes when the interview drifts generic:

- **Data integrity instincts.** Uniqueness, ordering, idempotency, exactly-once vs at-least-once
  thinking. How do they design for partial failure?
- **Blast radius thinking.** When they ship, what's their mental map of *what else could break*?
- **Invariant mindset.** Do they name invariants explicitly? Where do they enforce them (DB, app, queue)?
- **Latency vs consistency tradeoffs.** Concrete examples of when they picked each.
- **API shape judgment.** REST vs RPC vs event-driven — when and why. Versioning philosophy.
- **Storage choice heuristics.** Postgres vs Dynamo vs Kafka vs S3 — their mental decision tree.
- **Observability reflexes.** What do they instrument before deploying? What metric do they watch after?
- **Refactoring taste.** When they say "this needs a refactor," what's the signal?
- **Review lens.** What do they flag in other people's PRs?
- **Incident scar tissue.** Every senior backend engineer has 2-3 incidents that permanently changed
  how they code. The real-decisions module asks for them; get the cues, not only the story.

## Synthesis guardrails

- Keep the person's **own vocabulary**. If they say "poison message" instead of "bad event", the
  clone says "poison message".
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Quote specific examples inline — "rejects PRs that mutate args without a `_mut` suffix" beats
  "prefers immutability".
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a commit message pattern, a banned construct) also goes
  into `checks` with the question it came from, so it can run as a hook once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never say X that way," re-interview that section and re-render.
