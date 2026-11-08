# Quality gates: isolating deterministic regressions from benign variance

## Contents

1. The paradox, stated
2. Determinism preconditions
3. Classifying every signal
4. The statistics behind `gate.py`
5. Calibration and A/A
6. Structural layout diffs instead of pixel diffs
7. Ratchets, quarantine and ownership
8. Wiring it into CI

## 1. The paradox, stated

A strict gate on noisy signals fails often for nothing. Engineers learn to re-run it, then to
ignore it, then to disable it. A lax gate passes regressions. The way out is not a threshold
between the two; it is **removing noise from the signal before the gate sees it**: make most
signals deterministic, gate those exactly, and gate the irreducibly stochastic rest with
statistics that know how noisy they are and abstain when they cannot tell.

## 2. Determinism preconditions

Every item removes one known source of run-to-run variance. A structural metric that still
differs between two identical runs after all of this is a nondeterminism finding.

| Precondition | How | Why |
| --- | --- | --- |
| Fonts local and loaded | self-hosted files, `await document.fonts.ready` before measuring | a font swap re-lays out text and shifts everything after it |
| Network replayed | route mocks or HAR replay, no live third parties | response order and timing change what renders when |
| Images sized | `width`/`height` on every `img`; served locally | late decode resizes boxes |
| Clock fixed where the UI shows time | Playwright `page.clock`, or a fixed `Date` | "2 minutes ago" changes text width |
| Randomness seeded | the app's seed hook, or a stub of `Math.random` and `crypto.randomUUID` | random ids and orders |
| Viewport, DPR, `reducedMotion`, color scheme, locale, timezone explicit | context options | defaults differ by host |
| Animations: left on in the fluidity suite, disabled for geometry snapshots | `reducedMotion` or the probe's `animations()` | the fluidity suite measures motion; snapshots need rest |
| Readiness by signal, not by sleep | the app's own ready attribute, `networkidle` only when it is meaningful, two rAFs after | a sleep is a guess that is either flaky or slow |
| Served over http | a local static server or the dev server | LoAF attribution is empty on `file://` |
| A fresh browser context per test | Playwright's default isolation | storage and caches leak state |
| One measurement process per core | workers ≤ cores for timing suites; timing suites never share the host with builds | CPU contention is the largest timing noise in CI |

## 3. Classifying every signal

Before a metric becomes a gate, put it in one class. If you cannot, it is not ready to gate.

| Class | Property | Gate | Examples |
| --- | --- | --- | --- |
| Structural, exact | identical on identical runs | exact compare, zero tolerance unless a reason is written | audit findings, shift count and sources, forced-layout script count, animated property classes, non-passive listeners, `LayoutCount`/`RecalcStyleCount` per interaction, layer count and estimated memory, DOM size |
| Structural, quantized | identical up to a known quantum | exact compare after quantizing | layout-shift score rounded to 4 decimals, rects rounded to 1/64 px |
| Timing | a distribution | paired A/B with `gate.py` | interaction duration and phases, LoAF blocking time, dropped frames, hydration blocking, `ScriptDuration` |
| Perceptual | pixels | never a hard gate across hosts | screenshots: a review aid, same engine and host only |

## 4. The statistics behind `gate.py`

**Paired, interleaved samples.** Run baseline and candidate alternately on the same host
(B, C, B, C, …, with the starting side alternated between batches), N ≥ 10 pairs. Pair i shares
the host's state at that moment: thermal state, background load, cache warmth. Differences dᵢ =
cᵢ − bᵢ cancel that drift, which an unpaired comparison cannot do. In the gate's own test, a host
that warms up across 20 pairs makes the unpaired comparison INCONCLUSIVE (ratio bounds 0.97 to
1.39), while the paired one correctly FAILS a +20 ms regression (bounds 1.15 to 1.17).

**Significance.** Wilcoxon signed-rank on dᵢ (paired) or Mann-Whitney U (unpaired), one-sided,
with tie correction, because timing distributions are skewed and heavy-tailed: no normality
assumption. Event Timing's 8 ms quantization produces ties, which the correction handles.

**False-discovery control.** With 20 timing metrics at α = 0.05, one false alarm per run is
expected. Benjamini-Hochberg across all timing metrics of a run keeps the expected share of false
discoveries at α. A shift with p = 0.006 is a discovery alone, and not among twenty metrics,
where BH needs 0.0025 for the strongest.

