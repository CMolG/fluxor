# CEET — Marketing

Interview a marketer (growth, brand, demand-gen, PMM) and produce a portable AI environment that plans campaigns, drafts positioning, and briefs agencies in their style.

## Who this is for

- Heads of marketing scaling their playbook with AI.
- Founding marketers codifying GTM judgment before the team grows.
- PMM / growth leads who want AI partners that respect their bar.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/marketing-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the marketer thinks, decides and speaks, and their best-evidenced rules.
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

Marketing is dominated by *who is out* and *what is believed*: the customers pushed away, the channels killed, and the gap between the attribution reported to the board and the one the person trusts. The interview asks for those refusals and for a real campaign end to end. Where the copywriter decides how the words sound, this role decides who to reach, with what promise, through which channel, and how to tell whether it worked.
