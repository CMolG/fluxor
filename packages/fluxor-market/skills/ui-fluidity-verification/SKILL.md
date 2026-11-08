---
name: ui-fluidity-verification
description: Verifies that a UI is fluid and structurally sound, not just functionally correct. Covers frame-level invariants (long animation frames, dropped frames, interaction latency, layout shifts, forced layouts, non-composited animations, hydration stutter), algorithmic layout checks (containment, clipped text, flex/grid blowouts, sub-pixel seams, occluded or undersized targets, scroll traps) across widths and font scales derived from the CSS, what headless emulation can and cannot prove about real phones (iOS WebKit, GPU memory, touch coalescing, thermal throttling), and gates that separate real regressions from rendering noise (PASS/FAIL/INCONCLUSIVE). Use it to design or run performance or visual checks in CI, when the tests pass but it feels janky, it stutters on mobile, it breaks at some widths, screenshot tests are flaky, or a CLS, INP or jank budget is being set.
---

# UI Fluidity Verification

## Why this skill exists

An end-to-end assertion samples the DOM at rest: `toBeVisible` and `toHaveText` wait until the
state settles, then check it. The experience lives in the frames *between* settled states, which
is exactly what the assertion steps over. A click handler that holds the main thread for 300 ms
passes (the text does appear). A hydration pass that freezes the page for 800 ms passes (the button
works afterwards). An animation that re-lays out the page sixty times a second passes (the end
state is right). **Functional correctness is a property of states; fluidity is a property of
transitions.** Verifying fluidity means measuring transitions directly, with invariants precise
enough to compute and to gate.

Three facts shape everything below:

1. **Structure is deterministic, time is not.** Under a pinned environment, geometry, the set of
   animated properties, whether a script forced a layout and which element shifted are the same on
   every run. Durations are not, and in CI they are measured on the wrong machine anyway. Gate
   structure exactly and time statistically; never the reverse.
2. **An emulator changes the viewport, not the silicon.** Headless device emulation is a layout
   oracle for its own engine, and a *relative* performance oracle at best.
3. **A gate that fails on noise gets switched off, and a switched-off gate passes everything.**
   False positives are a correctness defect of the gate, not an inconvenience.

## The model: two signal classes, three verdicts

| Class | Examples | Compared how |
| --- | --- | --- |
| **Structural** | audit findings, layout-shift count and sources, scripts with forced style/layout, animated property classes, non-passive listeners, layout and style-recalc counts, promoted-layer memory | exactly, against the baseline and/or a budget, from one run |
| **Timing** | interaction duration and its phases, long-animation-frame blocking time, dropped frames, hydration blocking | interleaved A/B samples on one host, rank test plus bootstrap bounds plus false-discovery control |

A gate returns **PASS**, **FAIL** or **INCONCLUSIVE**. INCONCLUSIVE is not a soft fail. It means
"this evidence cannot separate a material regression from noise", and it comes with the sample
size that would decide. A structural value that differs between two identical runs is not noise:
it is a **nondeterminism finding** (a race, a late font, unpinned data), and it is reported as one.

## The fluidity invariants (F)

What separates "fluid" from "functional". Formulas, thresholds and their sources are in
`references/fluidity-invariants.md`.

- **F1 Frame continuity.** In every window of continuous motion (scroll, drag, animation,
  transition), with T the *calibrated* refresh interval: dropped = Σ (round(Δ/T) − 1) over frame
  deltas Δ > 1.5T. Fluid means no streak of ≥ 2 dropped frames and stable pacing (p95/median Δ ≤
  1.5). Judder (uneven pacing) is more visible than a uniformly lower rate.
