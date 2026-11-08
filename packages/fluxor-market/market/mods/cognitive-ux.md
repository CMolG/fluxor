# cognitive-ux: Cognitive Load & Interface Psychology Modifier

When this modifier is active, every user-visible change is designed and reviewed under the
project's interface-psychology and value-clarity rules if the harness has them (e.g.
`.harness/rules/interface-psychology.md` and `.harness/rules/value-clarity.md`). If the session
offers the `ux-psychology` skill, it MUST be loaded before designing or auditing the surface — the
rules below remain sufficient without it, but the skill carries the full protocol and the friction
scanner.

## Rules

1. **Extraneous-load budget ≈ 0.** Every element on screen must support a step of the user's
   task. For each element you add or keep, you can name that step; if you cannot, it is debt and
   it goes. ≤4 items the user must hold at once, one primary decision per screen.
2. **All mandatory states exist.** Initial, empty (with the first action suggested), loading
   (with semantics, not a mute spinner), success (anchored to the affected object), error (what
   happened, why, and the way out), and disabled (always with the reason visible). A surface
   missing empty or error states is half-built, whatever the happy path looks like.
3. **No dead controls, no silent actions.** Anything painted as pressable does something, and
   every action yields perceptible feedback in ≤100 ms.
4. **Friction is classified in writing.** Each point of friction is extrinsic (remove it),
   desirable (keep it and justify it: irreversibility, cost, learning), or dark (prohibited —
   DSA/GDPR exposure). "Here there is NO confirmation because the action is reversible and undo
   exists" is valid documentation; write it.
5. **Symmetry of entry and exit.** Cancelling, unsubscribing, or deleting costs no more steps
   than the opposite action. Reversible actions get undo, not confirmation dialogs; irreversible
   ones get a deliberate micro-limit proportional to the damage.
6. **Plain language, congruent verbs.** The button's verb appears literally in the resulting
   screen; value is stated before mechanism; internal jargon never reaches the user. Color is
   never the only channel, and controls do not move between views without a written reason.

## Behavioral Overrides

- Before declaring a user-visible change done, the agent walks the project's interface-psychology
  checks (or, when the project has none, the six rules above) and reports findings as mechanism +
  concrete fix, never as vague adjectives.
- If a requested change ADDS friction, the agent runs the friction decision tree and records the
  decision in the deliverable (card, plan, or commit body).
- Stacks cleanly with `error-ux` (surface-level async states) and `a11y-enforcer` (WCAG); it does
  not overlap the design-system mods or an art-direction contract — those govern how a piece
  LOOKS, this mod governs what is shown, in what order, with how much friction, and with which
  words.
