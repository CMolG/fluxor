---
name: product-hunt-launch-readiness
description: Audit a product (a code repository, a live URL, or both) against Product Hunt's official launch guide and featuring guidelines and get it launch-ready. It finds everything that would get the launch penalised, left un-featured or waste launch-day traffic, fixes what it can, and produces an evidence-backed report, a validated ready-to-paste launch kit (name ≤40, tagline ≤60, description, tags, 240x240 thumbnail, 1270x760 gallery plan, maker comment, pricing, promo, compliant sharing messages) and a 12:01 AM PT timeline in the maker's timezone. Use it whenever someone is preparing, reviewing, scheduling or relaunching a Product Hunt (PH) launch, even without the word 'audit', e.g. checking a landing page or repo before going live on PH, writing or fixing a PH tagline, description, maker comment or gallery, picking a launch day, asking if an app, site, extension, CLI or side project is ready for Product Hunt, or aiming for Product of the Day. Not for general Product Hunt research, scraping or competitor lists.
---

# Product Hunt Launch Readiness

Your job is to take a product to the point where it's ready to launch on
Product Hunt, and to prove it with evidence. "Ready" means:

1. **Nothing breaks a Product Hunt rule.** Asking for upvotes, vote rings or
   paid votes can get a launch penalised or removed.
2. **Nothing rules out being featured.** Featuring is editorial, and it is
   where the traffic is: non-featured launches sit behind the "All" tab. A
   waitlist-only product, a missing maker comment, a broken link, an unclear
   tagline or a launch that wasn't scheduled ahead all make it very unlikely.
3. **Every visitor can understand and try the product in seconds**, on
   mobile too, and the product survives a traffic spike.
4. **Every listing asset exists and fits Product Hunt's limits.**
5. **The launch-day and follow-up plan is in place.**

The top bar, 🏆 **launch-perfect**, means zero open items and every
unverifiable item confirmed by the maker. Report honestly how far the product
is from that bar and close as much of the gap as you can.

Script paths below are relative to this skill's directory. The scripts only
need Python 3 (standard library); screenshots additionally need Node and
Playwright.

## 1. Scope the job

Work out from the request, without interrupting the user:

- **Target.** A local repo (the cwd if it's a project), a git URL (shallow
  clone it), a live URL, or both. If a repo reveals its production URL
  (`homepage_candidates` from the repo audit: `metadataBase`, `SITE_URL`,
  `CNAME`, `package.json` homepage, README), audit that URL too. Code shows
  what should happen; the live site shows what actually happens.
- **Product type.** Web app, mobile app, browser or IDE extension, desktop
  app, dev tool/library/CLI, API, open source, AI product. Each type adds
  checks (checklist §J).
- **Launch facts given.** Date, timezone, whether it's a relaunch, draft
  listing fields, team size.
