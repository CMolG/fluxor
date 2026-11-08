---
name: ceet-data-analytics
description: Use this skill to interview a data scientist, analytics engineer, or data analyst and capture how they think, so an AI can reproduce their judgment: question framing, metric design, experiment and causal reasoning, uncertainty language, SQL/Python/dbt conventions. Applies when the person wants a portable "cognitive clone" or profile of their own analytics approach, or wants to run, resume, or re-run that interview. Not for doing analysis itself, general style guides, hiring or ranking analysts, cloning non-data roles (engineers, ML engineers, ops), or choosing between roles.
---

# CEET — Data / Analytics

## What this skill does

Interviews a data practitioner (data scientist, analytics engineer, analyst), with their consent,
and turns the answers into a **pack**: their cognitive profile, a short always-on core, their real
decisions as examples, and the agents, skills, commands and rules rendered from the profile, with
adapters for Claude Code, Cursor, Copilot, `AGENTS.md` and Agent Skills. The pack goes to the
project (`.harness/packs/data-analytics-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI collaborator that writes SQL, dbt or notebook code with *their* conventions
  and *their* statistical rigor.
- The user wants their metric design and experimentation discipline captured once and applied by
  any AI tool.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking an analyst (a pack never serves evaluation, hiring or task allocation),
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

## Data-specific things to listen for

These are the cognitive signals that distinguish a senior data practitioner from a textbook one.
Use them as probes when the interview drifts generic:

- **Question framing.** How they turn "what's going on with X" into a tractable question, and which
  requests they reframe before touching data.
- **Metric design.** What makes a metric good to them: stability, gaming resistance, leading vs. lagging.
- **Causal thinking.** RCT, diff-in-diff, synthetic control, observational: what they reach for and when.
- **Confidence and honesty.** How they communicate uncertainty, and what they refuse to claim.
- **Data quality reflexes.** What they check before trusting a table, and how they smell a bad join.
- **Modeling taste.** Simple vs. complex, and their bar for "good enough".
- **Experimentation discipline.** Power, MDE, guardrails, peeking, multiple comparisons.
- **Workflow and tools.** Notebooks vs. scripts vs. dbt; SQL dialect, dataframe and viz libraries.
- **Stakeholder translation.** How they narrate numbers to non-technical audiences, and what they
  say when asked for "just the number".
- **The worked example.** Data judgment is example-driven; the real-decisions module walks through
  a real analysis. Get every branch they rejected, not only the path they took.

## Synthesis guardrails

- Keep the person's **own vocabulary** and their metric-naming conventions (snake_case, domain
  prefixes) exactly as stated.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Uncertainty language goes in verbatim: the words they avoid ("proves", "causes") matter as much as
  the ones they use.
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned SQL construct, a naming pattern) also goes into
  `checks` with the question it came from.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never call that significant," re-interview that section and re-render.
