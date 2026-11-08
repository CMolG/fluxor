---
name: ceet-financial
description: Use this skill to capture a finance operator's judgment (CFO, FP&A lead, controller, finance partner) through a consent-based interview and turn it into a portable AI profile that builds and reviews models, sets assumptions, forecasts, budgets, says no to spend, and drafts board memos the way they do. Trigger when the user wants to clone, extract, interview, or re-run the profile for a finance person, or to scale that person's finance thinking into any AI tool (Claude, ChatGPT, Cursor, Copilot, Gemini). Examples: "clone our CFO", "interview me about FP&A", "capture my forecasting playbook". Do not use for doing finance work directly (building models, ranking staff, job descriptions), for other roles' profiles, or for questions about which CEET role to pick. Founder fundraising and company strategy belong to ceet-founder-ceo.
---

# CEET — Finance

## What this skill does

Interviews a finance lead, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that builds models, sets assumptions, forecasts, budgets and says no to spend the way they do. The pack goes to the project
(`.harness/packs/financial-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that drafts board memos, financial models, or scenario analyses in their voice.
- A CFO wants their judgment scaled across an FP&A team.
- A founder wants finance instincts captured before hiring a CFO.
- The user wants a portable artifact they can reuse across AI tools.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a finance lead (a pack never serves evaluation, hiring or task allocation),
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

## Finance-specific things to listen for

These are the cognitive signals that distinguish a senior finance lead from a textbook one. Use them
as probes when the interview drifts generic:

- **Model taste.** Monolithic vs. modular, driver-based vs. line-item, opinions on circular references, color/format conventions.
- **Assumption discipline.** Where they justify, where they approximate, where they refuse to guess.
- **Unit economics frame.** CAC, payback, LTV, contribution margin — which they actually trust.
- **Forecasting method.** Bottoms-up vs. tops-down, sales-led forecast vs. FP&A forecast, variance tolerance.
- **Budgeting philosophy.** Zero-based, last-year-plus, OKR-tied.
- **Capital allocation.** ROI hurdles, payback bars, strategic exceptions.
- **Board / investor voice.** What they emphasize, what they refuse to hide.
- **Controls & close.** Non-negotiables in month-end close.
- **Scenario modeling.** How they build base / bull / bear, sensitivity tables.
- **Pricing support.** When they get involved in pricing and what they argue for.

If they can walk you through re-forecasting after a 20% miss live, you've got great extraction material.

## Synthesis guardrails

- Capture their **model conventions** (naming, color coding, sheet structure, units).
- Include their **top 5 forecasting assumptions** and where each one comes from.
- Preserve their **board-voice phrases** — finance memos have a specific register.
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
If they say "close, but I'd never put that assumption in without a source", re-interview that section and re-render.
