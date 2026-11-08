# CEET — Finance

Interview a CFO, FP&A lead, or finance partner and produce a portable AI environment that builds models, runs forecasts, drafts board memos, and evaluates unit economics in their style.

## Who this is for

- CFOs scaling their discipline across an FP&A team via AI.
- Founders capturing finance instincts before hiring a full-time CFO.
- Finance partners who want AI copilots that respect their assumptions discipline.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/financial-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the finance lead thinks, decides and speaks, and their best-evidenced rules.
- `cognitive-profile.md` / `.json` — the full cognitive clone, every directive traced to the questions it came from.
- `examples/` — real decisions with their rationale, retrieved into the task at hand.
- `agents/`, `skills/`, `commands/`, `rules/` — the AI environment rendered from the profile.
- `adapters/` — the same, in the native formats of Claude Code, Cursor, Copilot, `AGENTS.md` and Agent Skills.
- `private/` — the verbatim answers and a private reflection, never shared or committed.

## How to run it

If your AI tool supports Agent Skills, `SKILL.md` triggers on its own. Otherwise open `SKILL.md` and
`interview/questions.md` and walk through them as a guided interview. The form itself is data:
`interview/form.json`.

Time required: **about 70 minutes** for the core and the real decisions, plus
up to an hour and a quarter of optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

Finance is dominated by *what gets refused a number*: the assumption with no source, the spend below the bar, the metric not buried in the board memo. The interview asks for a real model walked end to end, a forecast that missed, and the mid-quarter call with half the facts, because a finance lead's judgment shows in how they re-forecast, not in the template they use. It does not assume a tool or a planning method: it records the ones the person trusts and where they bend them.
