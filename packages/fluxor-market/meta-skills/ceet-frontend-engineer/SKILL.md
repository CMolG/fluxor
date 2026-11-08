---
name: ceet-frontend-engineer
description: Cognitive Extraction Engine for frontend engineers. Use whenever a user wants to "clone" a frontend engineer's judgment about UI architecture, rendering, state, accessibility and client-side performance, or build a personalized AI environment for frontend work that mirrors their taste and heuristics. Trigger on phrases like "extract my frontend style", "build an AI setup that writes components like me", "interview me about frontend engineering", "make a React/Vue/Svelte cognitive clone", "capture how I think about UI state", or any request to distill frontend judgment into a reusable AI configuration. Outputs are tool-agnostic (Claude, ChatGPT, Cursor, Copilot, Gemini, etc.).
---

# CEET — Frontend Engineer

## What this skill does

Interviews a frontend engineer, with their consent, and turns the answers into a **pack**: their
cognitive profile, a short always-on core, their real decisions as examples, and the agents, skills,
commands, rules and hooks rendered from the profile, with adapters for Claude Code, Cursor, Copilot,
`AGENTS.md` and Agent Skills. The pack goes to the project (`.harness/packs/frontend-engineer-<person>/`),
never into this skill's folder.

## When to use

- The user says "build a frontend cognitive clone", "extract how I build UI", or "interview me so any
  AI writes components like me".
- The user wants an AI that writes components, styles and interactions in *their* style, not generic
  React/Vue/Svelte boilerplate.
- The user wants a portable artifact they can reuse across AI tools.

Not for: judging or ranking an engineer (a pack never serves evaluation, hiring or task allocation),
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

## Frontend-specific things to listen for

These are the cognitive signals that distinguish a senior frontend engineer from a textbook one. Use
them as probes when the interview drifts generic:

- **State philosophy.** Local vs. lifted vs. global; when they reach for a store and when they refuse;
  the URL as state; server state vs. client state.
- **Component boundaries.** What makes a component "too big", and how they factor it.
- **Rendering mental model.** SSR / SSG / CSR / streaming / islands: when each, and why. Where
  hydration has bitten them.
- **Accessibility reflexes.** Do they think keyboard-first? What do they audit before shipping?
- **Styling philosophy.** Utility classes, CSS modules, CSS-in-JS, tokens, and the taste behind the choice.
- **Performance instincts.** Which Web Vital they chase first, which bundle patterns they distrust,
  and whether they measure before they memoize.
- **States and forms.** Do they design empty, loading, error and success, or only two? Where does
  validation live, and how do they design error states?
- **Motion.** Where they are subtle, where bold, what they refuse to animate, how they treat reduced motion.
- **Testing mix.** Unit vs. component vs. E2E vs. visual regression, and what they refuse to mock.
- **Taste by example.** Frontend judgment comes out through sites and components they admire or
  distrust; ask for them, and for the detail that makes the difference.

## Synthesis guardrails

- Keep the person's **own vocabulary**. If they call a styled primitive a "brick" or a "motif", the
  clone says so.
- Frontend taste is often *negative*: what they refuse to ship. Capture those anti-patterns verbatim.
- Distinguish **heuristics** (rules with exceptions) from **anti-patterns** (never do X).
- Accessibility: don't let them hand-wave. Record keyboard paths, focus handling and label
  conventions as they state them.
- Record contradictions in `contradictions`; they stay in the profile, out of task prompts.
- A rule stated precisely enough to check (a commit message pattern, a banned import) also goes into
  `checks` with the question it came from, so it can run as a hook once its bench is green.

## When to stop

The interview is complete when the person reads the teachback and says "yes, that is how I work."
If they say "close, but I'd structure that component with X, not Y," re-interview that section and
re-render.
