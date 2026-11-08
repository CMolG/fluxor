# Layout pathologies: deterministic detection

## Contents

1. Geometry the engine actually computes
2. The audit rules: algorithm, tolerance, false-positive traps
3. Intrinsic sizing blowouts, from the specs
4. Sweeping the parameter space
5. Metamorphic relations: verification without a golden image
6. Engine divergence and robustness margins

## 1. Geometry the engine actually computes

- **Layout units.** Blink and WebKit lay out in fixed-point units of 1/64 CSS px (`LayoutUnit`),
  Gecko in 1/60 px (app units). `getBoundingClientRect()` returns doubles derived from those, so
  two edges closer than 1/60 px are the same edge. Every containment comparison uses ε = 1/60.
- **Scroll dimensions are integers.** `scrollWidth`, `scrollHeight`, `clientWidth` and
  `clientHeight` are rounded. A box with 100.4 px of content in 100 px may report 100 or 101 by
  engine. So the probe first screens with `scroll > client + 1`, then confirms the overflow with
  exact rects (in-flow children, text ranges).
- **Paint snaps to device pixels.** Each edge is snapped to the nearest device pixel: x_dev =
  round(x · dpr) / dpr. Two boxes that touch in layout but sit at different sub-pixel offsets snap
  to different pixels: a 1-device-pixel hairline gap or overlap (a "seam") appears at some DPRs and
  zoom levels and not others.
- **`getBoundingClientRect` ignores clipping.** It reports the full layout box even when an
  ancestor's `overflow: hidden` hides part of it. That is what lets the audit see clipped
  content at all.

## 2. The audit rules

Every rule skips elements that are not rendered (`checkVisibility()`, or display/visibility), SVG
internals (drawing, not layout boxes), and elements under `data-fluidity-allow="<rule>"`.

| Rule | Algorithm | Severity | False-positive traps handled |
| --- | --- | --- | --- |
| `viewport-overflow-x` | elements whose right edge (page coordinates; viewport for fixed) exceeds `clientWidth` + ε, outside any ancestor that clips or scrolls x; outermost culprits only | error if the page scrolls sideways, warn if the root's `overflow-x` hides it ("masked") | body/html overflow belongs to the viewport, not to a container |
| `unreachable-content` | the root's effective `overflow-y` (html, or body propagated) is hidden/clip and `scrollHeight` > viewport + 1 | error | catches a scroll lock left behind by a closed modal |
| `content-spill` | deepest boxes with overflow visible whose scroll size exceeds their client size AND an in-flow, untransformed child or the box's own text leaves the padding box | warn | positioned and transformed descendants (menus, tooltips) inflate scroll sizes: ignored; containers already reported as blowouts are not reported again |
| `clipped-text` | overflow hidden/clip, scroll > client + 1, and a text range rect leaves the padding box on the clipped axis, with no `text-overflow: ellipsis` on non-wrapping text and no line clamp | error | media crops (no text) and visually-hidden 1 px boxes are skipped |
| `flex-blowout` | a flex container that is not a scroller on its main axis has an in-flow item leaving its content box on that axis; suspects are items at `min-width`/`min-height: auto`, largest first | error | reels (`overflow-x: auto`) are intentional |
| `grid-blowout` | the used column tracks (`getComputedStyle().gridTemplateColumns`, resolved px) plus gaps exceed the content width | error | a grid that scrolls x is intentional |
| `overlap` | per parent, in-flow block-level siblings (not floats, not sticky, not transformed), a sweep line over x, O(n log n + k); pairs overlapping by > ε on both axes | error, warn with a negative margin | explicit grid placement stacking items in one cell is deliberate; inline boxes that wrap span whole lines and are skipped |
| `subpixel-seam` | consecutive flex items with zero gap: \|start(B) − end(A)\| < 1/dpr and snap(start(B)) ≠ snap(end(A)) | warn | only touching items; spaced items are apart on purpose |
| `occluded-target` | for each visible interactive element, `elementFromPoint` at the center of its visible part (diving through open shadow roots) must return the element, a descendant or one of its labels | error | `pointer-events: none` overlays are skipped by hit-testing itself; 1 px visually-hidden inputs are skipped |
| `target-size` | WCAG 2.2 SC 2.5.8: an undersized target fails when a 24 px circle on its center intersects another target or another undersized target's circle; info below 44 px on coarse pointers | error / info | inline links inside running text are exempt; user-agent default controls are an exception only a person can grant (`data-fluidity-allow`) |
| `scroll-trap` | a vertical scroller whose size covers ≥ 85 % of the viewport on both axes, inside another scrolling container or a scrolling document | error with `overscroll-behavior: contain/none` (chaining blocked), else warn | coverage is computed from size, not from the current scroll position |
| `touch-action-block` | `touch-action: none` over ≥ 50 % of the viewport, outside canvas, video, iframe | warn | nested elements under a reported one are not reported again |
| `unreachable-fixed` | a fixed box taller than half the viewport that extends past it and cannot scroll itself | error | the landscape-phone and open-keyboard case |
| `ios-input-zoom` | a text-like input, select or textarea with computed `font-size` < 16 px | warn | iOS Safari zooms the page on focus below 16 px, in any browser on iOS |
| `non-composited-animation` | running animations (`document.getAnimations()`) classified per property | error for layout, warn for paint, info for engine-dependent | transitions show up as `CSSTransition` with their property |
| `latent-transition` | non-zero `transition-duration` on `all` or a layout property | warn | catches the defect before the state change that triggers it |
| `layer-memory` | Σ over promoted elements (`will-change`, 3D transforms) of min(w, 3vw) · min(h, 3vh) · dpr² · 4 bytes, against `layerBudgetMB` | warn | a DOM-side lower bound; the CDP LayerTree recipe gives the engine's figure |
| `blocking-scroll-listener` | listeners recorded at registration (the probe wraps `addEventListener` at init); non-passive touch/wheel listeners on connected targets | warn over the viewport or on roots, else info | root listeners default to passive; the test driver's own listeners (Playwright's hit-target interceptor) are recognized by stack and excluded |

