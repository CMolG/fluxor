# CEET — Data / Analytics

Interview a data practitioner, extract their cognitive patterns, and produce a portable AI environment that frames questions, writes queries and reports results their way — in any AI tool.

## Who this is for

- **Senior analysts, analytics engineers and data scientists** who want an AI collaborator that applies their statistical rigor and conventions instead of generic defaults.
- **Data leads** who choose to share their metric and experimentation standards through an AI assistant, with their consent.
- **Teams** that want one reusable artifact for "how we treat data here".

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/data-analytics-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the analyst thinks, decides and speaks, and their best-evidenced rules.
- `cognitive-profile.md` / `.json` — the full cognitive clone, every directive traced to the questions it came from.
- `examples/` — real decisions with their rationale, retrieved into the task at hand.
- `agents/`, `skills/`, `commands/`, `rules/` — the AI environment rendered from the profile.
- `adapters/` — the same, in the native formats of Claude Code, Cursor, Copilot, `AGENTS.md` and Agent Skills.
- `private/` — the verbatim answers and a private reflection, never shared or committed.

## How to run it

If your AI tool supports Agent Skills, `SKILL.md` triggers on its own. Otherwise open `SKILL.md` and
`interview/questions.md` and walk through them as a guided interview. The form itself is data:
`interview/form.json`.

Time required: **about 75 minutes** for the core and the real decisions, plus about an hour of
optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

Data work is dominated by *question framing*, *trust in the data* and *honesty about uncertainty*.
The interview starts with how the person reshapes a vague request and what they refuse to answer as
asked, and its required time goes to a real analysis walked end to end — every branch rejected —
because data judgment is carried by worked examples more than by rules.
