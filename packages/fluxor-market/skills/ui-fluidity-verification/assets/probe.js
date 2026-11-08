/*
 * probe.js: the in-page instrument of ui-fluidity-verification.
 *
 * Inject it before any application code runs (Playwright: `page.addInitScript({ path })`), so it
 * sees hydration and every listener the app registers. Then drive the page and call, through
 * `page.evaluate`:
 *
 *   await __fluidity.calibrate()        the display's frame interval, measured on an idle page
 *   __fluidity.begin(label, { frames }) opens a measurement window (frames: sample rAF deltas)
 *   await __fluidity.end()              closes it: frames, long animation frames, long tasks,
 *                                       layout shifts and interactions inside the window
 *   __fluidity.audit(options)           layout pathologies of the current state (no side effects)
 *   __fluidity.animations()             running animations, classified by compositor safety
 *   __fluidity.snapshot(options)        geometry snapshot for scripts/layout_diff.py
 *
 * Rules it honors, because an instrument that perturbs what it measures is a second bug:
 * no dependencies, no network, no timers or rAF loops outside an open window, and every report
 * carries a `support` map: an API the engine lacks is reported as unsupported, never as zero.
 * An element (or an ancestor) opts out of named audit rules with
 * `data-fluidity-allow="rule another-rule"`; every opt-out is counted in the audit summary.
 */
