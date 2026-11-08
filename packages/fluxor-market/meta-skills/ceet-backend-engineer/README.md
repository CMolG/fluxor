# CEET — Backend Engineer

Interview a backend engineer, extract their cognitive patterns, and produce a portable AI environment that codes in their style — in any AI tool.

## Who this is for

- **Staff / senior backend engineers** who want an AI assistant that matches their judgment instead of defaulting to generic patterns.
- **Teams** where an engineer chooses to share their review standards through an AI assistant, with their consent.
- **Founders / tech leads** onboarding contractors or junior engineers, who want a reusable "this is how we think about backend" artifact.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/backend-engineer-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the engineer thinks, decides and speaks, and their best-evidenced rules.
- `cognitive-profile.md` / `.json` — the full cognitive clone, every directive traced to the questions it came from.
- `examples/` — real decisions with their rationale, retrieved into the task at hand.
- `agents/`, `skills/`, `commands/`, `rules/`, `hooks/` — the AI environment rendered from the profile; the
  mechanical part of the hooks runs as checks (`hooks/checks.json`, `bin/ceet_check.py`).
- `adapters/` — the same, in the native formats of Claude Code, Cursor, Copilot, `AGENTS.md` and Agent Skills.
- `private/` — the verbatim answers and a private reflection, never shared or committed.

## How to run it

If your AI tool supports Agent Skills, `SKILL.md` triggers on its own. Otherwise open `SKILL.md` and
`interview/questions.md` and walk through them as a guided interview. The form itself is data:
`interview/form.json`.

Time required: **about 70 minutes** for the core and the real decisions, plus up to three hours of
optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

Backend engineering is dominated by *invariant thinking*, *failure-mode awareness*, and *blast-radius reasoning*. The interview questions in this CEET are tuned to surface those specifically — not the more visual/structural concerns of frontend, nor the infrastructure concerns of SRE, nor the metric-first concerns of data.
