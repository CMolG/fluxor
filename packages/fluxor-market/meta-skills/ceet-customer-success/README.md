# CEET — Customer Success

Interview a CSM or CS leader and produce a portable AI environment that drafts onboarding plans, QBRs, at-risk playbooks, and renewal / expansion motions in their style.

## Who this is for

- CS leaders scaling a top CSM's judgment across the team.
- Founder-CSMs capturing retention instincts before CS hires start.
- Account managers who want an AI copilot that matches their voice.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/customer-success-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the customer success manager thinks, decides and speaks, and their best-evidenced rules.
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

Customer success is dominated by *signals the dashboard misses*: the green account that churned, the champion who left, the renewal shrinking quietly. The interview asks for a real save and a real expansion, a live rework of the person's own QBR, and the renewal decided with half the facts. Where sales decides who to win, this role decides how a customer gets value, stays and grows, and who not to upsell.
