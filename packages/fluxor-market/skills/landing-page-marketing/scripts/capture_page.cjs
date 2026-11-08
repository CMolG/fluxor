#!/usr/bin/env node
/*
 * Render a landing page in headless Chromium and record what a visitor actually sees.
 *
 * Output (in --out):
 *   desktop-fold.png     first screen at 1440x900
 *   mobile-fold.png      first screen at 390x844 (a phone)
 *   desktop-full.png     the whole page
 *   fold.json            for each viewport: the headings, paragraphs, buttons/CTAs, images and prices
 *                        visible in the first screen (the "5-second test" evidence), plus
 *                        load timings, console errors and horizontal overflow on mobile
 *   rendered.html        (with --dump-html) the DOM after JavaScript, for extract_page.py / copy_lint.py
 *
 * Usage:
 *   node capture_page.cjs --url https://example.com --out evidence [--dump-html] [--wait 1500]
 *   node capture_page.cjs --url file:///abs/path/index.html --out evidence
 *
 * Needs Playwright with Chromium (`npm i -D playwright && npx playwright install chromium`, or a global install).
 */
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const USAGE = `usage: node capture_page.cjs --url <url> --out <dir> [--dump-html] [--wait 1500]

Renders a landing page in headless Chromium (Playwright) and records what a visitor sees first.

options:
  --url <url>      page to render (https://... or file:///abs/path/index.html)
  --out <dir>      output folder (default: evidence)
  --dump-html      also save rendered.html, the DOM after JavaScript
  --wait <ms>      extra wait after load before capturing (default: 1500)
  -h, --help       show this help and exit

Writes desktop-fold.png, mobile-fold.png, desktop-full.png and fold.json in --out.
Needs Playwright with Chromium (npm i -D playwright && npx playwright install chromium).`;

if (process.argv.includes("--help") || process.argv.includes("-h")) {
  console.log(USAGE);
  process.exit(0);
}

function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return def;
  const v = process.argv[i + 1];
  return v === undefined || v.startsWith("--") ? true : v;
}

function loadPlaywright() {
  const tries = ["playwright", "playwright-core", "@playwright/test"];
  for (const t of tries) {
    try { return require(t); } catch (_) { /* keep looking */ }
  }
  try {
    const root = execSync("npm root -g", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
    for (const t of tries) {
      try { return require(path.join(root, t)); } catch (_) { /* keep looking */ }
    }
  } catch (_) { /* npm not available */ }
  return null;
}

// Runs in the page: inventory of meaningful elements inside the first viewport.
function foldInventory(configured) {
  // On phones an overflowing layout makes innerWidth grow beyond the device width; measure against the device.
  const vw = configured.width, vh = configured.height;
  const scale = window.innerWidth > vw ? vw / window.innerWidth : 1;
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0) return false;
    return r.top * scale < vh && r.bottom > 0 && r.left * scale < vw && r.right > 0;
  };
  const txt = (el) => (el.innerText || el.value || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim();
  const pick = (sel, max = 30) => Array.from(document.querySelectorAll(sel)).filter(visible).slice(0, max);
  const btnSel = "button, a[role=button], input[type=submit], input[type=button], a[class*=btn], a[class*=button], a[class*=cta]";
  const box = (el) => { const r = el.getBoundingClientRect(); return { top: Math.round(r.top), height: Math.round(r.height) }; };
  const headings = pick("h1, h2, h3").map((el) => ({ tag: el.tagName.toLowerCase(), text: txt(el).slice(0, 200), ...box(el),
    fontSize: getComputedStyle(el).fontSize }));
  const ctas = pick(btnSel).map((el) => ({ text: txt(el).slice(0, 80), href: el.getAttribute("href") || "", ...box(el),
    inNav: !!el.closest("nav, [role=navigation]") }));
  const paragraphs = pick("p, li, blockquote, figcaption", 40).map((el) => txt(el)).filter((t) => t.length > 2).map((t) => t.slice(0, 240));
  const images = pick("img, video, picture, [role=img]", 15).map((el) => ({ tag: el.tagName.toLowerCase(), alt: el.getAttribute("alt"),
    ...box(el), width: Math.round(el.getBoundingClientRect().width) }));
  const allText = Array.from(document.querySelectorAll("body *")).filter((el) => el.children.length === 0 && visible(el))
    .map(txt).join(" ");
  const prices = (allText.match(/[$€£]\s?\d[\d.,]*|\d[\d.,]*\s?(€|EUR|USD)/g) || []).slice(0, 10);
  const words = allText.split(/\s+/).filter(Boolean).length;
  return { viewport: { width: vw, height: vh }, headings, ctas, primaryCtaVisible: ctas.some((c) => !c.inNav),
    paragraphs, images, prices, wordsVisible: words,
    pageHeight: document.documentElement.scrollHeight,
    screens: Math.round((document.documentElement.scrollHeight * scale / vh) * 10) / 10,
    layoutWidth: window.innerWidth,
    horizontalOverflow: document.documentElement.scrollWidth > vw + 1 };
}

