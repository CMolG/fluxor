# CEET — Legal / Compliance

Interview an in-house counsel, compliance lead, DPO, or legal ops lead and produce a portable AI environment that does first-pass contract review, policy drafting, and risk triage in their style.

## Who this is for

- General counsels scaling first-pass review across product / sales partners via AI.
- Founders capturing legal instincts before bringing counsel in-house.
- Compliance leads standardizing how the company answers regulatory questions.

Never for evaluating, ranking, hiring or allocating work to the person profiled: those uses are
excluded by every pack's consent record.

## What you'll produce

A pack in your project (`.harness/packs/legal-compliance-<person>/` by default), never in this folder:

- `core.md` — the short always-on core: how the counsel or compliance lead thinks, decides and speaks, and their best-evidenced rules.
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

Outputs describe *how a person reasons* about legal and compliance issues. They are not, and must not be used as, legal advice. The generated AI environment carries a disclaimer, in the communication standards every artifact inherits, flagging that final decisions and matters outside the person's jurisdictions require human counsel.

## What makes this CEET different from the others

Legal work is dominated by *where the line sits*: the clause always pushed, the one always conceded, the matter that goes to outside counsel whatever its size. The interview asks for a real redline narrated clause by clause, a matter that went wrong, and a breach decided with half the facts, and it records the jurisdictions the person does and does not advise on. The pack reasons in their style and says so; it never presents itself as legal advice.
