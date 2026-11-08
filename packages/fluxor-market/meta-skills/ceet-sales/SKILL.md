---
name: ceet-sales
description: Use this skill to run the CEET interview with a salesperson (AE, rep, sales leader, solutions consultant) so an AI can reproduce their own selling judgment: qualification, discovery, objections, negotiation, champions, forecasting, outreach voice. The person being cloned must be a seller who is in the conversation, or an agreed top rep being interviewed. Typical requests: "extract my sales thinking", "clone our top AE", "build an AI that drafts outreach like me", "capture my objection playbook", "re-run my sales profile". Do not use it for other roles, such as pricing analysts, finance, customer success (renewals, churn, QBRs: ceet-customer-success), or marketing. Also do not use it for choosing which CEET role fits someone, for ranking or evaluating sellers, or for one-off sales writing and coaching without a clone. Outputs work with any AI tool.
---

# CEET — Sales

## What this skill does

Interviews a seller, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that qualifies, runs discovery, handles objections, negotiates and forecasts the way they do. The pack goes to the project
(`.harness/packs/sales-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI that writes emails / follow-ups / proposals in their voice, with their judgment about what to say to whom.
- A sales leader wants a top rep's pattern captured and scaled via AI.
- A founder-seller wants their discovery style preserved as hiring starts.
- The user wants a portable artifact they can reuse across AI tools.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a seller (a pack never serves evaluation, hiring or task allocation),
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

## Sales-specific things to listen for

These are the cognitive signals that distinguish a senior seller from a textbook one. Use them
as probes when the interview drifts generic:

- **ICP & qualification.** Their actual bar, how they disqualify fast, what they refuse to chase.
- **Discovery style.** The questions they always ask, what they listen for, how they avoid demo-leading.
- **Methodology.** MEDDICC / SPICED / Challenger / Sandler — what they use and how they customized it.
- **Objection patterns.** The 5-10 recurring objections and their responses (verbatim if possible).
- **Pricing & negotiation.** Anchor behavior, discount ladder, trade behavior.
- **Forecasting discipline.** What they count as committed vs. best-case.
- **Email / outreach voice.** Length, openers, subject lines, follow-up cadence.
- **Multi-threading instincts.** How and when they bring in exec / champion / economic buyer.
- **Handoff to CS.** What they tell the CS team, what they refuse to promise.
- **Losing posture.** What they do when a deal is slipping. What they refuse to do.

The lost deal narration is usually where the sharpest heuristics live.

## Synthesis guardrails

- Capture their **discovery question set** verbatim.
- Include their **objection library** as do/say/don't-say triplets.
- Preserve **email voice** — short / long, signature, sign-off, reply patterns.
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd never discount before they've agreed on value", re-interview that section and re-render.