(async () => {
  const url = arg("url");
  const out = arg("out", "evidence");
  const waitMs = Number(arg("wait", 1500)) || 0;
  const dumpHtml = arg("dump-html", false);
  if (!url) {
    console.error(USAGE);
    process.exit(2);
  }
  const pw = loadPlaywright();
  if (!pw) {
    console.error("Playwright is not installed. Install it (`npm i -D playwright && npx playwright install chromium`) " +
      "or continue without screenshots using extract_page.py.");
    process.exit(2);
  }
  fs.mkdirSync(out, { recursive: true });
  const browser = await pw.chromium.launch();
  const result = { url, capturedAt: new Date().toISOString(), viewports: {}, consoleErrors: [], failedRequests: [] };
  try {
    const shots = [
      { name: "desktop", viewport: { width: 1440, height: 900 }, mobile: false },
      { name: "mobile", viewport: { width: 390, height: 844 }, mobile: true },
    ];
    for (const s of shots) {
      const ctx = await browser.newContext({ viewport: s.viewport, isMobile: s.mobile, hasTouch: s.mobile,
        deviceScaleFactor: s.mobile ? 2 : 1,
        userAgent: s.mobile ? "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" : undefined });
      const page = await ctx.newPage();
      if (s.name === "desktop") {
        page.on("console", (m) => { if (m.type() === "error") result.consoleErrors.push(m.text().slice(0, 300)); });
        page.on("requestfailed", (r) => result.failedRequests.push(`${r.url().slice(0, 200)} ${r.failure() ? r.failure().errorText : ""}`));
      }
      const t0 = Date.now();
      let status = null;
      try {
        const resp = await page.goto(url, { waitUntil: "load", timeout: 45000 });
        status = resp ? resp.status() : null;
      } catch (e) {
        result.viewports[s.name] = { error: String(e).slice(0, 300) };
        await ctx.close();
        continue;
      }
      const loadMs = Date.now() - t0;
      if (waitMs) await page.waitForTimeout(waitMs);
      const timing = await page.evaluate(() => {
        const nav = performance.getEntriesByType("navigation")[0];
        const lcp = performance.getEntriesByType("largest-contentful-paint");
        return { domContentLoadedMs: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
          lcpMs: lcp.length ? Math.round(lcp[lcp.length - 1].startTime) : null };
      }).catch(() => ({}));
      const inv = await page.evaluate(foldInventory, s.viewport);
      await page.screenshot({ path: path.join(out, `${s.name}-fold.png`) });
      if (s.name === "desktop") {
        await page.screenshot({ path: path.join(out, "desktop-full.png"), fullPage: true });
        if (dumpHtml) fs.writeFileSync(path.join(out, "rendered.html"), await page.content());
      }
      result.viewports[s.name] = { status, loadMs, ...timing, ...inv };
      await ctx.close();
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(out, "fold.json"), JSON.stringify(result, null, 2));
  for (const [name, v] of Object.entries(result.viewports)) {
    if (v.error) { console.log(`${name}: ERROR ${v.error}`); continue; }
    console.log(`${name} ${v.viewport.width}x${v.viewport.height}: status ${v.status}, load ${v.loadMs} ms, ` +
      `page = ${v.screens} screens` +
      (v.horizontalOverflow ? `, HORIZONTAL OVERFLOW (layout is ${v.layoutWidth}px wide)` : ""));
    console.log(`  headings in first screen: ${JSON.stringify(v.headings.map((h) => h.text))}`);
    console.log(`  CTAs in first screen: ${JSON.stringify(v.ctas.map((c) => c.text + (c.inNav ? " (nav)" : "")))}` +
      (v.primaryCtaVisible ? "" : "  <- no primary CTA outside the nav"));
    console.log(`  words visible: ${v.wordsVisible}; images: ${v.images.length}; prices: ${JSON.stringify(v.prices)}`);
  }
  if (result.consoleErrors.length) console.log(`console errors: ${result.consoleErrors.length}`);
  console.log(`saved to ${out}/`);
})().catch((e) => {
  console.error(`capture_page failed: ${e && e.stack ? e.stack : e}`);
  process.exit(1);
});
