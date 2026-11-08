# Fluidity invariants: where they come from and how to measure them

## Contents

1. The pipeline a frame goes through
2. Why functional tests pass while the experience degrades
3. The invariants, precisely
4. Perceptual thresholds and their sources
5. Measurement pitfalls

## 1. The pipeline a frame goes through

Every visual update in a browser engine passes through the same stages. Which stages a change
touches, and on which thread, decides whether it can stutter.

```
input ─► event dispatch ─► rAF callbacks ─► style ─► layout ─► paint ─► commit ─► raster ─► composite ─► present
         └──────────── main thread ──────────────────────────────┘          └── compositor / GPU ─────┘
```

- The **main thread** runs JavaScript, style, layout and paint (recording display lists). It is
  single and cooperative: a task that runs 120 ms delays every frame and every input behind it.
- The **compositor thread** takes committed layers and composites them. It can keep scrolling and
  keep animating `transform` and `opacity` **while the main thread is blocked**, provided nothing
  forces it to wait for the main thread: a non-passive touch or wheel listener, a scroll-linked
  effect written in JavaScript, or an animation of a property only the main thread can compute.
- **Vsync** gives a frame deadline every T = 1000 / refresh ms (16.7 ms at 60 Hz, 8.3 ms at 120 Hz).
  Work that misses the deadline does not "slow the frame down": that frame is dropped, and the
  previous one is presented again.

So the cost of a change is decided by the earliest stage it invalidates. `transform`/`opacity`
touch only compositing. `color`, `background`, `box-shadow` need repaint. `width`, `top`, `margin`,
`font-size` and inserting nodes need layout, which can cascade to the whole document.

## 2. Why functional tests pass while the experience degrades

A web-first assertion polls until the expected state appears, then passes. It is blind, by
construction, to everything the user lives through before that:

| What happens | What the assertion sees | What the user sees |
| --- | --- | --- |
| A 300 ms click handler | the result, eventually | a dead button, then a jump |
| Hydration as one long task | a working page | taps that do nothing for 800 ms |
| `transition: height` on an accordion | the right end state | the page re-laid out every frame, scroll judder |
| Read-after-write in a loop (`el.style.x = …; el.offsetHeight`) | correct output | forced synchronous layout, N layouts per frame |
| A late font, a late image, a late banner | final geometry | content jumping under the finger |
| A non-passive `touchmove` on the scroll area | nothing | scrolling that waits for JavaScript |
| A GC pause or a synchronous image decode | nothing | one hitch in an otherwise smooth scroll |

**Micro-stutters during state transitions** come mostly from one frame doing all the work of a
state change: the framework commit, the style recalc of a large subtree, a layout of the whole
document and a big repaint, all before one deadline. That frame is dropped. Spreading the work
helps (`startTransition`, `content-visibility`, virtualization, smaller invalidation roots); so
does not doing it (compositor-only motion, `contain: layout paint` on the moving part).

## 3. The invariants, precisely

Notation: a **window** W is the interval from an action to its settled state, opened with
`__fluidity.begin()` and closed with `end()`. T is the refresh interval from `calibrate()`.

**F1 Frame continuity**, over windows of continuous motion.
- Frame deltas Δᵢ = tᵢ − tᵢ₋₁ from rAF timestamps.
- dropped(Δ) = round(Δ / T) − 1 when Δ > 1.5 T, else 0. dropped(W) = Σ dropped(Δᵢ).
- worstDropStreak = the longest run of consecutive missed frames.
- pacing = p95(Δ) / median(Δ).
- Default budgets: worstDropStreak ≤ 1, pacing ≤ 1.5, droppedRatio ≤ 5 %. These are timing
  signals: device-dependent, gated A/B (quality-gates.md).
- Without calibration, T is estimated as the 25th percentile of the deltas, which is blind to a
  page that runs at a uniformly halved rate. Always calibrate on an idle page first.

**F2 Interaction latency**, per discrete interaction (pointer, key; Event Timing entries sharing
an `interactionId`).
- duration = max over the interaction's events of (next paint − event timestamp).
- input delay = min(processingStart) − start; processing = max(processingEnd) − min(processingStart);
  presentation delay = end − max(processingEnd).
- Budgets: ≤ 100 ms for direct feedback, ≤ 200 ms for any interaction.
- Fixes by phase: input delay means something else held the thread (hydration, timers, third
  parties), so split it or defer it. Processing is your handler: yield (`scheduler.yield()`,
  `setTimeout` continuation), do less, move work off the main thread. Presentation delay means
  the DOM change is expensive to render: shrink the invalidation, virtualize, `content-visibility`.

**F3 Main-thread headroom**, over interaction windows.
- Long animation frames (LoAF, Chromium): frames whose work exceeded 50 ms. `blockingDuration`
  is the part of the frame's long tasks beyond 50 ms each, plus render time.
- Structural part: the count of LoAF scripts with `forcedStyleAndLayoutDuration > 0` is 0. A
  forced layout happens when JavaScript reads geometry (`offsetHeight`, `getBoundingClientRect`,
  `getComputedStyle(...).width`, `scrollTop`) after writing a style or the DOM in the same task.
  Whether it happens depends on the code path, not on the machine.