- **F2 Interaction latency.** Every discrete interaction paints its response within 100 ms when
  it is direct feedback (press, toggle, typing) and within 200 ms in any case (INP's "good"). Each
  interaction is decomposed into **input delay** (the thread was busy with other work),
  **processing** (your handlers) and **presentation delay** (style, layout and paint after them).
  Each phase has a different fix, so a report that gives only the total is not actionable.
- **F3 Main-thread headroom.** No long animation frame with blocking time inside an interaction
  window, and **zero scripts with forced style/layout** (layout thrashing). That last one is
  structural: the code either reads layout after writing to it or it does not.
- **F4 Compositor-only motion.** Every animation or transition that runs during motion animates
  only `transform`, `translate`, `rotate`, `scale` or `opacity`, which is structural and exact.
  No *latent* layout transitions (`transition: all`, `transition: height`) waiting for the next
  state change.
- **F5 Visual stability.** Zero layout shifts without recent input inside a measured window. In
  the lab, any unexpected shift is a defect with a named source node. CLS ≤ 0.1 is the *field*
  threshold, not a lab tolerance.
- **F6 Hydration continuity.** From first paint to interactive: no hydration mismatch, no shift
  caused by hydration (F5 over the load window), the longest blocking frame within budget under the
  device-class CPU throttle, and no dead click. A tap at first paint is either replayed or met by
  a control that visibly says it is not ready.
- **F7 Scroll integrity.** No non-passive touch or wheel listener over a scrolling area, no
  JavaScript-driven scroll physics, and `touch-action` declared on custom gesture surfaces.

## The layout invariants (L)

Checked by `__fluidity.audit()` at every settled state of every matrix cell. The algorithms,
tolerances and their false-positive traps are in `references/layout-pathologies.md`.

- **L1 Containment.** Every in-flow box stays inside its container, within 1/60 px (the coarsest
  layout unit, Gecko's; Blink and WebKit use 1/64), unless a scroller owns that axis. Rules:
  `viewport-overflow-x`, `content-spill`, `flex-blowout`, `grid-blowout`.
- **L2 Content conservation.** No text clipped without an ellipsis or a line clamp, and nothing
  outside every scrollable area. Rules: `clipped-text`, `unreachable-content`, `unreachable-fixed`.
- **L3 Non-collision.** In-flow siblings do not overlap: `overlap`.
- **L4 Hit-testability.** A tap at a visible control's center hits that control, and undersized
  targets keep WCAG 2.2 SC 2.5.8's 24 px spacing circle. Rules: `occluded-target`, `target-size`.
- **L5 Scroll reachability.** One scroller per axis under a finger. Rules: `scroll-trap`,
  `touch-action-block`, `blocking-scroll-listener`.
- **L6 Device-pixel integrity.** Boxes that touch in layout snap to the same device pixel:
  `subpixel-seam`.
- **L7 Continuity across the parameter space.** L1–L6 hold at every width of the derived matrix,
  at every font scale and with stress content. The layout changes shape only at declared
  thresholds; a jump anywhere else is an undeclared breakpoint, found by a width sweep with
  bisection.

## Workflow

1. **Pick the experience-critical transitions** per surface: load to first interaction, the main
   interaction, scrolling the main list, opening and closing overlays, route changes. A gate on
   everything is a gate on nothing.
2. **Pin the environment** before measuring anything: fonts local and awaited, network replayed,
   clock and randomness fixed, viewport, DPR and `reducedMotion` explicit, served over http, one
   browser context per test. The checklist and its reasons are in `references/quality-gates.md`.
3. **Derive the matrix from the CSS.** Run `python3 scripts/breakpoints.py <built css dir>` to get
   both sides of every media threshold, per font scale, plus floor and ceiling. Add short
   heights (landscape phones, an open keyboard) and stress content: unbroken URLs, +40 % text,
   RTL, CJK, empty states.
4. **Instrument** with `assets/probe.js`, injected before the app runs (`addInitScript`). Call
   `calibrate()` once, open a window with `begin()` / `end()` around each transition, `audit()` each
   settled state, and `snapshot()` the states you want to diff.
5. **Drive through the real input pipeline**: synthesized scroll gestures, touch, and CPU
   throttling calibrated to a device class. The code is in `references/driver-recipes.md`.
6. **Collect.** Structural values come from one run. Timing comes from interleaved A/B: baseline
   and candidate builds alternating on the same host, at least 10 pairs.
7. **Gate.** `python3 scripts/gate.py metrics.json` exits 0 PASS, 1 FAIL, 3 INCONCLUSIVE.
   `python3 scripts/layout_diff.py base.json cand.json` exits 0 with no change cluster, 1 with one.
8. **Report a cause, not a symptom.** Each failure names the invariant, the element, the
   mechanism ("flex item at `min-width: auto`", "forced layout in `BUTTON#save.onclick`") and the
   smallest fix. INCONCLUSIVE results are reported with their suggested sample sizes, never
   dropped.

## What CI can and cannot prove

Detail and strategies: `references/device-realism.md`.

| Question | Headless CI | What answers it |
| --- | --- | --- |
| Layout at a width, DPR, font scale | Yes, for that engine | Chromium, WebKit and Firefox projects in CI |
| iOS-only behavior (focus zoom, toolbar resize, keyboard, safe areas) | No: Playwright's WebKit is not iOS Safari | iOS Simulator, on a schedule, plus the static checks the probe makes (`ios-input-zoom`) |
| Main-thread cost | Relative only, A/B on one host | CPU throttling calibrated against a reference device |
| Raster, GPU, compositing cost | No: headless rasterizes in software | Work proxies: layer count and memory, paint area |
| Touch handling | Partly: gestures run, but there is no digitizer and no coalescing | Bursts of moves per frame; `getCoalescedEvents()` in drawing and drag code |
| Thermal throttling | No | Headroom: the work fits the budget at the throttled rate (×2 on phones until calibrated) |
| What users get | No | Field data (LoAF, INP attribution, shift sources). When it contradicts the lab, the lab's model is wrong |

## Gating policy (the false-positive paradox)

1. **Exact on structure, statistical on time, no absolute milliseconds from CI.**
2. **Interleave**: ABAB on one host, paired tests. Never compare against last week's numbers.
3. **Material, not merely significant**: FAIL needs the confidence bound to clear a relative AND an
   absolute threshold, after false-discovery control across all timing metrics.
4. **Abstain on a noisy host**: when the calibration workload's robust CV exceeds 5 %, timing
   abstains (INCONCLUSIVE) and structure still decides.
5. **A/A before A/B**: run the baseline against itself. A metric that fails A/A is not a gate yet;
   it is a monitor until its noise is fixed.
6. **Diff structure, not pixels**: `layout_diff.py` collapses a cascade into one change cluster
   and names its origin. Pixel diffs are a review aid, valid only on the same engine and host.
7. **Ratchet**: an improvement tightens the baseline in the same change. Loosening a budget is a
   person's decision, with the reason written down.
8. **A flake is a defect**, never retried away.
9. **Scope** the gate to the surfaces the change reaches.

## Tools

- `assets/probe.js`: in-page instrument, zero dependencies, for Chromium, WebKit and Firefox. It
  reports `support` for every API, so a missing API reads "unsupported", never 0 (WebKit and Firefox
  have no LoAF or layout-shift entries). `calibrate`, `begin`/`end`, `audit` (18 rules,
  `__fluidity.rules`), `animations`, `snapshot`. Opt out per element with
  `data-fluidity-allow="rule …"`; every opt-out is counted in the audit summary.
- `scripts/breakpoints.py`: the width and height matrix from media and container queries, with
  em and rem thresholds moving with the user's font scale.
- `scripts/gate.py`: the three-valued gate. Input format in its docstring.
- `scripts/layout_diff.py`: structural regression between two snapshots, as change clusters with
  probable origins.

## Anti-patterns

- A fixed sleep before measuring. Wait for the app's readiness signal, `document.fonts.ready`
  and two frames.
- Observers or a rAF loop installed after the action: the action has already happened. Inject
  at init; sample frames only inside a window, because a permanent rAF loop changes scheduling.
- Reading a missing API as zero: "0 layout shifts" from WebKit means "not measured".
- A Lighthouse score as the gate: a weighted composite moves for reasons it cannot name.
- Disabling animations in the fluidity suite, which removes the thing under test. Disabling them
  for geometry snapshots is correct.
- `retries` on a perf or visual gate, or a raised timeout to make it pass.
- Fixtures on `file://`: Chromium then attributes no scripts in long animation frames.
- A device descriptor taken for the device: `devices['iPhone 15']` gives a viewport and a WebKit
  build, not iOS.

## References

- `references/fluidity-invariants.md`: the rendering pipeline the invariants come from, their
  formulas, perceptual thresholds and measurement pitfalls. Read it before setting a budget or
  explaining jank.
- `references/layout-pathologies.md`: every audit rule's algorithm, tolerance and false-positive
  trap, the width sweep with bisection, metamorphic relations, and font scaling and zoom. Read it
  when a finding looks wrong or a layout breaks only somewhere.
- `references/device-realism.md`: emulation versus silicon, measuring work instead of time, cost
  model calibration, GPU memory, touch coalescing, iOS divergences, thermal headroom and the field
  loop. Read it before claiming anything about phones.
- `references/quality-gates.md`: determinism preconditions, the statistics behind `gate.py`,
  calibration, A/A, ratchets and CI wiring. Read it before turning any measurement into a gate.
- `references/driver-recipes.md`: Playwright and CDP code for injection, windows, synthesized
  gestures, throttling, work counters, layer memory, font scaling, the width sweep, the A/B loop,
  and proving the probe on a fixture. Read it when writing the harness.
