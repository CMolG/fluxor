# Device realism: emulation fallacies and what to do instead

## Contents

1. What device emulation changes, and what it does not
2. Measure work, not time
3. A cost model, calibrated once
4. GPU memory and compositing
5. Touch: pipelines and coalescing
6. iOS WebKit divergences
7. Thermal throttling as headroom
8. The field loop
9. Where a physical device still earns its place

## 1. What device emulation changes, and what it does not

| Emulated (Playwright descriptor, CDP `Emulation.*`) | Not emulated |
| --- | --- |
| viewport size, DPR, user agent, `hasTouch`, `isMobile` | the engine: every iOS browser is WebKit, and a Chromium "iPhone" is Blink |
| media features (`prefers-*`, `pointer`, `hover`) | the GPU: headless rasterizes in software (SwiftShader), so raster and composite costs are fiction |
| CPU throttling (`Emulation.setCPUThrottlingRate`) | what throttling means: it slows the **main thread's** scheduler only, not raster or compositor threads, not memory bandwidth, not big.LITTLE core migration |
| network throttling | memory pressure: tab killing, image decode limits, tile eviction |
| touch events synthesized from the driver | the digitizer: 120–240 Hz sampling, coalescing, palm rejection, fling physics |
| | the dynamic toolbar, the virtual keyboard, safe areas, iOS focus zoom, rubber-band overscroll |
| | heat |

So CI is a **layout oracle** for each engine it runs, and a **relative** performance oracle: it
can say build B does more main-thread work than build A on the same host. It cannot say "this
takes 180 ms on a Galaxy A15".

## 2. Measure work, not time

Time = work × cost per unit of work on that device. The work part is device-independent and,
for a deterministic code path, deterministic. Measure it in CI, exactly:

| Work signal | Where it comes from | Engines |
| --- | --- | --- |
| layouts and style recalcs per interaction | CDP `Performance.getMetrics`: `LayoutCount`, `RecalcStyleCount` deltas | Chromium |
| forced synchronous layouts | LoAF `scripts[].forcedStyleAndLayoutDuration > 0`, counted | Chromium |
| main-thread script time per interaction | `Performance.getMetrics` `ScriptDuration` delta (timing class, but stable under A/B) | Chromium |
| animated property classes | `document.getAnimations()` (probe) | all |
| promoted layers and their pixel area | CDP `LayerTree` | Chromium |
| DOM size touched | `Performance.getMetrics` `Nodes`; the size of the subtree a state change replaces | all |
| JavaScript shipped and evaluated | bundle analysis; coverage (`Profiler.takePreciseCoverage`) | Chromium |

A regression in work is a regression on every device; it is gated exactly. Time is then derived
for the device classes that matter, through the cost model.

## 3. A cost model, calibrated once

1. Pick device classes from your audience: e.g. low-end Android (a recent budget phone),
   mid-range Android, a two-year-old iPhone, desktop.
