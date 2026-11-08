# CEET — DevOps / SRE

Interview a platform, infrastructure or reliability engineer, extract their cognitive patterns, and produce a portable AI environment that reviews changes, runs incidents and writes postmortems their way — in any AI tool.

## Who this is for

- **Senior SREs and platform engineers** who want an AI assistant that reviews Terraform, Kubernetes and pipeline changes with their standards, not generic best practice.
- **On-call leads** who choose to share their incident-response and postmortem voice through an AI assistant, with their consent.
- **Teams** that want a reusable "how our platform team thinks" artifact for AI assistants.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/devops-sre-<person>/` by default), never in this folder:

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

Time required: **about 75 minutes** for the core and the real decisions, plus a bit over an hour of
optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

SRE judgment is shaped by incidents more than by any other experience. The interview spends its
required time on real ones — the first cues, the options ruled out, the call to roll back — and on a
mock page with deliberately partial information, because those narrations encode more heuristics
than scripted questions. Its directives are about error budgets, page-versus-ticket, blast radius and
change management, not the code-level concerns of the backend or frontend roles.