A finding id for the gate is `rule:selector` (`clipped-text:h1#title`). Selectors prefer
`data-testid`, then a non-generated id, then a short `nth-of-type` path: they survive class-name
churn.

## 3. Intrinsic sizing blowouts, from the specs

- **Flex items have an automatic minimum size** (CSS Flexbox §4.5): `min-width: auto` resolves
  to the item's min-content size on the main axis, unless the item is a scroll container. A flex
  item holding an unbreakable string refuses to shrink below it and pushes its siblings out of
  the container. The fix is `min-width: 0` (or `min-height: 0` in a column) on that item, plus a
  wrapping or truncation strategy for the content.
- **`1fr` is `minmax(auto, 1fr)`** (CSS Grid §7.2.4): the track's minimum is its items' automatic
  minimum contribution, so a track grows to fit its widest item. The fix is
  `minmax(0, 1fr)` tracks and `min-width: 0` on the item.
- **A column flex child at `min-height: auto` defeats `overflow: auto`**: it grows instead of
  scrolling, and the scroll lands on the next ancestor or nowhere. That is the "inner panel
  doesn't scroll" bug, detected as a column `flex-blowout` or an `unreachable-content`.
- **`h-full` / `height: 100%` without a definite-height parent** resolves to `auto`: the same
  failure, one level up.

## 4. Sweeping the parameter space

A layout is a function L(w, h, s, c) of viewport width, height, font scale and content. It is
piecewise: it changes shape only where a query flips or content wraps.

**The matrix.** `scripts/breakpoints.py` reads the built CSS and returns, per font scale, the
integers on both sides of every media threshold, plus floor (320, WCAG 1.4.10) and ceiling.
Container thresholds are listed apart: they are container sizes, so drive them through a harness
that sizes the container, or through viewport widths that put the container there.

