# CEET — People Ops / HR

Interview a People leader and produce a portable AI environment that drafts job descriptions, rubrics, review templates, conversation plans and policy in their style.

## Who this is for

- Heads of People scaling hiring and performance standards across managers.
- Founders capturing their culture bar before a People function exists.
- People partners who want AI copilots that match their tone.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/people-ops-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the People leader thinks, decides and speaks, and their best-evidenced rules.
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

## Important disclaimer

Outputs describe *how a person reasons* about People practices. They are not HR, employment-law or compliance advice, and sensitive decisions go through qualified counsel and leadership. The generated AI environment never evaluates, scores or ranks a candidate or an employee, and never recommends a decision about one: it works on processes, documents and conversations. Using it to evaluate people would make it a high-risk AI system under the EU AI Act, and it is not built or offered for that.

## What makes this CEET different from the others

People work is dominated by *fairness under pressure*: the hire the person blocked against the room, the performance plan they refused to run, the words they ban in a hard conversation. The interview asks for a departure handled well, a live rework of their own rubric, and a termination request decided with half the facts, all without naming anyone. The pack helps design and write; it never judges a person.
