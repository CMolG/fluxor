---
name: ux-psychology
description: >-
  Analyzes and designs interfaces using cognitive psychology and neuroscience: cognitive load
  (intrinsic/extraneous/germane), the gulfs of execution and evaluation, the Fogg Behavior Model
  (B=MAP), processing fluency and trust, the ventral/dorsal visual pathways, the aesthetic-usability
  effect, dark patterns vs. desirable difficulties, cognitive accessibility (COGA/WCAG 2.2) and
  DSA/GDPR compliance. Use it ALWAYS when designing, reviewing, simplifying or refactoring any
  component, flow or screen (forms, onboarding, checkout, sign-up and cancellation, consent banners,
  modals, notifications, tables, dashboards, destructive actions or AI/LLM interfaces); when the
  conversation turns to conversion, drop-off, friction, trust, "make it easier to understand",
  "simplify the UI", button copy, loading or error states or visual hierarchy; or when dark patterns
  or regulatory risk are suspected. Apply it even if nobody mentions psychology, UX, cognition or
  neuroscience.
---

# Psychology applied to UX/UI design

The brain is a prediction engine that minimizes metabolic cost: it checks every stimulus against
its internal models and penalizes whatever doesn't fit. Hence the governing rule of this skill:

> **Every element of an interface is paid for with the user's mental energy. If it doesn't serve
> their task, it's debt.** And an interface is judged not only by what it shows, but by the mental
> work it forces on people and by whether it respects the autonomy of whoever uses it.

This skill decides **what is shown, in what order, with how much friction and in what words**.
It complements, and does not replace, whatever performance/SEO-audit, visual-direction and
UI-review skills are installed; if none is, it still covers everything above on its own.

Script paths are relative to this skill's directory. The scanner needs only the Python standard
library.

## How to use this skill

