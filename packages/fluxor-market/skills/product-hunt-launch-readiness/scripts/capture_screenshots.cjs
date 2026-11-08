#!/usr/bin/env node
/*
 * Render a product page in headless Chromium (Playwright) and capture launch evidence:
 *   - gallery-1270x760.png     above-the-fold desktop shot at Product Hunt's recommended gallery size
 *   - fullpage-desktop.png     the whole landing page, for reviewing copy and craft
 *   - mobile-390x844.png       above-the-fold on a phone (a lot of Product Hunt traffic is mobile)
 *   - thumbnail-240x240.png    optional: a logo fitted into Product Hunt's 240x240 thumbnail
 *   - rendered.html            optional: DOM after JavaScript, for client-rendered apps (feed it to audit_url.py --html-file)
 *   - capture.json             console errors, failed requests, load timings, mobile horizontal overflow
 *
 * Usage:
 *   node capture_screenshots.cjs --url https://example.com --out evidence/screens [--dump-html] [--thumbnail logo.png] [--scale 2]
 *
 * Needs Playwright with Chromium (`npm i -D playwright && npx playwright install chromium`, or a global install).
 */
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const USAGE = `usage: node capture_screenshots.cjs --url <url> --out <dir> [--dump-html] [--thumbnail <logo>] [--scale 2]

Renders a product page in headless Chromium (Playwright) and captures launch evidence.

options:
  --url <url>          page to capture (gallery, full-page and mobile shots)
  --out <dir>          output folder (default: screens)
  --dump-html          also save rendered.html, the DOM after JavaScript (for audit_url.py --html-file)
  --thumbnail <logo>   fit a logo (local file or URL) into a 240x240 thumbnail; works without --url
  --scale <n>          device scale factor for the desktop shots (default: 1)
  --wait <ms>          extra wait after load before capturing (default: 1500)
  -h, --help           show this help and exit

Writes gallery-1270x760.png, fullpage-desktop.png, mobile-390x844.png, thumbnail-240x240.png and
capture.json in --out. Needs Playwright with Chromium (npm i -D playwright && npx playwright install chromium).`;

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

