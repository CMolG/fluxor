# CEET — Copywriter

Interview a copywriter or UX writer and produce a portable AI environment that drafts and edits in their voice across marketing, product, and microcopy.

## Who this is for

- Brand / content leads codifying editorial voice for AI-assisted writing.
- Founding writers who want their taste available to the whole team via AI.
- Solo writers who want rules sharper than a one-page brand doc.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/copywriter-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the copywriter thinks, decides and speaks, and their best-evidenced rules.
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
up to an hour of optional depth modules. You can split it across sessions; the interview state resumes.

## How to install the output in your AI tool

Render the adapters (`render_pack.py render <pack> --adapter <tool>`) and install them; see
[`../ceet-core/references/tool-integration.md`](../ceet-core/references/tool-integration.md).

## What makes this CEET different from the others

Copywriting is dominated by *the sentence*: rhythm, the words banned and the words reached for, the persuasion moves refused even when they convert. The interview asks for sentences the person would and would never ship, and for real before/after edits, because edits narrate a voice better than rules. Where marketing decides who to reach and through which channel, this role decides what the words on the page say and how they sound.
