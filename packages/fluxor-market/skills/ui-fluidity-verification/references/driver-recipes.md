# Driver recipes: Playwright and CDP

Every snippet below ran against Playwright 1.63 (Chromium, WebKit, Firefox) while this skill was
written. Adapt it to the project's own test runner and fixtures; keep the shape. `PROBE` is the
installed path of `assets/probe.js` (for example
`.harness/skills/ui-fluidity-verification/assets/probe.js`). `cdp` calls are Chromium only.

## Contents

1. Inject, serve, wait for readiness
2. A measured interaction
3. Auditing the matrix, with the user's font scale
4. Scrolling through the real gesture pipeline, throttled
5. Work counters
6. Composited layer memory
7. Touch bursts and coalescing
8. The width sweep with bisection
9. Interleaved A/B into `gate.py`
10. Prove the probe

## 1. Inject, serve, wait for readiness

```ts
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3,
  hasTouch: true, isMobile: true, reducedMotion: 'no-preference', locale: 'en-US', timezoneId: 'UTC' });
const page = await context.newPage();
await page.addInitScript({ path: PROBE });          // before any app code: sees hydration and listeners
await page.goto('http://127.0.0.1:3000/route');     // http, never file:// (LoAF attribution is empty there)
await page.evaluate(() => document.fonts.ready);
await expect(page.locator('[data-ready="true"]')).toBeVisible();   // the app's own readiness signal
const { vsyncMs } = await page.evaluate(() => __fluidity.calibrate());
```

## 2. A measured interaction

```ts
await page.evaluate(() => __fluidity.begin('save', { frames: false }));   // frames: true only for motion
await page.getByRole('button', { name: 'Save' }).click();
await expect(page.getByText('Saved')).toBeVisible();                       // the settled state
const w = await page.evaluate(() => __fluidity.end());
// w.interactions[0] = { events, target, durationMs, inputDelayMs, processingMs, presentationDelayMs }
// w.longAnimationFrames.forcedLayoutScripts, w.layoutShifts.count, w.layoutShifts.shifts[].sources
```

`support` in every report says what the engine measured. In WebKit and Firefox,
`longAnimationFrames`, `longTasks` and `layoutShifts` are `"unsupported"`, not zero.

## 3. Auditing the matrix, with the user's font scale

```ts
import { execFileSync } from 'node:child_process';
const m = JSON.parse(execFileSync('python3', [`${SKILL}/scripts/breakpoints.py`, '.next/static/css', '--json']).toString());
const findings = new Set<string>();
for (const [scale, { widths }] of Object.entries(m.matrix)) {
  const page = await context.newPage();
  await page.addInitScript({ path: PROBE });
  const cdp = await context.newCDPSession(page);                     // Chromium: moves em/rem media queries
  await cdp.send('Page.setFontSizes', { fontSizes: { standard: Math.round(16 * Number(scale)) } });
  for (const width of widths) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto(url);
    await page.evaluate(() => document.fonts.ready);
    const a = await page.evaluate(() => __fluidity.audit());
    for (const f of a.findings) if (f.severity === 'error') findings.add(`${f.rule}:${f.selector}@${width}x${scale}`);
  }
  await page.close();
}
```

`Page.setFontSizes` changes the default font size the way the user setting does: with a 20 px
default the root computes to 20 px and `(min-width: 40em)` stops matching at 700 px. WebKit and
Firefox have no equivalent in Playwright; a root `font-size` override there scales rem, not media
queries.

## 4. Scrolling through the real gesture pipeline, throttled

```ts
const cdp = await context.newCDPSession(page);
await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });          // the device class's calibrated rate
await page.evaluate(() => __fluidity.begin('feed-scroll', { frames: true }));
await cdp.send('Input.synthesizeScrollGesture', { x: 200, y: 400, yDistance: -1200, speed: 2400,
  gestureSourceType: 'touch' });
const s = await page.evaluate(() => __fluidity.end());   // s.frames: droppedFrames, worstDropStreak, pacing
await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
```

`synthesizeScrollGesture` goes through the compositor's gesture handling, so passive-listener
decisions and compositor scrolling are real. Measured: 1,200 px at 4× throttle, 0 dropped
frames. `page.mouse.wheel` is not the same path.

## 5. Work counters

```ts
await cdp.send('Performance.enable');
const metrics = async () => Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((x) => [x.name, x.value]));
const before = await metrics();
await page.getByRole('button', { name: 'Filter' }).click();
await expect(page.getByRole('list')).toHaveAttribute('data-state', 'filtered');
const after = await metrics();
const work = { layouts: after.LayoutCount - before.LayoutCount, styleRecalcs: after.RecalcStyleCount - before.RecalcStyleCount,
  scriptMs: (after.ScriptDuration - before.ScriptDuration) * 1000 };
```

Layout and style-recalc counts are structural for a deterministic code path (gate them exactly).
In the fixture, a read-after-write loop produced 29,519 layouts in one click: the count makes
layout thrashing undeniable where a duration only hints at it. `ScriptDuration` is timing.

## 6. Composited layer memory