(async () => {
  const url = arg("url");
  const out = arg("out", "screens");
  const scale = Number(arg("scale", 1)) || 1;
  const thumb = arg("thumbnail");
  const dumpHtml = arg("dump-html", false);
  const waitMs = Number(arg("wait", 1500)) || 0;
  if (!url && !thumb) {
    console.error(USAGE);
    process.exit(2);
  }
  const pw = loadPlaywright();
  if (!pw) {
    console.error("Playwright is not installed. Install it with `npm i -D playwright && npx playwright install chromium`, " +
      "or skip screenshots and rely on audit_url.py.");
    process.exit(2);
  }
  fs.mkdirSync(out, { recursive: true });
  let browser;
  try {
    browser = await pw.chromium.launch({ headless: true });
  } catch (e) {
    console.error(`Could not launch Chromium: ${e.message}\nTry \`npx playwright install chromium\`.`);
    process.exit(2);
  }
  const result = { url, out, files: [], console_errors: [], page_errors: [], failed_requests: [], timings: {}, mobile: {} };

  if (url) {
    const ctx = await browser.newContext({ viewport: { width: 1270, height: 760 }, deviceScaleFactor: scale });
    const page = await ctx.newPage();
    page.on("console", (m) => { if (m.type() === "error") result.console_errors.push(m.text().slice(0, 300)); });
    page.on("pageerror", (e) => result.page_errors.push(String(e).slice(0, 300)));
    page.on("requestfailed", (r) => result.failed_requests.push({ url: r.url().slice(0, 200), error: (r.failure() || {}).errorText }));
    page.on("response", (r) => { if (r.status() >= 400) result.failed_requests.push({ url: r.url().slice(0, 200), status: r.status() }); });
    const t0 = Date.now();
    let resp;
    try {
      resp = await page.goto(url, { waitUntil: "load", timeout: 45000 });
    } catch (e) {
      result.navigation_error = e.message.split("\n")[0];
    }
    result.status = resp ? resp.status() : null;
    result.final_url = page.url();
    try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch (_) { /* long-polling pages never go idle */ }
    if (waitMs) await page.waitForTimeout(waitMs);
    result.timings.wall_ms_to_load = Date.now() - t0;
    try {
      result.timings.navigation = await page.evaluate(() => {
        const n = performance.getEntriesByType("navigation")[0];
        const lcp = performance.getEntriesByType("largest-contentful-paint").pop();
        return n ? { ttfb_ms: Math.round(n.responseStart), dom_content_loaded_ms: Math.round(n.domContentLoadedEventEnd),
          load_ms: Math.round(n.loadEventEnd), transfer_kb: Math.round((n.transferSize || 0) / 1024),
          lcp_ms: lcp ? Math.round(lcp.startTime) : null } : null;
      });
      result.title = await page.title();
      // Is each element's first-choice font actually rendering? document.fonts.check() says yes even for
      // fonts that never loaded, so compare canvas text widths against generic fallbacks instead.
      result.fonts = await page.evaluate(() => {
        const ctx = document.createElement("canvas").getContext("2d");
        const probe = "mmmmmmmmmmlliiWWWWwwww 0123456789";
        const width = (f) => { ctx.font = `72px ${f}`; return ctx.measureText(probe).width; };
        const generic = /^(serif|sans-serif|monospace|system-ui|cursive|fantasy|ui-[\w-]+|-apple-system|BlinkMacSystemFont|inherit|initial)$/i;
        const out = {};
        for (const sel of ["h1", "h2", "p", "a", "button", "body"]) {
          const el = document.querySelector(sel);
          if (!el) continue;
          const family = getComputedStyle(el).fontFamily;
          const first = family.split(",")[0].trim().replace(/^['"]|['"]$/g, "");
          const ok = generic.test(first) ||
            !(width(`"${first}", monospace`) === width("monospace") && width(`"${first}", serif`) === width("serif"));
          out[sel] = { family, first_choice: first, renders: ok };
        }
        return out;
      });
      result.missing_fonts = [...new Set(Object.values(result.fonts || {}).filter((f) => !f.renders).map((f) => f.first_choice))];
      if (result.missing_fonts.length) {
        result.fonts_note = `Rendered with fallback fonts because ${result.missing_fonts.join(", ")} did not load here; ` +
          "text widths (and therefore wrapping or overflow) may differ on real devices. Caveat layout findings accordingly.";
      }
    } catch (_) { /* page crashed */ }
    const shot = async (p, opts) => {
      const f = path.join(out, p);
      try { await page.screenshot({ path: f, ...opts }); result.files.push(f); } catch (e) { result[`error_${p}`] = e.message; }
    };
    await shot(`gallery-1270x760${scale > 1 ? `@${scale}x` : ""}.png`, { fullPage: false });
    await shot("fullpage-desktop.png", { fullPage: true });
    if (dumpHtml) {
      const f = path.join(out, "rendered.html");
      fs.writeFileSync(f, await page.content());
      result.files.push(f);
    }
    await ctx.close();

    const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true,
      hasTouch: true, userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" });
    const mpage = await mctx.newPage();
    try {
      await mpage.goto(url, { waitUntil: "load", timeout: 45000 });
      try { await mpage.waitForLoadState("networkidle", { timeout: 8000 }); } catch (_) { /* ignore */ }
      if (waitMs) await mpage.waitForTimeout(waitMs);
      // Mobile Chromium zooms out to fit over-wide content, which silently grows window.innerWidth,
      // so compare against the device width we asked for, not against the page itself.
      result.mobile = await mpage.evaluate((deviceWidth) => {
        const doc = document.documentElement;
        const widest = [...document.querySelectorAll("body *")]
          .map((el) => ({ el, right: el.getBoundingClientRect().right }))
          .filter((x) => x.right > deviceWidth + 1)
          .sort((a, b) => b.right - a.right)
          .slice(0, 5)
          .map(({ el, right }) => `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}${el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : ""} (right edge ${Math.round(right)}px)`);
        return {
          device_width: deviceWidth,
          layout_viewport_width: window.innerWidth,
          scroll_width: doc.scrollWidth,
          horizontal_overflow: doc.scrollWidth > deviceWidth + 1 || window.innerWidth > deviceWidth + 1,
          overflowing_elements: widest,
          tiny_text_elements: [...document.querySelectorAll("p, li, a, span, button")]
            .filter((el) => el.offsetParent && parseFloat(getComputedStyle(el).fontSize) < 12 && el.textContent.trim().length > 20).length,
        };
      }, 390);
      const f = path.join(out, "mobile-390x844.png");
      await mpage.screenshot({ path: f, fullPage: false });
      result.files.push(f);
    } catch (e) {
      result.mobile.error = e.message.split("\n")[0];
    }
    await mctx.close();
  }

  if (thumb && thumb !== true) {
    // Pages created with setContent() can't load file:// URLs, so inline local files as data URIs.
    const mime = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
      ".webp": "image/webp", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".avif": "image/avif" };
    const src = /^https?:\/\//.test(thumb) ? thumb
      : `data:${mime[path.extname(thumb).toLowerCase()] || "application/octet-stream"};base64,` +
        fs.readFileSync(path.resolve(thumb)).toString("base64");
    const tctx = await browser.newContext({ viewport: { width: 240, height: 240 }, deviceScaleFactor: 1 });
    const tpage = await tctx.newPage();
    await tpage.setContent(`<html><body style="margin:0;background:transparent">
      <img src="${src}" style="width:240px;height:240px;object-fit:contain;display:block"></body></html>`);
    try { await tpage.waitForLoadState("networkidle", { timeout: 8000 }); } catch (_) { /* ignore */ }
    const f = path.join(out, "thumbnail-240x240.png");
    await tpage.screenshot({ path: f, omitBackground: true });
    result.files.push(f);
    await tctx.close();
  }

  await browser.close();
  result.console_errors = [...new Set(result.console_errors)].slice(0, 20);
  result.failed_requests = result.failed_requests.slice(0, 30);
  fs.writeFileSync(path.join(out, "capture.json"), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
})().catch((e) => {
  console.error(`capture_screenshots failed: ${e && e.stack ? e.stack : e}`);
  process.exit(1);
});
