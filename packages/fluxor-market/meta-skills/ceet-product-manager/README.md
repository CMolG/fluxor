# CEET — Product Manager

Interview a PM and produce a portable AI environment that drafts specs, triages feedback, prioritizes, and communicates trade-offs in their style.

## Who this is for

- Heads of product scaling their judgment across a team.
- Founding PMs capturing their product sense before onboarding others.
- Solo PMs who want an AI thinking partner aligned with their priorities.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/product-manager-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the product manager thinks, decides and speaks, and their best-evidenced rules.
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

Product management is dominated by *what gets refused*: the feature killed, the date not promised, the sales ask declined. The interview asks for the person's real prioritization — not the framework they would post — and for real specs and kill decisions, because a PM's judgment shows in the trade-offs they made, not in the process they describe. It does not assume RICE, OKRs or any framework: it records the one the person actually uses, and where they bend it.
