---
name: ceet-marketing
description: Use this skill when a marketer (growth, brand, demand gen, product marketing) wants their own judgment on positioning, ICP, messaging, channels, funnels, budgets or attribution captured through an interview and turned into a personalized AI setup that plans campaigns and GTM the way they do. Typical asks: "extract my marketing thinking", "clone our head of growth", "interview me about positioning", "capture my growth playbook", "build an AI that plans campaigns like me", or re-running or continuing that interview. Do not use for general questions about the CEET framework or choosing among CEET roles, nor for writing voice or line editing (ceet-copywriter), ranking or evaluating marketers, or drafting ads and campaign copy. Output works with any AI tool.
---

# CEET — Marketing

## What this skill does

Interviews a marketer, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that positions, targets, picks channels and judges campaigns the way they do. The pack goes to the project
(`.harness/packs/marketing-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that drafts campaigns, briefs agencies, or plans GTM in their voice.
- A head of marketing wants to scale their playbook across team members and AI tools.
- A PMM wants narratives and launch plans drafted to their standards.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a marketer (a pack never serves evaluation, hiring or task allocation),
or cloning someone who is not in the conversation (that is `ceet-impersonator`, with its own rules).

## Run order

Follow the shared protocol in
[`../ceet-core/references/interview-protocol.md`](../ceet-core/references/interview-protocol.md);
the role's form is [`interview/form.json`](interview/form.json) (read as
[`interview/questions.md`](interview/questions.md)).

1. **Consent** before the first question (`interview.py statement`, then `interview.py start`).
2. **Held-out decisions**, if the person wants the clone's fidelity measured: 20–40 real past
   decisions set aside before the interview ([fidelity](../ceet-core/references/fidelity.md)).
3. **Core interview**, then **real decisions** (required), then the **depth modules** the person
   has time for; `interview.py next` picks the next question, `interview.py answer` records it verbatim.
4. **Synthesize** `cognitive-profile.json` following the
   [synthesis rules](../ceet-core/references/synthesis-rules.md), and the decisions into
   `examples/decisions.json`.
5. **Teachback**: the person accepts, edits or rejects every directive (`render_pack.py teachback`).
6. **Render** with `render_pack.py render <pack>`, show the person the dry run, then `--write`;
   `validate_pack.py` must pass. Offer the adapters for the tools they use.

## Marketing-specific things to listen for

These are the cognitive signals that distinguish a senior marketer from a textbook one. Use them
as probes when the interview drifts generic:

- **Positioning frame.** Category, alternative, ICP, unique value — which lens is dominant?
- **ICP rigor.** Who's in, who's explicitly out, what makes a bad-fit customer.
- **Channel philosophy.** Paid / organic / community / sales-led / PLG — their mix and why.
- **Funnel model.** AARRR, bowtie, jobs funnel, GTM partnership with sales.
- **Brand vs. demand.** How they split budget and attention. What they refuse to measure by ROI.
- **Attribution honesty.** What they actually believe vs. what they report to the board.
- **Creative bar.** What makes a great campaign, piece of content, event.
- **Growth loops.** Do they think in loops, funnels, or both?
- **Messaging hierarchy.** The one line, the three pillars, the taglines, and how they cascade.
- **Competitive stance.** How they position against alternatives without naming names.

The ICP refusals and the killed-campaign stories carry the most signal.

## Synthesis guardrails

- Separate **positioning statements** from **messaging pillars** from **campaign headlines**. The AI should know the level it's writing at.
- Capture their **ICP refusals** (who they don't sell to) — often more revealing than the ICP they claim.
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never sell to that customer", re-interview that section and re-render.
