# CEET — Sales

Interview a sales professional and produce a portable AI environment that drafts outreach, discovery questions, objection responses, and proposals in their style.

## Who this is for

- Sales leaders capturing a top rep's playbook and scaling it.
- Founder-sellers who want their discovery style preserved as the team grows.
- AEs / AMs who want AI copilots that match their voice.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/sales-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the seller thinks, decides and speaks, and their best-evidenced rules.
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

Sales is dominated by *what gets walked away from*: the deal disqualified, the discount refused, the commit pulled from the forecast. The interview asks for a real won deal and a real lost one, a live rewrite of the person's own outreach, and the quarter-end call with half the facts, because a seller's judgment shows under pressure, not in the methodology they name. It does not assume MEDDICC or any framework: it records the one the person uses and the parts they ignore.