- **Depth.** For a readiness question, run the full audit. For a narrow
  request ("fix my tagline", "review my first comment", "what size are
  gallery images?"), do just that part with the relevant reference and
  `check_launch_kit.py`, then offer the full audit.
- **A producthunt.com URL** (an existing or scheduled listing): audit the
  listing fields. If the page can't be fetched, ask the user to paste them.
  Don't reach it through caches, mirrors or proxy services.

Collect anything you can't determine as ⚪ items to ask about at the end.

## 2. Gather evidence

Create the output folder first: `product-hunt-launch/` at the repo root (repo
mode) or in the current directory (URL mode), unless the user named one.
Save everything under it.

```bash
python3 scripts/audit_repo.py <repo> --json <out>/evidence/repo.json
python3 scripts/audit_url.py <url> --json <out>/evidence/url.json
node scripts/capture_screenshots.cjs --url <url> --out <out>/evidence/screens --dump-html
```

- `audit_repo.py` covers stack and product type, README/LICENSE/CHANGELOG,
  logo and screenshot assets with real pixel sizes, metadata (Open Graph,
  Twitter, `metadataBase`, missing referenced assets, localhost URLs), and
  copy signals with `file:line` (waitlist, upvote asks, hype, placeholders,
  card-required trials, demo-only CTAs, prices). It also covers
  pricing/sign-up/legal routes, analytics, error monitoring, rate limiting,
  AI endpoints without guards, email/auth/payment/DB providers, and hosting
  hints. It never reads real `.env` files.
- `audit_url.py` covers HTTP status, redirects and HTTPS, head metadata, the
  social preview image and icons with real sizes, hero copy and CTAs, the
  same copy signals, legal and contact links, third-party analytics,
  monitoring, chat, payments and consent, broken links, that
  `?ref=producthunt` still loads, and robots/sitemap. It also opens the
  linked pricing, sign-up, demo and download pages (`key_pages`) and reads
  their prices, free-plan and card-required copy, and form lengths. If it
  reports a client-rendered shell, re-run it with
  `--html-file <out>/evidence/screens/rendered.html`.
- `capture_screenshots.cjs` saves `gallery-1270x760.png` (Product Hunt's
  gallery size), a full-page shot, a phone shot, console errors, failed
  requests, timings and mobile overflow. Look at the screenshots yourself:
  they are the best evidence for "high craft" and above-the-fold clarity. If
  Playwright is missing, say so and continue without them.

Scripts find signals; you make the judgments. Also read the files and pages
that matter: the hero/home page, pricing, the sign-up and checkout handlers,
README, metadata/layout, and any endpoint the scripts flagged. Follow the
primary CTA as a first-time visitor would, all the way to a created account
and back in again (checklist A5). Two more checks, when they're cheap:

- **Production build.** If dependencies are installed, run it. A failing
  build is a 🔴.
- **Dependency audit.** If the package registry is reachable, run
  `npm audit --omit=dev` or `pip-audit` (checklist E8). If there's no
  lockfile, work in a scratch copy, never in the user's repo.

## 3. Evaluate

Read `references/audit-checklist.md` in full and score every applicable check
as Pass / Fail (with severity) / N/A (with the reason) / Unverified. Each
failing check needs **evidence** (`file:line`, URL, field, screenshot or
script output) and a **concrete fix**. `references/product-hunt-guide.md` is
the rulebook behind the checks; cite its section when the reason isn't
obvious.

Severity and verdict:

- 🔴 **Blocker**: breaks a Product Hunt rule, makes featuring very unlikely,
  or breaks the experience for launch visitors.
- 🟠 **Major**: clearly lowers featuring odds, or wastes the traffic you get.
- 🟡 **Minor**: polish.
- ⚪ **Unverified**: needs the maker to confirm.

| Verdict | When |
|---|---|
| 🔴 Not ready | any open 🔴 |
| 🟡 Ready with fixes | no 🔴, at least one 🟠 |
| 🟢 Ready | no 🔴 or 🟠 (🟡 or ⚪ may remain) |
| 🏆 Launch-perfect | nothing open at any level, and every ⚪ confirmed |

If an unverified item could turn out to be a blocker (account younger than a
week, relaunch within 6 months, a "growth consultant" buying votes), make the
verdict conditional: "Ready once you confirm …".

Also rate **featuring potential**: Useful, Novel, High craft and Creative,
each Strong / Moderate / Weak, with one line of evidence. Editors feature
launches that spike on one or two of these; say which one this launch can
win on and how to sharpen it.

## 4. Draft and validate the launch kit

Read `references/launch-kit-guide.md`. Fill `<out>/launch-kit.json` (shape in
`assets/launch-kit.template.json`), using only facts from the evidence or the
user and marking gaps `[TODO: …]`. If the user supplied draft fields,
validate those first and report what fails, then write corrected versions.
Then run:

```bash
python3 scripts/check_launch_kit.py <out>/launch-kit.json --markdown <out>/launch-kit.md
```

Never estimate a character count. Fix every FAIL and re-run until clean. The
last line says whether the kit is **paste-ready**. TODOs and planned but
unproduced images make it "no", even with zero FAILs. Report that line as
it is, and never fill a TODO with invented facts to get to "yes". To compare
tagline options quickly:
`python3 scripts/check_launch_kit.py --tagline "…" --tagline "…"`.

Map the thumbnail and gallery to real files where they exist (screenshots
from step 2, logo files); otherwise describe exactly what to produce.

## 5. Timeline

```bash
python3 scripts/launch_timeline.py --date <YYYY-MM-DD> --tz <IANA tz> --markdown
```

This converts 12:01 AM PT (the start of the Product Hunt day, correct across
DST) into the maker's time, and lays out the T-30 → T+6 months milestones. If
the date or timezone is unknown, show the go-live time for a sensible
default, mark it ⚪, and ask. `--next-days 14` lists upcoming days with their
local go-live times. If it reports that no timezone database was found (usual
on Windows), run `pip install tzdata` and re-run it.

## 6. Write the report

Fill `assets/report-template.md` into `<out>/readiness-report.md`: verdict,
counts, summary, blockers → majors → polish (each with evidence and fix),
items to confirm, scorecard, featuring potential, launch-kit key lines,
timeline, changes made, and evidence/limits. Write it in the user's language.
Be specific ("`app/layout.tsx:5` sets `metadataBase` to localhost, so every
shared link shows a broken preview") rather than generic ("improve SEO").

Keep the report scannable. Use one row per root cause, and list every check
ID it covers. Evidence and fix take one to three sentences each. Put long
code or copy-paste snippets in an appendix at the end. A maker should get the
picture from the verdict, summary and blocker table in under two minutes.

## 7. Fix mode (repo)

If the user asked you to fix, prepare or "make it ready", or agrees after the
audit, apply the code-level fixes. Examples: remove upvote asks from UI copy;
fix metadata (absolute `og:image`, a production `metadataBase`, a Twitter
card); add missing referenced assets or icons; repair broken links; add a
`?ref=producthunt`-aware welcome banner or offer; wire analytics; put auth or
rate limits on paid-API endpoints; replace boilerplate README text. Keep each
change minimal and in the project's style, and re-run the relevant script to
prove it's fixed. Don't generate legal policies or fake content
(testimonials, metrics). Flag those for the user instead. List every changed
`file:line` in the report.

## 8. Reply

Keep the chat reply short. The report holds the detail.

- The verdict line and the counts.
- The top blockers and majors: one line each, with the fix.
- The recommended tagline (with its character count) and where the kit is.
- Go-live in the maker's timezone, if known.
- Up to five questions for the ⚪ items that matter most.
- An offer to apply the fixes, if you haven't already.

## Rules to never get wrong

- Launch day runs from 12:01 AM to 11:59 PM **Pacific Time**.
- Name ≤ 40 characters · tagline ≤ 60 · description ≤ 500 (only the first
  ~260 show) · up to 3 launch tags · up to 3 shoutouts · thumbnail square,
  240×240 · gallery ≥ 2 images (3+ recommended) at 1270×760, where the first
  image is the social preview · first comment: the first ~800 characters show.
- Pricing options: Free · Paid · Paid (with a free trial or plan). A promo
  needs an offer, a code **and** an expiration.
- **Don't ask for upvotes and don't reward them.** Ask people to visit, try,
  comment, give feedback or share. Upvote services, vote exchanges and
  upvote groups lead to removal from the homepage, and the maker is
  responsible for their consultants.
- Waitlists, closed betas, vaporware, PDFs, lists and blog posts are not
  featured. Neither are launches with no maker comment, a broken link, no
  advance scheduling, duplicates, minor features or unclear taglines.
- New accounts must wait a week before posting. Self-hunting is fine (most
  featured launches are self-hunted).
- Relaunch only after 6 months **and** with a significant update, or with a
  relaunch request.
- Promote the launch page for two weeks, then point people to the Product
  Page.

Some limits have changed over time (see the "volatile" notes in
`references/product-hunt-guide.md`). If you can reach producthunt.com,
spot-check them; if you can't, say the numbers come from the bundled
September 2026 rulebook.

## Guardrails

- Never suggest or help with vote manipulation: rings, paid or incentivised
  votes, fake or alt accounts, DM blasts. If asked, explain the rule and the
  risk, and offer legitimate alternatives.
- Don't submit, schedule or post anything on Product Hunt or social networks.
  The maker does that; you prepare it.
- Never read real env files or print secrets. The repo script only lists
  variable names from example env files.
- If a network policy blocks a host, report it and continue with what you
  have. Don't route around it.
- Never invent product facts, metrics, testimonials or makers.
- Claim exactly what the evidence shows, in the report and the chat reply
  alike. Say when a result comes from a local build, a stub standing in for
  a real API, or a staging copy rather than production. Scope each finding
  to where it occurs: the home page is not "every page".
- Only stop processes you started (keep their PIDs). Never kill by name
  pattern on a machine others may share.

## Reference files

| File | Read it when |
|---|---|
| `references/audit-checklist.md` | Every audit, in full. It has the checks, severities, evidence fields and fixes. |
| `references/product-hunt-guide.md` | You need the official rule, source or wording behind a check, or a definition. |
| `references/launch-kit-guide.md` | Drafting or reviewing any listing field, the gallery, the first comment or sharing messages. |
| `assets/report-template.md` | Writing the report. |
| `assets/launch-kit.template.json` | Creating `launch-kit.json`. |
