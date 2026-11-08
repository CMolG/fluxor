// probe.js: the pure geometry the audit and the windows rest on, exercised without a DOM.
// The DOM half is verified in real engines (references/driver-recipes.md, "Prove the probe").
// Run from packages/fluxor-market: node --test skills/ui-fluidity-verification/tests/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../assets/probe.js', import.meta.url), 'utf8');
const context = {};
runInNewContext(source, context);
const g = context.__fluidity.geometry;
const box = (left, top, right, bottom) => ({ left, top, right, bottom });
// Arrays built inside the vm context have that realm's prototypes, which deepStrictEqual rejects.
const pairs = (list) => Array.from(list, (p) => [p[0], p[1]]);

test('loads without a DOM and installs nothing but the pure helpers', () => {
  assert.equal(typeof context.__fluidity.audit, 'undefined');
  assert.equal(typeof g.overlaps, 'function');
});

test('excess ignores sub-LayoutUnit differences and reports each side', () => {
  assert.deepEqual({ ...g.excess(box(0, 0, 100.01, 50), box(0, 0, 100, 50)) }, { left: 0, top: 0, right: 0, bottom: 0 });
  assert.deepEqual({ ...g.excess(box(-4, 0, 112, 50), box(0, 0, 100, 50)) }, { left: 4, top: 0, right: 12, bottom: 0 });
});

test('overlaps finds colliding pairs and not touching ones', () => {
  const rects = [box(0, 0, 100, 40), box(100, 0, 200, 40), box(150, 20, 260, 60), box(300, 0, 320, 20)];
  assert.deepEqual(pairs(g.overlaps(rects)), [[1, 2]]);
});

test('overlaps agrees with the all-pairs answer on random rects', () => {
  let seed = 7;
  const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
  const rects = Array.from({ length: 120 }, () => {
    const x = rand() * 1000; const y = rand() * 1000;
    return box(x, y, x + rand() * 80, y + rand() * 80);
  });
  const brute = [];
  for (let i = 0; i < rects.length; i++) {
    for (let j = i + 1; j < rects.length; j++) {
      const w = Math.min(rects[i].right, rects[j].right) - Math.max(rects[i].left, rects[j].left);
      const h = Math.min(rects[i].bottom, rects[j].bottom) - Math.max(rects[i].top, rects[j].top);
      if (w > g.EPS && h > g.EPS) brute.push([i, j]);
    }
  }
  assert.deepEqual(pairs(g.overlaps(rects)), brute);
});

test('seam: edges that touch in layout but snap to different device pixels', () => {
  assert.equal(g.seam(100.5, 100.5, 2), 0);                  // the same edge
  assert.equal(g.seam(100.2, 100.3, 2), 0.5);                 // snaps to 100 and 100.5: a gap
  assert.equal(g.seam(100.3, 100.2, 2), -0.5);                // an overlap
  assert.equal(g.seam(100, 104, 2), 0);                       // apart on purpose: not a seam
});

test('frameStats counts dropped frames and the worst streak against the calibrated interval', () => {
  const v = 1000 / 60;
  const times = [0];
  const deltas = [v, v, v, 3 * v, v, v, 5 * v, v];
  for (const d of deltas) times.push(times[times.length - 1] + d);
  const s = g.frameStats(times, v);
  assert.equal(s.frames, 8);
  assert.equal(s.droppedFrames, 6);                           // 2 + 4
  assert.equal(s.worstDropStreak, 4);
  assert.equal(s.vsyncSource, 'calibrated');
});

test('frameStats without calibration is blind to a uniformly halved rate', () => {
  const times = Array.from({ length: 20 }, (_, i) => i * (2000 / 60));
  assert.equal(g.frameStats(times).droppedFrames, 0);
  assert.equal(g.frameStats(times, 1000 / 60).droppedFrames, 19);
});

test('classifyProperty separates compositor, paint and layout work', () => {
  assert.equal(g.classifyProperty('transform'), 'compositor');
  assert.equal(g.classifyProperty('opacity'), 'compositor');
  assert.equal(g.classifyProperty('webkitTransform'), 'compositor');
  assert.equal(g.classifyProperty('filter'), 'engine-dependent');
  assert.equal(g.classifyProperty('backgroundColor'), 'engine-dependent');
  assert.equal(g.classifyProperty('boxShadow'), 'paint');
  assert.equal(g.classifyProperty('--progress'), 'paint');
  for (const p of ['width', 'height', 'top', 'marginLeft', 'padding', 'gridTemplateColumns', 'fontSize', 'all']) {
    assert.equal(g.classifyProperty(p), 'layout', p);
  }
});

test('targetSpacingFailures applies the 24px circle exception of SC 2.5.8', () => {
  const crowded = [box(0, 0, 16, 16), box(16, 0, 32, 16)];
  assert.deepEqual([...g.targetSpacingFailures(crowded, 24)], [0, 1]);
  const spaced = [box(0, 0, 16, 16), box(40, 0, 56, 16)];
  assert.deepEqual([...g.targetSpacingFailures(spaced, 24)], []);
  const bigNeighbor = [box(0, 0, 16, 16), box(18, 0, 60, 44)];
  assert.deepEqual([...g.targetSpacingFailures(bigNeighbor, 24)], [0]);
});
