---
name: ceet-product-manager
description: Use this skill to run the CEET interview that captures a product manager's own judgment (problem framing, prioritization, discovery, roadmaps, specs, success metrics, stakeholders, saying no) and turns it into a portable AI setup that drafts PRDs, triages requests and decides the way that person does. Use it when someone wants to be interviewed, re-profiled, or have a departing or senior PM's product sense cloned for use in any AI tool (Claude, ChatGPT, Cursor, Copilot, Gemini). Example phrases: "extract my PM thinking", "build an AI that writes PRDs like me", "capture how I prioritize". Do not use it for these: picking or comparing which CEET role fits someone (including hybrid roles such as technical PM plus engineering lead), writing a PRD or other PM deliverable directly, ranking or hiring PMs, or cloning non-PM roles such as analysts or engineers.
---

# CEET — Product Manager

## What this skill does

Interviews a product manager, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that frames problems, prioritizes, writes specs and handles stakeholders the way they do. The pack goes to the project
(`.harness/packs/product-manager-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that drafts PRDs, reviews specs, or triages feedback the way they would.
- A CPO wants to scale their judgment across a team of PMs with AI support.
- A founding PM wants their product sense captured before the team grows.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a product manager (a pack never serves evaluation, hiring or task allocation),
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

## PM-specific things to listen for

These are the cognitive signals that distinguish a senior product manager from a textbook one. Use them
as probes when the interview drifts generic:

- **Problem framing.** How they distinguish a real problem from a requested solution.
- **Prioritization system.** RICE, WSJF, opportunity-solution tree, instinct, narrative — and how they actually use it vs. say they use it.
- **Discovery habits.** User interviews cadence, assumption mapping, opportunity backlog.
- **Roadmap philosophy.** Dates vs. outcomes vs. themes. Commitment vs. direction.
- **Specs / PRDs.** Their template, what they include, what they refuse to include.
- **Success metrics.** How they define it *before* shipping. What counts as "this didn't work."
- **Stakeholder management.** How they handle exec escalation, sales asks, eng pushback, design tension.
- **Saying no.** Their script, their framing, their last-resort move.
- **Cross-functional partnerships.** How they work with eng lead, design lead, data, GTM.
- **Judgment calls.** Build vs. buy, feature vs. fix, polish vs. ship, vertical vs. horizontal.

The refusals and the kill stories carry more information than the ship stories. Probe those.

## Synthesis guardrails

- Capture their **prioritization procedure** step-by-step — this is the most reusable artifact for an AI.
- Include their **default PRD skeleton** verbatim if they have one.
- Preserve their **framing vocabulary** (problem statement vs. JTBD vs. opportunity, etc.).
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never put a date on that item", re-interview that section and re-render.