2. Write a calibration page with a fixed workload: N style recalcs over a fixed tree, N layouts,
   a fixed JavaScript loop, a fixed paint. Measure it **once** on one physical reference device per
   class (the field, a cloud device, a colleague's phone), and on the CI host.
3. The CPU throttling rate for class k is t_device,k / t_host for the main-thread parts. Store it
   with the date and the host type. Recalibrate when the CI host type changes. Lighthouse's
   `benchmarkIndex` is the same idea.
4. Throttling covers only main-thread cost. For a raster-heavy surface (big blurs, many layers,
   canvas), the model needs a raster coefficient from the reference device, or field data.

The model is an approximation, and that is acceptable as long as the field loop checks it (§8).

## 4. GPU memory and compositing

- Each composited layer costs about width × height × DPR² × 4 bytes when fully rasterized.
  Chromium rasterizes tiles near the viewport only, so the sum over layers is an **upper bound**. In
  this skill's fixture, a long page at DPR 2 summed to 99 MB from a handful of layers. Compare the
  figure across builds (work), not against device RAM.
- Layers multiply through `will-change`, 3D transforms, `position: fixed` in some engines,
  `backdrop-filter`, video, canvas and implicit promotion (a layer overlapping a composited layer
  gets promoted too: the "layer explosion").
- Low-end GPUs respond to pressure by checkerboarding (blank tiles while scrolling), evicting
  tiles, or the OS killing the tab. iOS kills the WebContent process with no event.
- Gate: layer count and estimated memory per surface, exactly, against a budget per device class.
  Get them from the CDP `LayerTree` recipe; the probe's `layer-memory` rule is a DOM-side lower
  bound for engines without the CDP.

## 5. Touch: pipelines and coalescing

- **Use the browser's gesture pipeline, not dispatched events.** CDP
  `Input.synthesizeScrollGesture` / `synthesizeTapGesture` / `synthesizePinchGesture` go
  through Chromium's synthetic gesture controller, so they exercise compositor scrolling,
  passive-listener decisions and scroll latching. `page.mouse.wheel` and `dispatchEvent` do not.
  In the recipe, a touch scroll of 1,200 px under 4× CPU throttling dropped no frames, because
  compositor scrolling does not wait for a busy main thread. The same scroll with a non-passive
  `touchmove` listener on the page waits for it.
- **Coalescing.** Real digitizers sample at 120–240 Hz while the page renders at 60–120 Hz. The
  browser delivers one `pointermove` per frame and keeps the rest in `getCoalescedEvents()`
  (`pointerrawupdate` exists for low-latency cases). Code that computes velocity, draws strokes or
  drives a drag from `pointermove` alone looks fine in CI, where each event comes one at a time,
  and jagged or laggy on a phone. Test it by dispatching bursts of 4–8 moves per frame
  (driver-recipes.md) and asserting the stroke keeps every point or the velocity stays stable.
- **Handler cost per frame, not per event**: a handler that does layout work on each
  `pointermove` must be rAF-batched; with coalescing that is per frame by construction, without it
  per event.
- **`touch-action`** declares which pans the browser keeps. A drag surface without it either
  scrolls the page under the drag, or the code calls `preventDefault()` from a non-passive
  listener and blocks scrolling everywhere it covers.

## 6. iOS WebKit divergences

Playwright's WebKit build runs the WebKit engine on Linux, macOS or Windows. It catches engine
divergences (flex, grid, sticky, line breaking, form controls, `:has()` and newer selectors), not
iOS Safari behaviors. Those need the iOS Simulator (Xcode), which runs real Mobile Safari on Mac
hardware: right for behavior, wrong for performance. The checks that matter, and how each is
caught:

| iOS behavior | Caught by |
| --- | --- |
| focus zoom on inputs under 16 px | probe `ios-input-zoom` (static, any engine) |
| `100vh` = the large viewport: content under the toolbar | static: `100vh`/`h-screen` on a viewport owner; use `dvh`/`svh`; Simulator to confirm |
| the keyboard resizes the visual viewport, not the layout viewport: `position: fixed` bottom bars float or hide | Simulator; `visualViewport` resize handling in code review |
| safe areas (notch, home indicator) | `env(safe-area-inset-*)` present on fixed edges, plus `viewport-fit=cover` in the meta |
| rubber-band overscroll exposing the body background | `overscroll-behavior` and the body background color |
| a sticky `:hover` after a tap | `@media (hover: hover)` around hover styles (static) |
| tab killed under memory pressure | layer and image memory budgets (§4) |
| canvas size limits (Mobile Safari caps canvas area) | budget canvas area per surface |

## 7. Thermal throttling as headroom

Phones under sustained load lower their clocks, by roughly half after minutes of heavy work on
many devices. It cannot be emulated in CI, and it does not need to be: it is a multiplier on cost.
The invariant becomes **headroom**: a surface's per-frame work, at the device class's calibrated
rate × a thermal factor (2 until measured), still fits the frame budget, and its interactions fit
theirs. A frame that takes 9 ms of main-thread work at the nominal rate is 18 ms when throttled,
and it drops frames at 60 Hz. Run the timing suite once at rate × thermal factor for the
surfaces with continuous motion (scroll, drag, animation).

## 8. The field loop

Lab results are a model; the field is the truth. Collect, from real users and per surface and
device class:

- LoAF with script attribution (Chromium), INP with its three phases (web-vitals attribution
  build), CLS with its largest shift's source, and long-task counts during hydration.
- The device signals the browser exposes: `navigator.deviceMemory`, `navigator.hardwareConcurrency`,
  and effective connection type where available, to bucket users into the cost model's classes.

When the field shows a regression the lab passed, **fix the model, not just the bug**: a missing
transition in the critical list, a work signal not gated, a throttling rate gone stale, a matrix
cell never rendered. That is the step that makes the next one impossible.

## 9. Where a physical device still earns its place

Not for routine testing: it is slow, unscalable and flaky. Use one physical reference device per
class for **calibration** (§3), for the occasional "does this feel right" check of a new
interaction pattern, and to confirm a field regression the lab cannot reproduce. A cloud device
farm is the same thing, rented.