- **em and rem in media queries are relative to the user's default font size**, not to the root's
  `font-size`. With a 20 px default a `40rem` breakpoint fires at 800 px. Set the default with
  CDP `Page.setFontSizes` in Chromium (driver-recipes.md). In WebKit and Firefox, a root
  `font-size` override scales rem but does not move media queries, so the matrix there is the
  px one.
- **Zoom is a narrower viewport at a higher DPR**: 400 % zoom on a 1280 px window is a 320 CSS px
  viewport at DPR × 4. WCAG 1.4.10 (Reflow) is that cell: no two-dimensional scrolling at 320.
- **Text spacing** (WCAG 1.4.12): inject `* { line-height: 1.5 !important; letter-spacing: 0.12em
  !important; word-spacing: 0.16em !important } p { margin-bottom: 2em !important }` and audit
  again. No loss of content or function is the pass condition.
- **Heights** matter on phones: landscape is 320–430 px tall, and an open keyboard leaves ~250 px.
  Add them with `--extra-heights`.
- **Stress content**: a 60-character unbroken token (URL, hash, email), +40 % text length
  (German or Finnish UI strings), RTL (`dir="rtl"`), CJK without spaces, empty and single-item
  lists, 200-item lists, missing images.

**Covering arrays, not the full product.** Widths × scales × heights × content explodes. Run every
width at scale 1 with default content, then a pairwise (strength-2) covering array over the
other factors. Most layout defects are triggered by one factor or an interaction of two.

**The width sweep with bisection** finds undeclared breakpoints and the exact width where a
pathology starts:

1. Define a signature S(w): the set of audit finding ids, plus a coarse shape of the layout (for
   each snapshot key, which row it sits in and its order). It is cheap to compare.
2. Render at the matrix widths. Between two consecutive widths a and b with S(a) ≠ S(b), where
   no declared threshold lies in (a, b], bisect: render at ⌊(a+b)/2⌋ and recurse until b − a = 1.
3. The result is the exact width at which the layout changed shape without a query saying so (a
   wrap kicking in, a blowout starting). It is a finding with a precise reproduction.

## 5. Metamorphic relations: verification without a golden image

No oracle says what a page "should" look like at 731 px, but some relations between renderings
must hold. Each one is a test that needs no baseline:

- **Content conservation**: every text node visible at one width is reachable at every other
  width (visible, or inside a scrollable area), except content declared responsive-only.
- **Monotone room**: going from width w to w + Δ never creates a new `clipped-text`,
  `content-spill` or `overlap`.
- **Font-scale safety**: going from scale s to s' > s may wrap and grow, but never clips or
  overlaps.
- **Order stability**: the visual reading order of landmarks and controls (top-to-bottom, then
  inline direction) matches the DOM order at every width; a mismatch breaks keyboard and
  screen-reader navigation (WCAG 1.3.2, 2.4.3).
- **Idempotent settle**: auditing twice in a row returns the same findings; a difference means
  something is still moving (late fonts, async data, an animation).

## 6. Engine divergence and robustness margins

The same markup lays out differently per engine. In this skill's own fixture, a grid with
`1fr 1fr` tracks and a long URL blows out to 512 px in Chromium and WebKit, while Firefox wraps
the URL and keeps 150 px tracks. **A pass in one engine is not a pass.** Run the audit in every
engine you ship to (Chromium, WebKit, and Firefox if you support it).

Text metrics differ by engine and platform (shaping with HarfBuzz versus CoreText, hinting,
fallback fonts). A layout that only *just* fits on the CI engine overflows on another. Measure
the margin instead of the pass:

- **Slack**: for every truncation-prone box, slack = clientWidth − scrollWidth. Report boxes whose
  slack is under 3 % of their width as at risk.
- **Perturbation**: audit again with `letter-spacing: 0.02em` and `font-size: 104%` injected,
  roughly the spread of cross-engine text widths. A rule that appears only under perturbation is a
  robustness finding: it will fail somewhere real.
- **Self-hosted fonts** reduce, but do not remove, the divergence: shaping and rasterization still
  differ.
