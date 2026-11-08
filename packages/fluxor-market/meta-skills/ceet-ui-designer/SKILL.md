---
name: ceet-ui-designer
description: Use this skill to interview a UI/visual product designer (with their consent) and turn their taste, judgment and critique voice into a portable AI "clone" pack that reviews mocks, proposes component variants and writes design rationale as they would. Covers visual system, type, color, motion and craft. Use for requests like "extract my design taste", "clone our UI designer", "interview me about visual design", "capture my design system philosophy", or re-running/continuing that designer interview. Works with any AI tool (Claude, ChatGPT, Cursor, Copilot, Gemini). Not for general design work (layouts, mockups), judging or ranking designers, hiring materials, other roles (engineers, marketers), or questions about choosing which CEET role to use.
---

# CEET — UI Designer

## What this skill does

Interviews a UI designer, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands and rules rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The result is an AI that critiques, systematizes and crafts interfaces the way they do. The pack goes to the project
(`.harness/packs/ui-designer-<person>/`), never into this skill's folder.

## When to use

- The user wants an AI critique partner that matches their visual taste.
- A design lead wants to codify house style and scale it via AI.
- A founding designer wants their taste captured before the team scales.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking a UI designer (a pack never serves evaluation, hiring or task allocation),
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

## UI-specific things to listen for

These are the cognitive signals that distinguish a senior UI designer from a textbook one. Use them
as probes when the interview drifts generic:

- **Grid & spacing taste.** 4pt / 8pt systems, tight vs. airy, ratio preferences.
- **Type systems.** Type scale, weights, line-height convictions, serif/sans preferences for context.
- **Color philosophy.** Saturated vs. desaturated, neutral ramps, semantic tokens, contrast bar.
- **Components.** What primitive does the system start from? How far do they build up before stopping?
- **Motion.** Where to add, where to resist, easing and duration defaults, reduced motion stance.
- **Craft details.** Focus states, hover states, loading states, empty states — which do they obsess over.
- **Icon & illustration taste.** Style, grid, line weight, illustration role.
- **Brand vs. usability.** Where do they let brand win? Where do they refuse?
- **Critique voice.** How do they give feedback? What words do they reach for?
- **Figma / tooling discipline.** Naming, auto-layout, variables, libraries, components vs. assets.

If you can, have them critique a public product's specific screen live. The way they talk about what's wrong is gold.

## Synthesis guardrails

- UI taste is best captured through **named exemplars** — products, sites, designers they respect. Include them.
- Capture the **critique vocabulary** verbatim ("this feels heavy", "the rhythm's off", "it's too polite").
- Include their token/naming conventions if any.
- Keep the person's **own vocabulary**: the clone uses their words, not the field's.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a banned phrase, a required section) also goes into
  `checks` with the question it came from, so it can run as a check once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but that spacing would feel heavy to me", re-interview that section and re-render.