1. **Identify the working mode:**
   - **Design** a new component or flow → *Design protocol*.
   - **Analyze/audit** something that exists (code, screenshot, description, Figma) → *Analysis protocol*.
   - **Rule on** a specific decision ("should this have a confirmation?", "should I shorten the
     form?") → *Friction decision tree*.
2. **Apply the invariants first.** They are boundary conditions, not suggestions: a broken
   invariant is a blocking finding even if the design is gorgeous and converts well.
3. **Load the detail you need:**
   - `references/cognitive-frameworks.md`: the mechanisms (CLT, Norman's gulfs, Fogg, fluency,
     ventral/dorsal, aesthetic-usability, cognitive offloading) and what each implies for the UI.
     Read it when you need to justify *why* something fails.
   - `references/component-catalog.md`: one entry per component type (forms, navigation, consent,
     cancellation, checkout, destructive actions, notifications, states, AI/LLM, tables, learning).
     Read it **every time** you work on one of them.
   - `references/audit-and-metrics.md`: how to measure without neurotechnology, what EEG/TAR,
     pupillometry (TEPR) and ERPs contribute, and why most "neuro" conclusions are invalid.
   - `references/regulation-and-ethics.md`: DSA, GDPR (including neurodata), COGA/WCAG 2.2,
     cognitive debt.
   - `assets/worksheet-templates.md`: complete output templates.
4. **Deliver in the worksheet format** (below). No vague judgments: every finding carries a
   mechanism, evidence, severity, a proposed change and a way to verify it.

**Precedence when things conflict:** invariants > cognitive accessibility > levers > aesthetics >
short-term business metric. If a lever collides with an invariant, the invariant wins.

## Invariants (INV): never negotiable

### A. Load and attention

- **INV-01 · Extraneous load budget ≈ 0.** Any element that competes for working memory without
  contributing to the task gets removed. *Check:* for each element on screen, name the decision or
  task step it supports; if there's no answer, it doesn't belong.
- **INV-02 · Zero memory dependency across screens.** No data the system already knows is asked for
  again; nothing forces the user to memorize a code, a value or an instruction to use later
  (WCAG 2.2 · 3.3.7 Redundant Entry, 3.3.8 Accessible Authentication).
- **INV-03 · Nothing hijacks attention.** No autoplay, no auto-advancing carousels, no unsolicited
  modals over the task in progress, no aggressive timers, and time limits can be extended
  (WCAG 2.2 · 2.2.x). Peripheral attention is involuntary: stealing it is a cost, not a resource.
- **INV-04 · Cognitive accessibility floor.** WCAG 2.2 level AA plus the COGA guidance: plain
  language, conventional icons with text labels, logical order, errors explained without jargon.
  Fatigue, multitasking and neurodivergence are the normal case, not the edge case.

### B. The action cycle (Norman's gulfs)

- **INV-05 · No open gulf of evaluation.** Every action produces a perceptible response within
  ≤100 ms (even if it's just a "processing" state), the system status is visible without hunting
  for it, and every error says **what happened, why, and how to get out of it**. "An error has
  occurred" is a failure, not a message.
- **INV-06 · Spatial stability.** Navigation and recurring controls don't move between views; touch
  targets are large enough and spaced far enough apart. Moving elements destroys spatial memory
  (the dorsal pathway) and forces users to consciously remap the screen on every visit.
- **INV-07 · Text–image–action–result congruence.** The button's verb appears verbatim on the
  resulting screen; the image illustrates exactly what the text describes; the label promises
  exactly what happens. Incongruence is processed as conflict and read as a reason for distrust,
  not as a slip.

### C. Autonomy (regulated territory: DSA)

- **INV-08 · Symmetry of entry and exit.** Canceling, unsubscribing, deleting the account or
  withdrawing consent can't cost more steps, more clicks or more searching than the opposite action
  (no *roach motel*).
- **INV-09 · Visual parity between options.** Accept/reject, yes/no, premium/free get the same
  visual weight: same control type, size, contrast and hierarchy. Disguising the option the business
  doesn't want as a faded link is visual interference.
- **INV-10 · Urgency and scarcity only when true and verifiable.** No countdowns that reset, no
  made-up "only 2 left". Exploiting loss aversion to shut down rational evaluation is manipulation,
  not persuasion.
- **INV-11 · No confirmshaming or emotional coercion.** Both options are worded in a neutral,
  symmetrical tone ("No, thanks", not "No, I'd rather keep losing money").
- **INV-12 · Microboundary for the irreversible, undo for the reversible.** Irreversible actions
  (deletion, payment, sending, sharing data) require a deliberate act (typing the name, checking a
  box explicitly) that forces a shift into analytical thinking. Reversible actions do **not** get a
  confirmation dialog: they get undo. Routine confirmations become automatic and stop protecting
  anyone.

### D. Evidence

- **INV-13 · Reverse inference is forbidden.** Never justify a decision with "this brain area
  lights up, so the user feels X": any given region takes part in many processes, and the argument
  is logically invalid. Mechanisms generate **hypotheses**; triangulated behavioral evidence decides.
  See `references/audit-and-metrics.md`.
- **INV-14 · Neurodata and biometrics only with explicit consent and minimization.** Gaze, pupil,
  EEG or emotional inferences are special-category data (GDPR Art. 9): a declared purpose, the bare
  minimum, bounded retention, auditability. Without explicit consent, they are not collected.

## Levers to promote (PRO)

- **PRO-01 · Perceptual fluency.** High contrast, legible type, stable alignment and rhythm. The
  brain mistakes "easy to process" for "true, safe and competent": fluency is the main generator of
  nonconscious trust.
- **PRO-02 · Deliberate aesthetics.** Beauty activates reward circuits and spreads a halo of
  usability over the rest of the product. It's a multiplier, never a substitute: beauty on top of a
  broken flow only delays the frustration.
- **PRO-03 · Progressive disclosure and *chunking*.** Split what is intrinsically complex into steps
  with few interdependent elements at a time. Rule of thumb: ≤4 elements the user has to hold at
  once, one main decision per screen.
- **PRO-04 · Conventions and existing mental models.** Reuse familiar patterns unless you have a
  strong reason not to; every deviation is paid for in the gulf of execution. Originality belongs
  in the visual identity, not in where the save button lives.
- **PRO-05 · Rich feedback and explicit states.** Progress with meaning ("uploading 3 of 7"),
  confirmations anchored to the affected element, multimodal feedback when the action matters.
- **PRO-06 · Prompt → ability → motivation, in that order.** A behavior happens when motivation,
  ability and a prompt coincide. When conversion is low: first check that the prompt is visible,
  then simplify until the action is trivial, and only at the end touch motivation (it's the most
  expensive lever and the easiest to turn into manipulation).
- **PRO-07 · Perceptual closure.** Group by proximity, similarity and continuity; let the user
  complete the pattern. Resolving a visual ambiguity produces pleasure and affinity (the aesthetic
  "aha"). Don't confuse this with puzzles: the ambiguity must resolve itself in under a second.
- **PRO-08 · Deliberate germane load** (only in learning or mastery contexts). Desirable
  difficulties (retrieval practice, spaced practice, interleaving) hurt immediate performance and
  greatly improve retention. Use them in training, onboarding for complex tools and gamification;
  never in a payment or an administrative chore.
- **PRO-09 · Microboundaries where the decision matters.** Two seconds of friction turns an
  automatic gesture into a conscious decision. Use it for what is irreversible, expensive or likely
  to be regretted (mass sends, transfers, public posts, sharing data).
- **PRO-10 · Calibrated transparency in AI interfaces.** An LLM's flawless fluency numbs skepticism
  and encourages overtrust. Compensate: sources one click away, visible uncertainty, cheap
  verification, stated system limits, easy editing of generated output.
- **PRO-11 · Automate mechanics, not judgment.** Offloading memory and calculation to the machine is
  good; systematically offloading synthesis and judgment erodes the user's ability and their
  commitment to the result. Design the point where the human decides.

## Analysis protocol

Follow the steps in order; skip only what doesn't apply, and say so.

1. **Framing.** The concrete task, the user (novice/expert, frequency of use), the device, the
   context (fatigue? multitasking? real urgency?) and what "success" means on this screen.
2. **Trace the action cycle.** Goal → intention → plan → execution → perception →
   interpretation → evaluation. Mark where the **gulf of execution** opens (they know what they want
   but not how to do it) and where the **gulf of evaluation** opens (they acted but don't know what
   happened).
3. **Load inventory.** Classify each element as intrinsic (inherent to the task), extraneous (noise)
   or germane (productive effort). The list of extraneous elements is the removal backlog, ordered by
   proximity to the critical path.
4. **Invariant sweep.** Go through INV-01…INV-14 with a verdict and concrete evidence (element, line,
   screenshot). Without evidence, it isn't a finding: it's an opinion.
5. **Friction classification.** Every friction point falls into one of three buckets:
   **extraneous** (remove it), **desirable** (keep it and justify it by learning or by user
   protection) or **dark** (forbidden, regulatory risk).
6. **Fluency and trust check.** Perceptual (legibility, contrast, density), conceptual (are the
   hierarchy and vocabulary understood?) and linguistic (plain language?). Look for text/image/action
   incongruences: they are what triggers visceral distrust.
7. **Ventral / dorsal.** Are there unlabeled icons, low-contrast type, density that forces decoding?
   (ventral fatigue). Do controls move between views, are there small targets or unpredictable
   patterns? (dorsal sabotage).
8. **Fogg on the key action.** Is there a perceptible prompt? Is ability the bottleneck? Never
   propose raising motivation while there is still simplification left to do.
9. **Measurement.** For each relevant finding, define the behavioral metric that would confirm or
   refute it before touching anything (`references/audit-and-metrics.md`).

**Severity:**

| Level | Criterion |
| :---- | :---- |
| **Blocking** | Broken invariant with legal exposure (INV-08…INV-11, INV-14) or a gulf of evaluation on the critical path |
| **High** | Extraneous load on the critical path, memory dependency, spatial instability |
| **Medium** | Avoidable friction off the critical path, degraded fluency, a convention broken for no reason |
| **Low** | Polish: rhythm, microcopy, aesthetic refinement |

**Output format (short version; the full one is in `assets/worksheet-templates.md`):**

```
### [ID] Finding title — [Severity]
- Where: component / screen / file:line
- What I observe: verifiable fact, no interpretation
- Mechanism: which principle explains the problem (INV/PRO + framework)
- Cost to the user: in steps, errors, memory or trust
- Proposed change: concrete and actionable
- How we verify it: metric or test, with a threshold
```

## Design protocol

1. **The component's cognitive budget** (declare it before drawing anything):
   elements the user must hold at once (≤4) · decisions per screen (ideally 1) ·
   required fields (the provable minimum) · time to first feedback (≤100 ms) ·
   steps to complete the task · steps to undo it (≤ the steps to do it).
2. **Pick an archetype** in `references/component-catalog.md` and inherit its invariants and warning
   signs before inventing anything.
3. **Decide the friction** with the tree below. Write the decision down: "there is NO confirmation
   here because the action is reversible and undo exists" is valid documentation.
4. **Define the required states**, all of them: initial · empty (with a suggested first action) ·
   loading (with meaningful progress) · success (anchored to the affected object) · error (cause +
   recovery) · partial/offline · disabled (always with a visible reason). A component without an
   error state and an empty state is only half designed.
5. **Map affordances**: what's clickable looks clickable, what's disabled explains why, focus is
   visible, tab order follows visual order, the primary goal dominates the hierarchy.
6. **Write the copy**: the same action verb on the button and in the result, plain language, no
   internal jargon, symmetrical options, errors in the second person without blame.
7. **Write the acceptance criteria** and the instrumentation (which events get logged so you know
   whether it works). Without this, the redesign is an opinion with CSS.

### Friction decision tree

```
Is the action irreversible or costly (money, data, identity, third parties)?
├── Yes → microboundary proportional to the harm (typing the name > double confirmation > pause)
│         + explain the exact consequence + offer undo if technically possible
└── No  → Is the goal for the user to LEARN or gain mastery?
          ├── Yes → desirable difficulty (retrieval, spacing, interleaving), never in administrative tasks
          └── No  → Does the friction protect the user or only the business?
                    ├── The user     → keep it, minimal and explained
                    └── The business → REMOVE IT. If it retains people by making it hard to leave, it's a dark pattern.
```

## Mistakes this skill exists to prevent

- **Neuro-theater.** Citing brain areas to lend authority to an aesthetic preference. If the
  argument doesn't survive without the word "cortex", it wasn't an argument (INV-13).
- **Zero-friction dogma.** Removing all effort produces shallow interaction, automatic decisions the
  user regrets and, in learning, illusory competence.
- **Aesthetics as an alibi.** The beauty halo inflates *perceived* usability in qualitative tests
  and hides objective failures. Measure tasks, not impressions.
- **Mistaking conversion for success.** A dark pattern lifts conversion in the short term and
  destroys trust, retention and (under the DSA) money in fines.
- **Optimizing for the team's expert user.** Whoever designed the system has automated mental
  schemas the new user lacks; the real cost is in the first time.
- **Adding explanations instead of removing complexity.** A tooltip that justifies a confusing field
  is extraneous load on top of extraneous load.

## Verification before calling anything done

- [ ] All 14 invariants reviewed explicitly, with a verdict and evidence.
- [ ] Every friction point present is classified and justified in writing.
- [ ] Every required state exists (including empty, error and offline).
- [ ] No causal claim rests on reverse inference or on "it's been proven that the brain...".
- [ ] Every proposed change has a verification metric and a threshold.
- [ ] If the flow touches consent, subscriptions, cancellation, pricing or personal data: checked
      against `references/regulation-and-ethics.md` and flagged for human legal review.

## Triage tool

`scripts/scan_friction.py` flags *candidates* for review in HTML/JSX/TSX/Vue/Svelte:
fabricated urgency, confirmshaming, asymmetric consent, destructive actions without a
microboundary, autoplay and timers, fields without `autocomplete`, a missing feedback region,
interactive density, placeholders used as labels, disabled controls without a reason and generic
errors. It recognizes UI copy in both English and Spanish.

```bash
python3 scripts/scan_friction.py path/to/project           # human-readable report
python3 scripts/scan_friction.py src/ --json               # output for CI
python3 scripts/scan_friction.py src/ --only INV-05,INV-09 # filter by invariant
python3 scripts/scan_friction.py src/ --fail-on high       # exit code 1 on high or blocking findings
```

It's a heuristic, regex-based detector: **it points to where to look; it doesn't hand down
verdicts**. It produces false positives on purpose (it would rather over-report). Nothing it says
replaces the invariant sweep done by hand.

## Source

An operational synthesis of the report *Cognitive Neuroscience and Psychology in UX/UI Design: Brain
Mechanisms, Trust and User Behavior*. The detail of the mechanisms, with the limits of their
validity, is in `references/`. The regulatory references guide design; they are not legal advice,
and any flow with regulatory exposure must go through human legal review.