- Work counters (CDP `Performance.getMetrics`: `LayoutCount`, `RecalcStyleCount`) per interaction
  are structural when the code path is deterministic: compare them exactly.

**F4 Compositor-only motion.**
- For every animation running in a motion window: every animated property ∈ {transform,
  translate, rotate, scale, opacity}. `filter`, `backdrop-filter`, `clip-path` and
  `background-color` are composited by some engines and versions only: allowed with a note, never
  assumed on a phone. Registered custom properties (`@property`) animate on the main thread.
- Latent: no element with a non-zero `transition-duration` on `all` or on a layout property.
- `will-change` is not free: each promoted layer costs width × height × DPR² × 4 bytes of GPU
  memory (device-realism.md).

**F5 Visual stability.**
- Layout Shift entries with `hadRecentInput = false` inside W: count 0. Each entry names its source
  nodes and their previous and current rects. With fonts, images and data pinned, the set is the
  same on every run.
- Shifts within 500 ms of a discrete input are excluded by definition (they are "expected"). The
  probe reports them separately as `withRecentInput`. A shift that lands 600 ms after a click,
  because a fetch was slow, counts.
- The field threshold (CLS ≤ 0.1 at the 75th percentile, session windows of 5 s with 1 s gaps) is
  for real-user data. A lab run with pinned inputs has no excuse for any unexpected shift.

**F6 Hydration continuity**, over the load window (navigation start to the app's readiness signal).
- No hydration mismatch (React logs it as an error; fail on console errors in this window).
- F5 over the load window: server HTML and hydrated DOM have the same geometry.
- Longest blocking frame (LoAF) or long task under the device-class CPU throttle ≤ budget, timing
  class. Default budget: 200 ms, the interaction budget, because a tap can land at any point.
- Dead-click test: tap the primary control the moment it paints, then assert a response within
  the interaction budget, or a visible not-ready state on the control. An invisible gap between
  visible and interactive is the defect.

**F7 Scroll integrity.**
- No non-passive `touchstart`, `touchmove`, `wheel` or `mousewheel` listener on a scrolling area,
  or on window/document with `{ passive: false }`. Browsers default root-level listeners to passive;
  any other target defaults to blocking.
- No scroll physics in JavaScript (scroll events driving `scrollTo`), which breaks momentum, rubber
  banding and assistive scrolling. Scroll-linked effects use `position: sticky`, scroll snap, or
  scroll-driven animations (`animation-timeline: scroll()`), which run on the compositor.
- Custom gesture surfaces declare `touch-action` so the browser knows which pans it still owns.

## 4. Perceptual thresholds and their sources

| Threshold | Meaning | Source |
| --- | --- | --- |
| ~100 ms | the limit for a response to feel caused by the action | Card, Moran and Newell, *The Psychology of Human-Computer Interaction* (1983), perceptual processor cycle; Miller (1968); Nielsen's response-time limits |
| 200 ms | INP "good" at the 75th percentile | web.dev Interaction to Next Paint (Core Web Vitals) |
| 50 ms | long task: a 100 ms response leaves ~50 ms for the handler | W3C Long Tasks API; RAIL model |
| 0.1 | CLS "good" at the 75th percentile, field data | web.dev Cumulative Layout Shift |
| 1–2 frames | a single dropped frame in a scroll is rarely noticed; a run of two or more reads as a hitch, and uneven pacing (judder) reads worse than a steady lower rate | display-motion perception; Chrome's smoothness metric work |
| 24 × 24 CSS px | minimum target with the spacing exception | WCAG 2.2 SC 2.5.8 (AA) |
| 44 × 44 CSS px | enhanced target size | WCAG 2.2 SC 2.5.5 (AAA); Apple HIG |

Budgets are per surface and written next to the gate. A budget nobody can trace to one of these,
or to a product decision, is a number someone guessed.

## 5. Measurement pitfalls

- **Event Timing durations are rounded to 8 ms** (a privacy mitigation), so differences under
  8 ms are invisible and ties are frequent. The rank tests in `gate.py` handle ties; do not gate a
  difference the clock cannot resolve.
- **Only Chromium has LoAF, Long Tasks and Layout Shift.** WebKit and Firefox report Event Timing
  (Firefox fully, WebKit partly) and rAF. The probe marks the rest `unsupported`. Treat that as
  missing evidence and get it from Chromium, or from the field where Safari users exist.
- **LoAF script attribution needs a real origin.** On `file://` the `scripts` list is empty. Serve
  fixtures over http.
- **rAF stops in background tabs and hidden iframes**, and headless Chromium paces frames
  without a display. Calibrate in the same context you measure.
- **Observers must exist before the work.** `buffered: true` recovers some entry types, but not
  all and not past the buffer size. Inject the probe at init.
- **A permanent rAF loop is an intervention**: it forces a frame on every vsync and can hide or
  create jank. The probe samples frames only inside a window that asks for it.
- **Timer clamping and `performance.now()` coarsening** (cross-origin isolation off: 100 µs; on:
  5 µs) bound the resolution of any in-page duration.
