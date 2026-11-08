# CEET — UI Designer

Interview a UI / product designer and produce a portable AI environment that critiques mocks, proposes components, and writes rationale in their visual voice.

## Who this is for

- Design leads scaling their taste across a team via AI.
- Founding designers capturing house style before the team grows.
- Design-engineering hybrids who want AI that matches their system.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/ui-designer-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the UI designer thinks, decides and speaks, and their best-evidenced rules.
- `cognitive-profile.md` / `.json` — the full cognitive clone, every directive traced to the questions it came from.
- `examples/` — real decisions with their rationale, retrieved into the task at hand.
- `agents/`, `skills/`, `commands/`, `rules/` — the AI environment rendered from the profile.
- `adapters/` — the same, in the native formats of Claude Code, Cursor, Copilot, `AGENTS.md` and Agent Skills.
- `private/` — the verbatim answers and a private reflection, never shared or committed.

## How to run it

If your AI tool supports Agent Skills, `SKILL.md` triggers on its own. Otherwise open `SKILL.md` and
`interview/questions.md` and walk through them as a guided interview. The form itself is data:
`interview/form.json`.

Time required: **about 75 minutes** for the core and the real decisions, plus
up to an hour and a quarter of optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

UI design is dominated by *taste*, and taste is mostly shown, not stated: the products admired, the screen called near-perfect, the variant rejected. The interview asks for named exemplars, a real piece of work and a live contrast, and records the person's critique vocabulary verbatim. It does not assume Figma or any design system: it records the numbers the person works in — baseline unit, type scale, contrast bar — and where they let the system bend.
