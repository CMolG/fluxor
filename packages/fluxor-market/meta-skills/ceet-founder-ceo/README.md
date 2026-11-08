# CEET — Founder / CEO

Interview a founder or CEO and produce a portable AI environment that drafts board updates, all-hands notes, investor emails, and strategic memos in their voice — and reasons about strategy, capital, and org in their style.

## Who this is for

- Founders who want an AI chief-of-staff that sounds like them.
- Scaling leaders making their judgment accessible to the layer below them via AI context.
- New CEOs codifying their operating philosophy up front.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/founder-ceo-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the founder or CEO thinks, decides and speaks, and their best-evidenced rules.
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
up to an hour and a half of optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

Leading a company is dominated by *what the person refuses to trade*: the round turned down, the task never delegated, the story not told even when it is true. The interview asks for the hard call made under ambiguity, a crisis led end to end, and a real board update reworked live, because a founder's judgment shows in the calls nobody else could make. Where finance decides whether the numbers hold, this role decides what the company bets on and how it says so.
