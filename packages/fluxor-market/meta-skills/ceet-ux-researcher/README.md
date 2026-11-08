# CEET — UX Researcher

Interview a UX researcher focused on user behavior and produce a portable AI environment that drafts research plans, interview guides, and synthesis artifacts in their style.

## Who this is for

- Research leads scaling rigor across PM-, design-, and AI-led research.
- Solo researchers codifying their craft for team reuse.
- Design-research hybrids who want AI help that respects behavioral method.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/ux-researcher-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the UX researcher thinks, decides and speaks, and their best-evidenced rules.
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

UX research is dominated by *evidence discipline*: what counts as a finding, how many sessions a claim needs, and when what people say outweighs what they do. The interview asks for a real study and a real readout, because a researcher's judgment shows in what they left out and softened, not in the methods they list. It does not assume a toolkit: it records the methods the person trusts and the ones they distrust.