(function (root) {
  'use strict';
  if (root.__fluidity) return;

  const VERSION = '1.0.0';
  /** Blink and WebKit lay out in 1/64 px units (LayoutUnit), Gecko in 1/60 px: below this, two
   * edges are the same edge. */
  const EPS = 1 / 60;
  const HAS_DOM = typeof document !== 'undefined' && typeof window !== 'undefined';

  // ---------------------------------------------------------------------------------------------
  // Pure helpers: no DOM, so the Node tests exercise them directly.
  // ---------------------------------------------------------------------------------------------

  function quantile(sorted, q) {
    if (!sorted.length) return NaN;
    const pos = (sorted.length - 1) * q;
    const lo = Math.floor(pos);
    const hi = Math.ceil(pos);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
  }

  function round(value, digits) {
    const f = Math.pow(10, digits === undefined ? 2 : digits);
    return Math.round(value * f) / f;
  }

  const COMPOSITOR = new Set(['transform', 'translate', 'rotate', 'scale', 'opacity']);
  /** Composited by some engines or versions only: never assume it on a phone. */
  const ENGINE_DEPENDENT = new Set(['filter', 'backdrop-filter', 'clip-path', 'background-color',
    'offset-distance', 'offset-path', 'offset-rotate']);
  const LAYOUT = /^(width|height|(min|max)-(width|height|inline-size|block-size)|inline-size|block-size|top|right|bottom|left|inset(-.+)?|margin(-.+)?|padding(-.+)?|border(-(top|right|bottom|left|inline|block)(-(start|end))?)?-width|border-width|font(-size|-weight|-family|-stretch)?|line-height|letter-spacing|word-spacing|flex(-.+)?|grid(-.+)?|gap|row-gap|column-gap|aspect-ratio|order|text-indent|white-space|display|position|columns?(-.+)?)$/;
  const IGNORED_KEYS = new Set(['offset', 'computedOffset', 'easing', 'composite']);

  function kebab(prop) {
    if (prop.startsWith('--')) return prop;
    return prop.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase()).replace(/^css-/, '')
      .replace(/^-?(webkit|moz|ms|o)-/, '');
  }

  /** Where the engine has to do the work to animate `prop`: 'compositor' (off the main thread),
   * 'engine-dependent', 'paint' (main thread, every frame) or 'layout' (main thread, the most
   * expensive). Registered custom properties animate on the main thread: 'paint' at least. */
  function classifyProperty(prop) {
    const p = kebab(prop);
    if (COMPOSITOR.has(p)) return 'compositor';
    if (ENGINE_DEPENDENT.has(p)) return 'engine-dependent';
    if (LAYOUT.test(p) || p === 'all') return 'layout';
    return 'paint';
  }

  /** Per-side amounts by which `inner` leaves `outer`; a side within `eps` counts as contained.
   * Rects are {left, top, right, bottom}. */
  function excess(inner, outer, eps) {
    const e = eps === undefined ? EPS : eps;
    const out = {
      left: outer.left - inner.left,
      top: outer.top - inner.top,
      right: inner.right - outer.right,
      bottom: inner.bottom - outer.bottom,
    };
    for (const k of Object.keys(out)) out[k] = out[k] > e ? out[k] : 0;
    return out;
  }

  function anyExcess(ex) {
    return ex.left > 0 || ex.top > 0 || ex.right > 0 || ex.bottom > 0;
  }

  function intersection(a, b) {
    const left = Math.max(a.left, b.left);
    const top = Math.max(a.top, b.top);
    const right = Math.min(a.right, b.right);
    const bottom = Math.min(a.bottom, b.bottom);
    return right > left && bottom > top ? { left, top, right, bottom } : null;
  }

  /** Index pairs [i, j] (i < j) of rects that overlap by more than `eps` on both axes. A sweep
   * over x: O(n log n + k) instead of comparing every pair. */
  function overlaps(rects, eps) {
    const e = eps === undefined ? EPS : eps;
    const order = rects.map((_, i) => i).sort((i, j) => rects[i].left - rects[j].left || i - j);
    const active = [];
    const pairs = [];
    for (const i of order) {
      const r = rects[i];
      for (let k = active.length - 1; k >= 0; k--) {
        if (rects[active[k]].right - e <= r.left) active.splice(k, 1);
      }
      for (const j of active) {
        const o = rects[j];
        const w = Math.min(o.right, r.right) - Math.max(o.left, r.left);
        const h = Math.min(o.bottom, r.bottom) - Math.max(o.top, r.top);
        if (w > e && h > e) pairs.push(i < j ? [i, j] : [j, i]);
      }
      active.push(i);
    }
    return pairs.sort((p, q) => p[0] - q[0] || p[1] - q[1]);
  }

  /** The device-pixel edge an engine paints for a layout edge: Blink and WebKit snap each edge
   * to the nearest device pixel. */
  function snap(x, dpr) {
    return Math.round(x * dpr) / dpr;
  }

  /** A hairline seam between two edges meant to touch (`endOfA`, `startOfB`, less than one
   * device pixel apart): the signed device-pixel gap (> 0) or overlap (< 0) they paint with, or 0. */
  function seam(endOfA, startOfB, dpr) {
    if (Math.abs(startOfB - endOfA) >= 1 / dpr) return 0;
    return round(snap(startOfB, dpr) - snap(endOfA, dpr), 4);
  }

  /** Frame statistics from rAF timestamps. `vsyncMs` should come from `calibrate()`; without it
   * the 25th percentile of the deltas stands in, which is blind to a uniformly halved frame rate.
   * A delta longer than 1.5 intervals dropped round(delta / interval) - 1 frames. */
  function frameStats(times, vsyncMs) {
    const deltas = [];
    for (let i = 1; i < times.length; i++) deltas.push(times[i] - times[i - 1]);
    if (!deltas.length) return { frames: 0 };
    const sorted = deltas.slice().sort((a, b) => a - b);
    const vsync = vsyncMs || quantile(sorted, 0.25);
    let dropped = 0;
    let streak = 0;
    let worstStreak = 0;
    for (const d of deltas) {
      const missed = d > 1.5 * vsync ? Math.round(d / vsync) - 1 : 0;
      dropped += missed;
      streak = missed ? streak + missed : 0;
      worstStreak = Math.max(worstStreak, streak);
    }
    const median = quantile(sorted, 0.5);
    return {
      frames: deltas.length,
      vsyncMs: round(vsync),
      vsyncSource: vsyncMs ? 'calibrated' : 'p25-estimate',
      medianMs: round(median),
      p95Ms: round(quantile(sorted, 0.95)),
      maxMs: round(sorted[sorted.length - 1]),
      droppedFrames: dropped,
      droppedRatio: round(dropped / (dropped + deltas.length), 4),
      worstDropStreak: worstStreak,
      pacing: round(quantile(sorted, 0.95) / median, 3),
    };
  }

  /** WCAG 2.2 SC 2.5.8 spacing exception: an undersized target passes when a circle of diameter
   * `min` centered on it intersects no other target and no other undersized target's circle.
   * `targets` are rects; returns the indexes of the undersized ones that fail. */
  function targetSpacingFailures(targets, min) {
    const r = min / 2;
    const center = (t) => ({ x: (t.left + t.right) / 2, y: (t.top + t.bottom) / 2 });
    const small = targets.map((t, i) => i).filter((i) => {
      const t = targets[i];
      return t.right - t.left < min - EPS || t.bottom - t.top < min - EPS;
    });
    const fails = [];
    for (const i of small) {
      const c = center(targets[i]);
      let bad = false;
      for (let j = 0; j < targets.length && !bad; j++) {
        if (j === i) continue;
        const t = targets[j];
        const dx = Math.max(t.left - c.x, 0, c.x - t.right);
        const dy = Math.max(t.top - c.y, 0, c.y - t.bottom);
        if (dx * dx + dy * dy < r * r - EPS) bad = true;
        else if (small.includes(j)) {
          const o = center(t);
          if (Math.hypot(o.x - c.x, o.y - c.y) < min - EPS) bad = true;
        }
      }
      if (bad) fails.push(i);
    }
    return fails;
  }

  const geometry = {
    EPS, quantile, classifyProperty, excess, intersection, overlaps, snap, seam, frameStats,
    targetSpacingFailures,
  };

  const api = { version: VERSION, geometry };
  root.__fluidity = api;
  if (!HAS_DOM) return;

  // ---------------------------------------------------------------------------------------------
  // Observers, installed at injection time so hydration and the first frames are seen.
  // ---------------------------------------------------------------------------------------------

  const supported = typeof PerformanceObserver !== 'undefined'
    ? new Set(PerformanceObserver.supportedEntryTypes || []) : new Set();
  const support = {
    longAnimationFrame: supported.has('long-animation-frame'),
    longTask: supported.has('longtask'),
    layoutShift: supported.has('layout-shift'),
    eventTiming: supported.has('event'),
    getAnimations: typeof document.getAnimations === 'function',
    checkVisibility: typeof Element !== 'undefined' && 'checkVisibility' in Element.prototype,
  };
  const CAP = 2000;
  const buffers = { 'long-animation-frame': [], longtask: [], 'layout-shift': [], event: [] };
  const observers = [];

  function observe(type, options) {
    if (!supported.has(type)) return;
    try {
      const obs = new PerformanceObserver((list) => {
        const buf = buffers[type];
        for (const entry of list.getEntries()) {
          buf.push(entry);
          if (buf.length > CAP) buf.shift();
        }
      });
      obs.observe(Object.assign({ type, buffered: true }, options));
      observers.push({ type, obs });
    } catch (err) {
      support[type] = false;
    }
  }
  observe('long-animation-frame');
  observe('longtask');
  observe('layout-shift');
  observe('event', { durationThreshold: 16 });

  function flush() {
    for (const { type, obs } of observers) {
      for (const entry of obs.takeRecords()) buffers[type].push(entry);
    }
  }

  // Scroll-blocking listeners: recorded as the app registers them, so the audit can name them.
  // The test driver registers its own (Playwright's hit-target interceptor: a capturing,
  // non-passive touchstart on window during every action); its frames in the stack exclude it.
  const SCROLL_EVENTS = new Set(['touchstart', 'touchmove', 'wheel', 'mousewheel']);
  const DRIVER_FRAMES = /addHitTargetInterceptor|__playwright|playwright_evaluation|puppeteer_evaluation_script|__webdriver|cypress/i;
  const listeners = [];
  const supportsWeakRef = typeof WeakRef !== 'undefined';
  try {
    const proto = EventTarget.prototype;
    const add = proto.addEventListener;
    const remove = proto.removeEventListener;
    proto.addEventListener = function (type, fn, options) {
      if (SCROLL_EVENTS.has(type) && fn && !DRIVER_FRAMES.test(String(new Error().stack))) {
        const explicit = options && typeof options === 'object' && 'passive' in options
          ? Boolean(options.passive) : null;
        const capture = typeof options === 'boolean' ? options : Boolean(options && options.capture);
        listeners.push({ ref: supportsWeakRef ? new WeakRef(this) : this, type, fn, capture, explicit });
      }
      return add.call(this, type, fn, options);
    };
    proto.removeEventListener = function (type, fn, options) {
      if (SCROLL_EVENTS.has(type)) {
        const capture = typeof options === 'boolean' ? options : Boolean(options && options.capture);
        const i = listeners.findIndex((l) => l.type === type && l.fn === fn && l.capture === capture
          && (supportsWeakRef ? l.ref.deref() : l.ref) === this);
        if (i >= 0) listeners.splice(i, 1);
      }
      return remove.call(this, type, fn, options);
    };
    support.listenerTracking = true;
  } catch (err) {
    support.listenerTracking = false;
  }

  // ---------------------------------------------------------------------------------------------
  // DOM helpers
  // ---------------------------------------------------------------------------------------------

  function rectOf(el) {
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
  }

  function plain(r) {
    return { x: round(r.left), y: round(r.top), width: round(r.right - r.left), height: round(r.bottom - r.top) };
  }

  function describe(el) {
    if (!el || el.nodeType !== 1) {
      return el === document ? 'document' : el === window ? 'window' : String(el && el.nodeName);
    }
    const tag = el.tagName.toLowerCase();
    const testid = el.getAttribute('data-testid');
    if (testid) return `${tag}[data-testid="${testid}"]`;
    if (el.id && !generatedId(el.id)) return `${tag}#${el.id}`;
    const parts = [];
    let node = el;
    for (let depth = 0; node && node.nodeType === 1 && depth < 4; depth++) {
      let part = node.tagName.toLowerCase();
      const tid = node.getAttribute('data-testid');
      if (tid) { parts.unshift(`${part}[data-testid="${tid}"]`); break; }
      if (node.id && !generatedId(node.id)) { parts.unshift(`${part}#${node.id}`); break; }
      const parent = node.parentElement;
      if (parent) {
        const same = Array.prototype.filter.call(parent.children, (c) => c.tagName === node.tagName);
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(' > ');
  }

  /** Ids a framework generates (React useId, Radix, Headless UI) change between builds. */
  function generatedId(id) {
    return /[:«»]/.test(id) || /^(radix-|headlessui-|_r_|r[0-9a-z]{1,3}$)/.test(id) || /\d{4,}/.test(id);
  }

  function allowed(el, rule) {
    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
      const allow = node.getAttribute('data-fluidity-allow');
      if (allow && allow.split(/\s+/).includes(rule)) return true;
    }
    return false;
  }

  function rendered(el, cs) {
    if (support.checkVisibility) {
      if (!el.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) return false;
    } else if (cs.display === 'none' || cs.visibility === 'hidden') {
      return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function paddingBox(el, r, cs) {
    const bl = parseFloat(cs.borderLeftWidth) || 0;
    const bt = parseFloat(cs.borderTopWidth) || 0;
    const br = parseFloat(cs.borderRightWidth) || 0;
    const bb = parseFloat(cs.borderBottomWidth) || 0;
    return { left: r.left + bl, top: r.top + bt, right: r.right - br, bottom: r.bottom - bb };
  }

  function contentBox(el, r, cs) {
    const p = paddingBox(el, r, cs);
    return {
      left: p.left + (parseFloat(cs.paddingLeft) || 0),
      top: p.top + (parseFloat(cs.paddingTop) || 0),
      right: p.right - (parseFloat(cs.paddingRight) || 0),
      bottom: p.bottom - (parseFloat(cs.paddingBottom) || 0),
    };
  }

  const scrolls = (v) => v === 'auto' || v === 'scroll';
  const clips = (v) => v === 'hidden' || v === 'clip';
  const inFlow = (cs) => cs.position !== 'absolute' && cs.position !== 'fixed' && cs.cssFloat === 'none'
    && cs.display !== 'contents';

  function composedContains(outer, inner) {
    for (let node = inner; node; node = node.parentNode || node.host) {
      if (node === outer) return true;
    }
    return false;
  }

  function deepElementFromPoint(x, y) {
    let hit = document.elementFromPoint(x, y);
    while (hit && hit.shadowRoot) {
      const inner = hit.shadowRoot.elementFromPoint(x, y);
      if (!inner || inner === hit) break;
      hit = inner;
    }
    return hit;
  }

  const INTERACTIVE = 'a[href], button, input:not([type="hidden"]), select, textarea, summary, '
    + '[role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="switch"], '
    + '[role="tab"], [role="menuitem"], [role="option"], [tabindex]:not([tabindex="-1"]), '
    + '[contenteditable=""], [contenteditable="true"]';

  /** An inline link inside running text is exempt from the target-size rule (SC 2.5.8). */
  function inlineInText(el, cs) {
    if (!cs.display.startsWith('inline') || cs.display === 'inline-block' || cs.display === 'inline-flex') {
      return false;
    }
    const parent = el.parentElement;
    if (!parent) return false;
    return Array.prototype.some.call(parent.childNodes, (n) => n.nodeType === 3 && n.textContent.trim());
  }

  // ---------------------------------------------------------------------------------------------
  // Windows: frames, long animation frames, long tasks, shifts, interactions
  // ---------------------------------------------------------------------------------------------

  let vsyncMs = 0;
  let open = null;

  function nextFrame() {
    return new Promise((resolve) => requestAnimationFrame(resolve));
  }

  /** Measures the display's frame interval: the median rAF delta over `frames` idle frames. Call
   * it once per page, before any window, while nothing animates. */
  api.calibrate = async function calibrate(frames) {
    const n = frames || 30;
    const times = [];
    for (let i = 0; i <= n; i++) times.push(await nextFrame());
    const deltas = [];
    for (let i = 1; i < times.length; i++) deltas.push(times[i] - times[i - 1]);
    deltas.sort((a, b) => a - b);
    vsyncMs = quantile(deltas, 0.5);
    return { vsyncMs: round(vsyncMs), refreshHz: round(1000 / vsyncMs, 1), frames: n };
  };

  api.begin = function begin(label, options) {
    if (open) throw new Error(`__fluidity: window "${open.label}" is still open`);
    const opts = options || {};
    flush();
    open = { label: label || 'window', start: performance.now(), times: [], sampling: Boolean(opts.frames) };
    if (open.sampling) {
      const state = open;
      const tick = (t) => {
        if (open !== state) return;
        state.times.push(t);
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  };

  api.end = async function end() {
    if (!open) throw new Error('__fluidity: no window is open');
    const state = open;
    const stop = performance.now();
    // Two frames let the last frame's entries be created; then the window closes.
    await nextFrame();
    await nextFrame();
    open = null;
    flush();
    const inside = (e) => e.startTime >= state.start && e.startTime <= stop;

    const loafs = buffers['long-animation-frame'].filter(inside);
    const scripts = [];
    for (const f of loafs) for (const s of f.scripts || []) scripts.push(s);
    const loaf = support.longAnimationFrame ? {
      count: loafs.length,
      totalBlockingMs: round(loafs.reduce((a, f) => a + (f.blockingDuration || 0), 0)),
      forcedLayoutScripts: scripts.filter((s) => s.forcedStyleAndLayoutDuration > 0).length,
      worst: loafs.slice().sort((a, b) => b.duration - a.duration).slice(0, 5).map((f) => ({
        startMs: round(f.startTime - state.start),
        durationMs: round(f.duration),
        blockingMs: round(f.blockingDuration),
        styleAndLayoutMs: f.styleAndLayoutStart ? round(f.startTime + f.duration - f.styleAndLayoutStart) : null,
        scripts: (f.scripts || []).slice().sort((a, b) => b.duration - a.duration).slice(0, 3).map((s) => ({
          invoker: s.invoker,
          invokerType: s.invokerType,
          source: [s.sourceURL, s.sourceFunctionName].filter(Boolean).join(' '),
          durationMs: round(s.duration),
          forcedStyleAndLayoutMs: round(s.forcedStyleAndLayoutDuration || 0),
        })),
      })),
    } : 'unsupported';

    const tasks = buffers.longtask.filter(inside);
    const longTasks = support.longTask ? {
      count: tasks.length,
      totalMs: round(tasks.reduce((a, t) => a + t.duration, 0)),
      totalBlockingMs: round(tasks.reduce((a, t) => a + Math.max(0, t.duration - 50), 0)),
    } : 'unsupported';

    const shifts = buffers['layout-shift'].filter(inside);
    const unexpected = shifts.filter((s) => !s.hadRecentInput);
    const layoutShifts = support.layoutShift ? {
      count: unexpected.length,
      withRecentInput: shifts.length - unexpected.length,
      score: round(unexpected.reduce((a, s) => a + s.value, 0), 4),
      shifts: unexpected.slice(0, 10).map((s) => ({
        value: round(s.value, 4),
        startMs: round(s.startTime - state.start),
        sources: (s.sources || []).map((src) => ({
          node: src.node ? describe(src.node) : null,
          from: plain(src.previousRect),
          to: plain(src.currentRect),
        })),
      })),
    } : 'unsupported';

    // One interaction (pointerdown, pointerup, click...) is several event entries: its duration
    // is the longest one, and its phases span all of them, as INP attribution measures them.
    const byInteraction = new Map();
    for (const e of buffers.event.filter(inside)) {
      if (!e.interactionId) continue;
      if (!byInteraction.has(e.interactionId)) byInteraction.set(e.interactionId, []);
      byInteraction.get(e.interactionId).push(e);
    }
    const interactions = support.eventTiming ? Array.from(byInteraction.values()).map((list) => {
      const start = Math.min.apply(null, list.map((e) => e.startTime));
      const end = Math.max.apply(null, list.map((e) => e.startTime + e.duration));
      const procStart = Math.min.apply(null, list.map((e) => e.processingStart));
      const procEnd = Math.max.apply(null, list.map((e) => e.processingEnd));
      const target = list.map((e) => e.target).find(Boolean);
      return {
        events: list.map((e) => e.name),
        target: target ? describe(target) : null,
        startMs: round(start - state.start),
        durationMs: Math.max.apply(null, list.map((e) => e.duration)),
        inputDelayMs: round(procStart - start),
        processingMs: round(procEnd - procStart),
        presentationDelayMs: round(Math.max(0, end - procEnd)),
      };
    }) : 'unsupported';

    return {
      probe: VERSION,
      label: state.label,
      durationMs: round(stop - state.start),
      support: Object.assign({}, support),
      frames: state.sampling ? frameStats(state.times, vsyncMs) : null,
      longAnimationFrames: loaf,
      longTasks,
      layoutShifts,
      interactions,
      worstInteractionMs: Array.isArray(interactions) && interactions.length
        ? Math.max.apply(null, interactions.map((i) => i.durationMs)) : null,
    };
  };

  // ---------------------------------------------------------------------------------------------
  // Animations
  // ---------------------------------------------------------------------------------------------

  function collectAnimations() {
    return document.getAnimations().filter((a) => a.playState === 'running' || a.playState === 'pending').map((a) => {
      const props = new Set();
      if (a.transitionProperty) props.add(a.transitionProperty);
      const effect = a.effect;
      if (effect && typeof effect.getKeyframes === 'function') {
        for (const frame of effect.getKeyframes()) {
          for (const key of Object.keys(frame)) if (!IGNORED_KEYS.has(key)) props.add(kebab(key));
        }
      }
      const classes = {};
      for (const p of props) classes[p] = classifyProperty(p);
      const target = (effect && effect.target) || null;
      return {
        name: a.animationName || a.transitionProperty || a.id || a.constructor.name,
        kind: a.constructor.name,
        targetEl: target,
        target: target ? describe(target) : null,
        properties: classes,
        worst: ['layout', 'paint', 'engine-dependent', 'compositor'].find((c) => Object.values(classes).includes(c))
          || 'compositor',
      };
    });
  }

  api.animations = function animations() {
    if (!support.getAnimations) return 'unsupported';
    return collectAnimations().map((a) => {
      const out = Object.assign({}, a);
      delete out.targetEl;
      return out;
    });
  };

  // ---------------------------------------------------------------------------------------------
  // Layout audit
  // ---------------------------------------------------------------------------------------------

  const RULES = ['viewport-overflow-x', 'unreachable-content', 'content-spill', 'clipped-text',
    'flex-blowout', 'grid-blowout', 'overlap', 'subpixel-seam', 'occluded-target', 'target-size',
    'scroll-trap', 'touch-action-block', 'unreachable-fixed', 'ios-input-zoom',
    'non-composited-animation', 'latent-transition', 'layer-memory', 'blocking-scroll-listener'];

  api.rules = RULES.slice();

  /** Layout findings for the current state. Options: `root` (element, default body), `rules`
   * (subset of `__fluidity.rules`), `minTarget` (24), `minTargetCoarse` (44), `trapCoverage`
   * (0.85), `layerBudgetMB` (64), `maxElements` (6000), `maxPerRule` (25). */
  api.audit = function audit(options) {
    const opts = Object.assign({
      root: document.body, minTarget: 24, minTargetCoarse: 44, trapCoverage: 0.85,
      layerBudgetMB: 64, maxElements: 6000, maxPerRule: 25,
    }, options || {});
    const active = new Set(opts.rules || RULES);
    const findings = [];
    const counts = {};
    const allowedCount = {};
    const dpr = window.devicePixelRatio || 1;
    const de = document.documentElement;
    const vw = de.clientWidth;
    const vh = de.clientHeight;
    const viewport = { left: 0, top: 0, right: vw, bottom: vh };

    function report(rule, severity, el, message, detail) {
      if (!active.has(rule)) return;
      if (el && el.nodeType === 1 && allowed(el, rule)) {
        allowedCount[rule] = (allowedCount[rule] || 0) + 1;
        return;
      }
      counts[rule] = (counts[rule] || 0) + 1;
      if (counts[rule] > opts.maxPerRule) return;
      findings.push({ rule, severity, selector: el ? describe(el) : null, message, detail: detail || {} });
    }

    // One pass: computed style, rect and flags for every element under root. SVG internals are
    // drawing, not layout boxes: they overlap by nature and are skipped.
    const nodes = [];
    const info = new Map();
    const svgNs = 'http://www.w3.org/2000/svg';
    const walker = document.createTreeWalker(opts.root || document.body, 1, {
      acceptNode: (el) => (el.namespaceURI === svgNs && el.localName !== 'svg' ? 2 : 1),
    });
    for (let el = walker.currentNode; el && nodes.length < opts.maxElements; el = walker.nextNode()) {
      const cs = getComputedStyle(el);
      if (!rendered(el, cs)) continue;
      let p = el.parentElement;
      while (p && !info.has(p)) p = p.parentElement; // display: contents has no box of its own
      const parentInfo = p ? info.get(p) : null;
      const isRootBox = el === document.body || el === de; // their overflow belongs to the viewport
      const item = {
        el, cs, rect: rectOf(el), parent: p,
        clipX: parentInfo ? parentInfo.clipX || parentInfo.selfClipX : false,
        selfClipX: !isRootBox && (scrolls(cs.overflowX) || clips(cs.overflowX)),
      };
      info.set(el, item);
      nodes.push(item);
    }
    const truncated = nodes.length >= opts.maxElements;

    // viewport-overflow-x and masked overflow on the root.
    const rootCs = getComputedStyle(de);
    const bodyCs = getComputedStyle(document.body);
    const viewportOverflowX = clips(rootCs.overflowX) ? rootCs.overflowX
      : (rootCs.overflowX === 'visible' ? bodyCs.overflowX : rootCs.overflowX);
    const viewportOverflowY = clips(rootCs.overflowY) ? rootCs.overflowY
      : (rootCs.overflowY === 'visible' ? bodyCs.overflowY : rootCs.overflowY);
    const culprits = [];
    for (const n of nodes) {
      if (n.clipX || n.el === document.body) continue;
      const fixed = n.cs.position === 'fixed';
      const right = fixed ? n.rect.right : n.rect.right + window.scrollX;
      if (right > vw + EPS && !culprits.some((c) => c.el.contains(n.el))) culprits.push(n);
    }
    if (culprits.length) {
      const scrolling = de.scrollWidth > vw && !clips(viewportOverflowX);
      report('viewport-overflow-x', scrolling ? 'error' : 'warn', culprits[0].el,
        scrolling ? `The page scrolls sideways: content is ${de.scrollWidth - vw}px wider than the viewport.`
          : `Content passes the right edge and the root's overflow-x: ${viewportOverflowX} hides it: it is cut, not fixed.`,
        { viewportWidth: vw, scrollWidth: de.scrollWidth, culprits: culprits.slice(0, 8).map((c) => ({
          selector: describe(c.el), overflowPx: round(c.rect.right + (c.cs.position === 'fixed' ? 0 : window.scrollX) - vw) })) });
    }

    // unreachable-content: the root cannot scroll, the document is taller than the viewport.
    if (clips(viewportOverflowY) && de.scrollHeight > vh + 1) {
      report('unreachable-content', 'error', document.body,
        `The root has overflow-y: ${viewportOverflowY} and the document is ${de.scrollHeight - vh}px taller than the viewport: that content cannot be reached (a scroll lock left behind?).`,
        { viewportHeight: vh, scrollHeight: de.scrollHeight });
    }

    // clipped-text: text cut by overflow hidden/clip with no ellipsis or line clamp.
    for (const n of nodes) {
      const { el, cs } = n;
      const cx = clips(cs.overflowX) && el.scrollWidth > el.clientWidth + 1;
      const cy = clips(cs.overflowY) && el.scrollHeight > el.clientHeight + 1;
      if (!cx && !cy) continue;
      if (n.rect.width <= 1 || n.rect.height <= 1) continue; // visually-hidden pattern
      const wrap = `${cs.whiteSpace} ${cs.textWrapMode || cs.textWrap || ''}`;
      const intentional = (cx && cs.textOverflow === 'ellipsis' && /nowrap|pre(?!-wrap|-line)/.test(wrap))
        || (cy && cs.webkitLineClamp && cs.webkitLineClamp !== 'none');
      if (intentional) continue;
      const pb = paddingBox(el, n.rect, n.cs);
      const tw = document.createTreeWalker(el, 4);
      let cut = null;
      for (let t = tw.nextNode(), seen = 0; t && seen < 300 && !cut; t = tw.nextNode(), seen++) {
        if (!t.textContent.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(t);
        for (const r of range.getClientRects()) {
          const ex = excess(r, pb);
          if ((cx && (ex.left || ex.right)) || (cy && (ex.top || ex.bottom))) { cut = ex; break; }
        }
      }
      if (cut) {
        report('clipped-text', 'error', el,
          'Text is cut off by overflow hidden/clip with no ellipsis or line clamp: content silently lost.',
          { clippedPx: { left: round(cut.left), top: round(cut.top), right: round(cut.right), bottom: round(cut.bottom) } });
      }
    }

    // flex-blowout, grid-blowout, subpixel-seam. A container reported here is not reported
    // again as a content spill: one cause, one finding.
    const blownOut = new Set();
    for (const n of nodes) {
      const { el, cs, rect } = n;
      const isFlex = cs.display === 'flex' || cs.display === 'inline-flex';
      const isGrid = cs.display === 'grid' || cs.display === 'inline-grid';
      if (!isFlex && !isGrid) continue;
      const cb = contentBox(el, rect, cs);
      const kids = Array.prototype.filter.call(el.children, (c) => info.has(c) && inFlow(info.get(c).cs));
      if (isFlex) {
        const row = cs.flexDirection.startsWith('row');
        const scroller = row ? scrolls(cs.overflowX) : scrolls(cs.overflowY);
        if (!scroller) {
          const out = kids.filter((c) => {
            const ex = excess(info.get(c).rect, cb);
            return row ? ex.left || ex.right : ex.top || ex.bottom;
          });
          if (out.length) {
            const prop = row ? 'minWidth' : 'minHeight';
            const blame = kids.filter((c) => info.get(c).cs[prop] === 'auto')
              .sort((a, b) => (row ? info.get(b).rect.width - info.get(a).rect.width : info.get(b).rect.height - info.get(a).rect.height))
              .slice(0, 3).map((c) => describe(c));
            blownOut.add(el);
            report('flex-blowout', 'error', el,
              `Flex items overflow their ${row ? 'row' : 'column'}: an item refuses to shrink below its content (min-${row ? 'width' : 'height'}: auto).`,
              { axis: row ? 'x' : 'y', overflowing: out.slice(0, 5).map((c) => describe(c)), suspects: blame,
                hint: `min-${row ? 'width' : 'height'}: 0 on the suspect, or a wrap strategy` });
          }
        }
        // Seams between touching items (no gap) in a row.
        const gap = parseFloat(row ? cs.columnGap : cs.rowGap) || 0;
        if (gap === 0 && kids.length > 1) {
          for (let i = 1; i < kids.length; i++) {
            const a = info.get(kids[i - 1]).rect;
            const b = info.get(kids[i]).rect;
            const s = row ? seam(a.right, b.left, dpr) : seam(a.bottom, b.top, dpr);
            if (s !== 0) {
              report('subpixel-seam', 'warn', kids[i],
                `Touching items paint ${s > 0 ? 'a gap' : 'an overlap'} of ${Math.abs(s)}px at DPR ${dpr}: fractional sizes snap to different device pixels.`,
                { seamPx: s, dpr });
            }
          }
        }
      } else {
        const tracks = cs.gridTemplateColumns.split(/\s+/).filter((t) => /px$/.test(t)).map(parseFloat);
        if (tracks.length && !scrolls(cs.overflowX)) {
          const gap = parseFloat(cs.columnGap) || 0;
          const used = tracks.reduce((a, t) => a + t, 0) + gap * (tracks.length - 1);
          const width = cb.right - cb.left;
          if (used > width + EPS) {
            const blame = kids.filter((c) => info.get(c).cs.minWidth === 'auto')
              .sort((a, b) => info.get(b).rect.width - info.get(a).rect.width).slice(0, 3).map((c) => describe(c));
            blownOut.add(el);
            report('grid-blowout', 'error', el,
              `Grid tracks need ${round(used)}px in ${round(width)}px: a track grew to fit its content (1fr is minmax(auto, 1fr)).`,
              { tracksPx: tracks.map((t) => round(t)), gapPx: gap, suspects: blame,
                hint: 'minmax(0, 1fr) tracks and min-width: 0 on the suspect' });
          }
        }
      }
    }

    // content-spill: the deepest boxes whose IN-FLOW content overflows them while overflow is
    // visible. Positioned and transformed descendants (menus, tooltips) also grow scrollWidth and
    // scrollHeight, so the overflow must be traced to an in-flow child or to the box's own text.
    function textLeaves(el, box) {
      for (const t of el.childNodes) {
        if (t.nodeType !== 3 || !t.textContent.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(t);
        for (const r of range.getClientRects()) if (anyExcess(excess(r, box))) return true;
      }
      return false;
    }
    const spill = new Map();
    for (const n of nodes) {
      const { el, cs } = n;
      if (el === document.body || cs.display === 'inline') continue;
      const xs = cs.overflowX === 'visible' && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0;
      const ys = cs.overflowY === 'visible' && el.scrollHeight > el.clientHeight + 1 && el.clientHeight > 0;
      if (!xs && !ys) continue;
      const pb = paddingBox(el, n.rect, cs);
      const children = Array.prototype.filter.call(el.children, (c) => info.has(c)
        && inFlow(info.get(c).cs) && info.get(c).cs.transform === 'none'
        && anyExcess(excess(info.get(c).rect, pb)));
      if (children.length || textLeaves(el, pb)) spill.set(el, children);
    }
    for (const [el, overflowing] of spill) {
      let deeper = false;
      for (const other of spill.keys()) if (other !== el && el.contains(other)) { deeper = true; break; }
      if (deeper || blownOut.has(el)) continue;
      const children = overflowing.slice(0, 5).map((c) => describe(c));
      report('content-spill', 'warn', el,
        `Content overflows this box (${el.scrollWidth}x${el.scrollHeight} in ${el.clientWidth}x${el.clientHeight}) and spills over its neighbors.`,
        { scrollWidth: el.scrollWidth, clientWidth: el.clientWidth, scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight, children, hint: children.length ? 'a child is wider than the box: min-width: 0 on it, or let it wrap'
            : 'unbreakable text: overflow-wrap: anywhere, or truncate on purpose' });
    }

    // overlap: in-flow block-level siblings that collide. Inline boxes that wrap have bounding
    // boxes spanning whole lines, and a stuck sticky box covers its siblings by design.
    const byParent = new Map();
    for (const n of nodes) {
      if (!inFlow(n.cs) || n.cs.transform !== 'none' || n.cs.display === 'inline' || n.cs.position === 'sticky') continue;
      const p = n.el.parentElement;
      if (!p || !info.has(p)) continue;
      if (!byParent.has(p)) byParent.set(p, []);
      byParent.get(p).push(n);
    }
    for (const [parent, kids] of byParent) {
      if (kids.length < 2) continue;
      const pcs = info.get(parent).cs;
      const grid = pcs.display === 'grid' || pcs.display === 'inline-grid';
      for (const [i, j] of overlaps(kids.map((k) => k.rect))) {
        const a = kids[i];
        const b = kids[j];
        if (grid && (a.cs.gridRowStart !== 'auto' || a.cs.gridColumnStart !== 'auto')
          && (b.cs.gridRowStart !== 'auto' || b.cs.gridColumnStart !== 'auto')) continue; // stacked on purpose
        const negative = [a, b].some((k) => ['marginLeft', 'marginRight', 'marginTop', 'marginBottom']
          .some((m) => parseFloat(k.cs[m]) < 0));
        const area = intersection(a.rect, b.rect);
        report('overlap', negative ? 'warn' : 'error', b.el,
          `Collides with its sibling ${describe(a.el)}${negative ? ' (a negative margin: deliberate?)' : ''}.`,
          { with: describe(a.el), overlapPx: area ? plain(area) : null });
      }
    }

    // Interactive targets: occlusion and size.
    const coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    const targets = [];
    for (const el of (opts.root || document.body).querySelectorAll(INTERACTIVE)) {
      const n = info.get(el);
      if (!n || el.disabled || el.getAttribute('aria-hidden') === 'true') continue;
      if (n.rect.width <= 1 || n.rect.height <= 1) continue;
      targets.push(n);
    }
    for (const n of targets) {
      const vis = intersection(n.rect, viewport);
      if (!vis) continue;
      const x = (vis.left + vis.right) / 2;
      const y = (vis.top + vis.bottom) / 2;
      const hit = deepElementFromPoint(x, y);
      const labels = n.el.labels ? Array.from(n.el.labels) : [];
      const ok = hit && (composedContains(n.el, hit) || labels.some((l) => composedContains(l, hit)));
      if (!ok) {
        report('occluded-target', 'error', n.el,
          `A tap at its center lands on ${hit ? describe(hit) : 'nothing'}: the control cannot be hit there.`,
          { point: { x: round(x), y: round(y) }, hit: hit ? describe(hit) : null });
      }
    }
    const sized = targets.filter((n) => !inlineInText(n.el, n.cs));
    const failing = new Set(targetSpacingFailures(sized.map((n) => n.rect), opts.minTarget));
    sized.forEach((n, i) => {
      if (failing.has(i)) {
        report('target-size', 'error', n.el,
          `${round(n.rect.width)}x${round(n.rect.height)}px target with neighbors closer than the ${opts.minTarget}px spacing circle (WCAG 2.2 SC 2.5.8).`,
          { width: round(n.rect.width), height: round(n.rect.height) });
      } else if (coarse && (n.rect.width < opts.minTargetCoarse - EPS || n.rect.height < opts.minTargetCoarse - EPS)) {
        report('target-size', 'info', n.el,
          `${round(n.rect.width)}x${round(n.rect.height)}px on a coarse pointer: below ${opts.minTargetCoarse}px (SC 2.5.5, AAA).`,
          { width: round(n.rect.width), height: round(n.rect.height) });
      }
    });

    // Scrolling: nested traps, touch-action, fixed panels that cannot scroll.
    const docScrollsY = de.scrollHeight > vh + 1 && !clips(viewportOverflowY);
    const scrollers = nodes.filter((n) => scrolls(n.cs.overflowY) && n.el.scrollHeight > n.el.clientHeight + 1);
    for (const n of scrollers) {
      // By size, not by the current scroll position: below the fold it still fills the screen
      // the moment the user reaches it.
      const coverW = Math.min(n.rect.width, vw) / vw;
      const coverH = Math.min(n.rect.height, vh) / vh;
      if (coverW < opts.trapCoverage || coverH < opts.trapCoverage) continue;
      let outer = docScrollsY ? 'document' : null;
      for (let p = n.el.parentElement; p && !outer; p = p.parentElement) {
        const pi = info.get(p);
        if (pi && scrolls(pi.cs.overflowY) && p.scrollHeight > p.clientHeight + 1) outer = describe(p);
      }
      if (!outer) continue;
      const contained = n.cs.overscrollBehaviorY === 'contain' || n.cs.overscrollBehaviorY === 'none';
      report('scroll-trap', contained ? 'error' : 'warn', n.el,
        contained ? `Covers ${Math.round(coverH * 100)}% of the viewport, scrolls, and blocks chaining (overscroll-behavior: ${n.cs.overscrollBehaviorY}): a touch user cannot reach the scrolling ${outer} around it.`
          : `Covers ${Math.round(coverH * 100)}% of the viewport inside the scrolling ${outer}: on touch the outer scroll is reachable only by chaining past this one's end.`,
        { coverage: round(coverH, 2), outer });
    }
    const blocked = [];
    for (const n of nodes) {
      if (n.cs.touchAction !== 'none' || blocked.some((b) => b.contains(n.el))) continue;
      const vis = intersection(n.rect, viewport);
      if (!vis) continue;
      const share = ((vis.right - vis.left) * (vis.bottom - vis.top)) / (vw * vh);
      if (share >= 0.5 && !/^(canvas|video|iframe)$/i.test(n.el.tagName)) {
        blocked.push(n.el);
        report('touch-action-block', 'warn', n.el,
          `touch-action: none over ${Math.round(share * 100)}% of the viewport: a finger cannot scroll the page there.`,
          { viewportShare: round(share, 2) });
      }
    }
    for (const n of nodes) {
      if (n.cs.position !== 'fixed') continue;
      const tooTall = n.rect.bottom > vh + 1 || n.rect.top < -1;
      const canScroll = scrolls(n.cs.overflowY) && n.el.scrollHeight > n.el.clientHeight + 1;
      if (tooTall && !canScroll && n.rect.height > vh * 0.5) {
        report('unreachable-fixed', 'error', n.el,
          `A fixed box ${round(n.rect.height)}px tall in a ${vh}px viewport, without its own scroll: its end cannot be reached (landscape phones, open keyboards).`,
          { height: round(n.rect.height), viewportHeight: vh });
      }
    }

    // ios-input-zoom.
    for (const el of (opts.root || document.body).querySelectorAll('input, select, textarea')) {
      const n = info.get(el);
      if (!n) continue;
      const type = (el.getAttribute('type') || 'text').toLowerCase();
      if (/^(checkbox|radio|range|color|file|button|submit|reset|image|hidden)$/.test(type)) continue;
      const size = parseFloat(n.cs.fontSize);
      if (size < 16) {
        report('ios-input-zoom', 'warn', el,
          `font-size ${size}px: iOS Safari zooms the whole page when this field takes focus (anything under 16px).`,
          { fontSizePx: size });
      }
    }

    // Animations running now, and transitions waiting to animate layout.
    if (support.getAnimations) {
      for (const a of collectAnimations()) {
        if (a.worst === 'compositor') continue;
        const severity = a.worst === 'layout' ? 'error' : a.worst === 'paint' ? 'warn' : 'info';
        report('non-composited-animation', severity, a.targetEl,
          `${a.kind} "${a.name}" on ${a.target} animates ${Object.keys(a.properties).filter((p) => a.properties[p] !== 'compositor').join(', ')}: ${a.worst === 'engine-dependent' ? 'composited only by some engines' : `main-thread ${a.worst} on every frame`}.`,
          { target: a.target, properties: a.properties });
      }
    }
    for (const n of nodes) {
      const durations = n.cs.transitionDuration.split(',').map(parseFloat);
      if (!durations.some((d) => d > 0)) continue;
      const props = n.cs.transitionProperty.split(',').map((p) => p.trim());
      const bad = props.filter((p, i) => (durations[i % durations.length] > 0) && classifyProperty(p) === 'layout');
      if (bad.length) {
        report('latent-transition', 'warn', n.el,
          `transition-property ${bad.join(', ')}: the next state change animates layout on the main thread (\`all\` included).`,
          { properties: bad });
      }
    }

    // layer-memory: promoted layers estimated from will-change and 3D transforms (a lower bound;
    // the CDP LayerTree recipe gives the real figure on Chromium).
    let layerBytes = 0;
    let promoted = 0;
    const capW = vw * 3;
    const capH = vh * 3;
    for (const n of nodes) {
      const wc = n.cs.willChange;
      const threeD = /matrix3d|translateZ|translate3d/.test(n.cs.transform);
      if ((wc && wc !== 'auto') || threeD) {
        promoted++;
        layerBytes += Math.min(n.rect.width, capW) * Math.min(n.rect.height, capH) * dpr * dpr * 4;
      }
    }
    const layerMB = layerBytes / (1024 * 1024);
    if (layerMB > opts.layerBudgetMB) {
      report('layer-memory', 'warn', null,
        `${promoted} promoted layers need about ${round(layerMB, 1)} MB of GPU memory at DPR ${dpr}, over the ${opts.layerBudgetMB} MB budget: low-end GPUs checkerboard or evict.`,
        { promoted, estimatedMB: round(layerMB, 1), dpr });
    }

    // blocking-scroll-listener: non-passive touch and wheel listeners that can hold the compositor.
    if (support.listenerTracking) {
      for (const l of listeners) {
        const target = supportsWeakRef ? l.ref.deref() : l.ref;
        if (!target) continue;
        const isRoot = target === window || target === document || target === de || target === document.body;
        const passive = l.explicit !== null ? l.explicit : isRoot; // browsers default root listeners to passive
        if (passive) continue;
        if (target.nodeType === 1 && !target.isConnected) continue;
        const el = target.nodeType === 1 ? target : null;
        report('blocking-scroll-listener', isRoot || (el && info.has(el) && intersection(info.get(el).rect, viewport)) ? 'warn' : 'info', el,
          `A non-passive ${l.type} listener on ${describe(target)}: every scroll gesture over it waits for the main thread.`,
          { type: l.type, target: describe(target), explicitPassiveFalse: l.explicit === false });
      }
    }

    const bySeverity = { error: 0, warn: 0, info: 0 };
    for (const f of findings) bySeverity[f.severity]++;
    return {
      probe: VERSION,
      viewport: { width: vw, height: vh, dpr },
      elements: nodes.length,
      truncated,
      support: Object.assign({}, support),
      summary: { bySeverity, byRule: counts, allowed: allowedCount },
      findings,
    };
  };

  // ---------------------------------------------------------------------------------------------
  // Geometry snapshot for scripts/layout_diff.py
  // ---------------------------------------------------------------------------------------------

  const SNAPSHOT = '[data-testid], [id], h1, h2, h3, h4, h5, h6, header, nav, main, aside, footer, '
    + 'section, article, form, ul, ol, table, button, a[href], input, select, textarea, img, video, '
    + 'picture, svg, [role]';

  function nameOf(el) {
    const n = el.getAttribute('aria-label') || el.getAttribute('alt') || el.getAttribute('placeholder')
      || el.getAttribute('name') || (el.textContent || '');
    return n.replace(/\s+/g, ' ').trim().slice(0, 40);
  }

  /** Boxes of the elements that matter (landmarks, headings, controls, media, anything with a
   * test id or a role), keyed by a path that survives class-name churn. Rects are page
   * coordinates rounded to 1/64 px. Options: `selector`, `root`. */
  api.snapshot = function snapshot(options) {
    const opts = Object.assign({ selector: SNAPSHOT, root: document.body }, options || {});
    const keys = new Map();
    const used = new Map();
    const nodes = [];
    const q = (v) => Math.round(v * 64) / 64;
    for (const el of opts.root.querySelectorAll(opts.selector)) {
      const cs = getComputedStyle(el);
      if (!rendered(el, cs)) continue;
      let parent = el.parentElement;
      while (parent && !keys.has(parent)) parent = parent.parentElement;
      const parentKey = parent ? keys.get(parent) : null;
      const tag = el.tagName.toLowerCase();
      const testid = el.getAttribute('data-testid');
      let local;
      if (testid) local = `${tag}[testid=${testid}]`;
      else if (el.id && !generatedId(el.id)) local = `${tag}#${el.id}`;
      else {
        const role = el.getAttribute('role');
        const name = /^(h[1-6]|button|a|label|legend|summary|th|img|input|select|textarea)$/.test(tag) || role
          ? nameOf(el) : '';
        local = `${tag}${role ? `[${role}]` : ''}${name ? `"${name}"` : ''}`;
      }
      let key = parentKey ? `${parentKey} > ${local}` : local;
      const n = (used.get(key) || 0) + 1;
      used.set(key, n);
      if (n > 1) key += `~${n}`;
      keys.set(el, key);
      const r = el.getBoundingClientRect();
      nodes.push({ key, parent: parentKey, rect: [q(r.left + window.scrollX), q(r.top + window.scrollY), q(r.width), q(r.height)] });
    }
    return {
      probe: VERSION,
      url: location.href,
      viewport: { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight,
        dpr: window.devicePixelRatio || 1 },
      nodes,
    };
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