```ts
const changed = new Promise<any[]>((resolve) => cdp.once('LayerTree.layerTreeDidChange', (e) => resolve(e.layers ?? [])));
await cdp.send('LayerTree.enable');
await page.evaluate(() => document.body.getBoundingClientRect());     // any change makes the tree report
const layers = await changed;
const dpr = await page.evaluate(() => devicePixelRatio);
const mb = layers.filter((l) => l.drawsContent).reduce((a, l) => a + l.width * l.height * 4 * dpr * dpr, 0) / 2 ** 20;
```

An upper bound (Chromium rasterizes tiles near the viewport only): compare it across builds and
against a per-class budget, together with `layers.length`.

## 7. Touch bursts and coalescing

```ts
const point = (x: number, y: number) => [{ x, y, id: 1 }];
await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: point(50, 300) });
// Eight moves in flight at once land within one frame, like a 240 Hz digitizer's samples.
await Promise.all(Array.from({ length: 8 }, (_, i) =>
  cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: point(60 + i * 10, 300) })));
await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
```

Measured: the eight moves arrived as two `pointermove` events, the second carrying seven
coalesced samples. A stroke or velocity computed from `pointermove` alone used two points out of
eight. Assert on the app's result (the stroke's point count, the drag's final velocity) that
every sample was used.

## 8. The width sweep with bisection

```ts
async function signature(page, width) {
  await page.setViewportSize({ width, height: 800 });
  await page.evaluate(() => document.fonts.ready);
  const a = await page.evaluate(() => __fluidity.audit());
  const s = await page.evaluate(() => __fluidity.snapshot());
  // rows: which line each box sits on, in order; findings: what is broken
  const tops = [...new Set(s.nodes.map((n) => Math.round(n.rect[1])))].sort((x, y) => x - y);
  const rows = s.nodes.map((n) => `${n.key}@${tops.indexOf(Math.round(n.rect[1]))}`).join('|');
  return JSON.stringify({ findings: a.findings.map((f) => `${f.rule}:${f.selector}`).sort(), rows });
}
async function undeclaredBreaks(page, widths, declared) {          // widths: sorted; declared: thresholds in px
  const out = [];
  async function bisect(a, sa, b, sb) {
    if (sa === sb || declared.some((t) => t > a && t <= b)) return;
    if (b - a === 1) return out.push(b);
    const mid = Math.floor((a + b) / 2);
    const sm = await signature(page, mid);
    await bisect(a, sa, mid, sm);
    await bisect(mid, sm, b, sb);
  }
  let prev = await signature(page, widths[0]);
  for (let i = 1; i < widths.length; i++) {
    const cur = await signature(page, widths[i]);
    await bisect(widths[i - 1], prev, widths[i], cur);
    prev = cur;
  }
  return out;                                                         // exact widths where the layout jumps
}
```

Use a coarse row signature: vertical positions shift continuously with width, so hashing exact
rects would see a "change" everywhere. A row change (a box moving to another line) or a new
finding is a discontinuity.

## 9. Interleaved A/B into `gate.py`

```ts
const pairs = { tap: { baseline: [], candidate: [] } };
for (let i = 0; i < 20; i++) {
  const order = i % 2 ? ['candidate', 'baseline'] : ['baseline', 'candidate'];   // alternate who goes first
  for (const side of order) {
    const page = await context.newPage();
    await page.addInitScript({ path: PROBE });
    await page.goto(side === 'baseline' ? BASELINE_URL : CANDIDATE_URL);       // two builds, same host
    // ... readiness, begin(), the interaction, end() ...
    pairs.tap[side].push(w.worstInteractionMs);
    await page.close();
  }
}
writeFileSync('metrics.json', JSON.stringify({
  calibration: { samples: calibrationRuns, maxCv: 0.05 },
  metrics: [
    { name: 'tap-ms', class: 'timing', paired: true, ...pairs.tap, minEffect: 0.1, minAbsolute: 8, budget: 200 },
    { name: 'audit', class: 'structural', baseline: baselineFindingIds, candidate: candidateFindingIds },
    { name: 'forced-layouts', class: 'structural', baseline: 0, candidate: forcedLayoutScripts },
    { name: 'unexpected-shifts', class: 'structural', candidate: shiftCount, budget: 0 },
  ],
}));
// python3 scripts/gate.py metrics.json   → exit 0 PASS, 1 FAIL, 3 INCONCLUSIVE
```

`minAbsolute: 8` because Event Timing durations come in 8 ms steps. The baseline build is the
merge base of the change, built once and served next to the candidate.

## 10. Prove the probe

Before trusting a gate built on the probe, prove the probe on the project's engines with a
fixture page that plants one instance of each pathology and one near-miss for each (an ellipsis
next to a clipped text, a reel next to a blowout, a spaced pair next to a crowded pair). Serve it
over http and run it in every engine you ship:

```ts
for (const engine of [chromium, webkit, firefox]) {
  const browser = await engine.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 700 } });
  await page.addInitScript({ path: PROBE });
  await page.goto('http://127.0.0.1:8765/fixture.html');
  const a = await page.evaluate(() => __fluidity.audit());
  // expect each planted rule once, no near-miss reported, a.summary.allowed counting the opt-outs
  await browser.close();
}
```

What a fixture taught while this skill was written: Playwright's own hit-target interceptor
registers a non-passive capturing `touchstart` on `window` during every action (the probe now
recognizes it by stack), and the same blown-out grid is 512 px wide in Chromium and WebKit and
fits in Firefox.