**Materiality.** Significant is not the same as important: 30 samples detect a 2 % shift. The gate
bootstraps (seeded, 2000 resamples) the shift of medians and the ratio of medians, and decides
with one-sided bounds at the confidence level (0.95 by default):

- **FAIL** when the lower bound of the shift exceeds `minAbsolute` AND the lower bound of the ratio
  exceeds 1 + `minEffect` AND the metric is a discovery after BH. A `budget` FAILS on its own when
  the candidate median's lower bound is above it.
- **PASS** when the upper bound of the shift is ≤ `minAbsolute`, or the upper bound of the ratio is
  ≤ 1 + `minEffect`: whatever regression exists is immaterial.
- **INCONCLUSIVE** otherwise, with `suggestedSamples`, a normal-theory size for detecting the
  material effect with 80 % power at the observed robust spread. When that number is absurd, the
  verdict says to measure work instead of time.

Defaults: `minEffect` 0.10, `minAbsolute` 0 (set it to at least the clock's resolution, 8 ms for
Event Timing), `minSamples` 10, `alpha` 0.05, `confidence` 0.95. The bootstrap seed derives from
the metric's name, so a verdict is reproducible and independent of metric order.

## 5. Calibration and A/A

- **Calibration workload**: before the timing suite, run a fixed workload (the calibration page of
  device-realism.md §3) 10 times and pass the durations as `calibration.samples`. A robust
  coefficient of variation (1.4826 · MAD / median) above `maxCv` (5 %) means the host is too noisy
  to judge time: every timing metric becomes INCONCLUSIVE, and structure still decides.
- **A/A runs**: run the baseline against itself regularly (nightly). Any timing metric that FAILS
  an A/A run is a false positive by definition. A metric whose A/A FAIL rate exceeds α is demoted
  to a monitor until its noise is fixed: more pairs, a quieter host, or a work proxy instead of a
  duration. A structural metric that differs in A/A is a nondeterminism finding, with a card.

## 6. Structural layout diffs instead of pixel diffs

`scripts/layout_diff.py` compares two `__fluidity.snapshot()` files of the same page, state and
viewport:

1. Boxes are matched by key. Keys are built from test ids, stable ids, landmarks, headings and
   control names, never class names.
2. Deltas under `--tolerance` (0.5 px by default; 1/64 for the same engine and host) are no change.
3. A box that moved by exactly the offset of its nearest matched ancestor was **carried**, and it
   is dropped.
4. Every other changed box joins a **change cluster** through its changed parent and changed
   siblings, so one cause makes one cluster, however many boxes it moved.
5. Each cluster names its **probable origins**: added and removed boxes, the deepest resized boxes
   (block sizes flow up from content), the topmost box when its inline size changed (inline sizes
   flow down from the container), and boxes that moved with nothing changed around them.

A reviewer accepts an intended change by replacing the baseline snapshot in the same commit. The
diff is explainable ("main > card > p grew 24 px; 5 boxes moved with it"), which a pixel diff
never is.

## 7. Ratchets, quarantine and ownership

- **Ratchet**: when a structural metric improves (`gate.py` says "ratchet the baseline"), the
  baseline is updated in the same change, so the improvement cannot silently regress later.
- **Loosening is a decision**: raising a budget or accepting new findings needs a person and a
  reason written next to the baseline. An agent never loosens a gate to make it pass.
- **Quarantine**: a gate that cannot be made deterministic yet is moved to a monitor with a card
  naming its noise source and an owner. It is not deleted and not retried.
- **Opt-outs are visible**: `data-fluidity-allow` counts appear in every audit summary; review
  them like any other exception.

## 8. Wiring it into CI

- **Per pull request**: structural gates on the affected surfaces, in every engine you ship
  (Chromium, WebKit, optionally Firefox). Fast, deterministic, blocking.
- **Per pull request, when a critical surface is touched**: the paired timing suite, Chromium
  only, CPU throttled to the low-end class. `gate.py` exit 1 blocks; exit 3 posts the
  inconclusive metrics with their suggested sample sizes and does not block.
- **Nightly**: A/A runs, the full matrix with the covering array, the width sweep with bisection,
  the thermal-headroom run, iOS Simulator checks.
- **Continuously**: field data per surface and device class, compared against the lab's
  predictions (device-realism.md §8).

Exit codes: `gate.py` 0 PASS, 1 FAIL, 3 INCONCLUSIVE, 2 bad input; `layout_diff.py` 0 no change
cluster, 1 changes, 2 bad input or snapshots that are not comparable.
