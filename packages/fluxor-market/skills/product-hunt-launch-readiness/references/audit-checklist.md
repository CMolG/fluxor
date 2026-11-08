# Launch-readiness checklist

Score every applicable check as **Pass**, **Fail** (with severity), **N/A**
(with the reason) or **Unverified** (what would confirm it). The default
severity is given for each check; move it up or down only with a stated
reason (e.g. a demo-only CTA is a 🔴 for a consumer app but a 🟠 for
enterprise infrastructure that also has a sandbox).

- 🔴 **Blocker**: breaks a Product Hunt rule (risk of penalties or removal),
  makes featuring very unlikely under the official guidelines, or breaks the
  experience for launch-day visitors.
- 🟠 **Major**: clearly lowers the chance of being featured, or wastes the
  traffic you do get.
- 🟡 **Minor**: polish that separates a good launch from a great one.
- ⚪ **Unverified**: can't be seen in the repo or site, so ask the user.

Sources in brackets refer to `product-hunt-guide.md` sections. "Repo" and
"Web" say where to find the evidence (`audit_repo.py` / `audit_url.py` fields
in `code`).

Contents: A Featuring eligibility · B Listing assets · C First impression ·
D Try-ability & conversion · E Launch-day robustness · F Trust & polish ·
G Rules & promotion · H Account, schedule & team · I After the launch ·
J Product-type add-ons

---

## A. Featuring eligibility

**A1 · Usable today, not a waitlist.** 🔴 [§10]
Unfinished or waitlisted products, vaporware and closed betas aren't featured.
Web: `signals.waitlist`, `signals.email_capture_forms`, and whether any CTA
leads to a working sign-up, download or install (`signals.live_product`,
`content.ctas`). Repo: `copy_signals.waitlist`; a real sign-up/app route
exists and isn't feature-flagged off.
Fix: launch when strangers can use the product unaided. Until then, use a
Coming Soon page to collect followers, and launch later.

**A2 · It's a product, not content.** 🔴 [§10]
A PDF guide, blog post, list or plain document isn't featured.
Check what a visitor actually gets.
Fix: launch the tool built around the content, or pick another channel.

**A3 · Substantial launch, not a minor feature.** 🟠 [§10 #6]
"No small boy stuff". A small update belongs in a Product Forum post or
changelog, not a new launch.
Repo: git tags / CHANGELOG entries since the previous launch.
Fix: bundle features into a meaningful release.

**A4 · Clear differentiation.** 🟠 [§10 Novel]
If the landing page can't say in one line what's new compared with the
obvious alternatives, editors can't either.
Web/Repo: hero copy, h1/h2, README intro.
Fix: state the difference ("open-source X", "X for Y", "does Z without W")
in the hero and the description.

**A5 · The core flow works end to end, with no visible bugs.** 🔴 when the core flow breaks, 🟠 when it's rough [§10 High craft]
Walk the path a first-time visitor takes: landing → sign-up → account
actually created → first use → (payment) → back in later (log in). Common
breaks: a checkout success URL that 404s, form fields the handler ignores,
verification emails with no link, no login page. If the product takes
payments, check three more things: a webhook (not the redirect) grants
access, quantities match per-seat pricing, and a trial can be cancelled.
Also look for console errors, broken layouts, lorem ipsum, template
boilerplate and dead ends.
Web: `capture.json` (console_errors, failed_requests), screenshots,
`key_pages`, `signals.placeholders`. Repo: read the sign-up/checkout
handlers and check that every redirect target route exists;
`copy_signals.placeholders`; whether the build passes, when that's cheap.
Fix: repair the flow end to end, then walk it once in production mode.

**A6 · No broken links.** 🔴 [§10 #3]
The listing's link and every CTA on the landing page must resolve. (Product
Hunt: "this happens more than you think".)
Web: `links.broken`; also open the listing's website link yourself.
Fix: repair or remove each broken link, then re-run the audit.

**A7 · Relaunch rules.** 🔴 if violated, ⚪ if unknown [§8, §10 #5]
Same product or company launched in the last 6 months, or no significant
update since then, means a relaunch request is needed. Duplicate launches
aren't featured.
Web: an existing Product Hunt badge on the site (`third_party.product_hunt`)
suggests a previous launch. Repo: tags, CHANGELOG.
Fix: wait, ship the significant update, or file a relaunch request.

## B. Listing assets
Validate drafted or supplied fields with `check_launch_kit.py`, and never
count characters by eye.

**B1 · Name ≤ 40 characters**, and it matches the brand on the site. 🔴 if over, 🟡 if inconsistent [§3]

**B2 · Tagline ≤ 60 characters, clear, no hype or emoji.** 🔴 if over, 🟠 if unclear or hyped [§3, §10 #7]
It should say what the product does or how it helps. Test: could a stranger
repeat what the product does after reading it once?

**B3 · Description ≤ 500 characters, core message in the first ~260.** 🔴 if over, 🟠 if the visible part is vague [§3]
Say what's new or different, and which features stand out.

**B4 · Up to 3 relevant launch tags.** 🔴 if more than 3, 🟡 if generic [§3]

**B5 · Thumbnail: square, 240×240, JPG/PNG/GIF.** 🟠 [§3]
There needs to be a source asset of at least 240×240 (square or vector).
Web: `best_icon`, `thumbnail_source_ok`. Repo: `images.best_square_logo`.
Fix: export the logo mark at 240×240 (`capture_screenshots.cjs --thumbnail`
can render one); an animated GIF plays on hover.

**B6 · Gallery: at least 2 images (3+), 1270×760, showing the real product.** 🔴 if fewer than 2 exist or can be made, 🟠 if weak [§3]
The first image is the social preview when the launch link is shared.
Use screenshots, not stock photos or marketing fluff. End with social proof
or a CTA.
Web: `capture_screenshots.cjs` shots (gallery-1270x760.png is at the exact
size). Repo: `images.gallery_ready_count`, `screenshot_candidates`.

**B7 · Video or interactive demo.** 🟡 [§3]
YouTube/Loom demo, or Arcade/Storylane/Hexus/Supademo/Layerpath/ScreenSpace
(free for Product Hunt launches). Raise it to 🟠 when the product is hard to
grasp from stills (dev tools, AI agents, workflows).

**B8 · Makers tagged, with complete profiles.** 🟡, ⚪ [§3, §9]

**B9 · Maker first comment prepared.** 🔴 if missing [§3, §5, §9, §10 #2]
Who you are, why you built it, the problem, what it does, what's new, and a
specific question for feedback. Key content goes in the first ~800
characters; use short paragraphs or bullets. It must not ask for upvotes.

**B10 · Up to 3 shoutouts.** 🔴 if more than 3, 🟡 if none [§3]

**B11 · Pricing option is accurate.** 🟠 [§3]
Free / Paid / Paid (with a free trial or plan) must match the pricing page. A
free plan or trial means "Paid (with a free trial or plan)", or "Free" if
everything is free.
Web: `signals.pricing`, `signals.free_offer`, pricing page. Repo:
`copy_signals.prices`, `free_offer`, `trial_config`, `routes.pricing`.

**B12 · Promo offer is complete and redeemable.** 🟡, or 🟠 if offered but broken [§3, §7]
Offer, code and expiration must all be filled. The product must accept the
code (checkout coupon or promotion codes enabled).
Repo: `copy_signals.promo_code_support` (e.g. Stripe
`allow_promotion_codes`).

**B13 · Links are minimal and correct.** 🟡 [§3]
The primary link goes to the page that converts. Store or GitHub links only
where visitors need them.

## C. First impression (message match)

**C1 · The hero says what it is and who it's for, above the fold.** 🟠
The h1 or hero should echo the tagline. Visitors decide in seconds.
Web: `content.h1`, `hero_text`, the gallery-1270x760 and mobile screenshots.
Repo: page/hero components.

**C2 · A primary CTA is visible and works.** 🔴 if missing or broken
Examples: "Start free", "Download", "Add to Chrome", "npm i …".

**C3 · Screenshots or a demo on the landing page.** 🟡
Show the real product.

**C4 · Works on mobile.** 🟠
Much Product Hunt traffic comes through the app and newsletter.
Web: viewport meta, `capture.json.mobile.horizontal_overflow` and
`overflowing_elements`, the mobile screenshot. If `capture.json.missing_fonts`
is non-empty, the page rendered with fallback fonts, so text-driven overflow
may not reproduce on real phones. Report it with that caveat and ask for a
check on a real device, or reproduce it with the site's actual fonts.

**C5 · Loads fast.** 🟠 if it's clearly slow (multi-second loads, huge pages)
Web: `elapsed_ms`, `capture.json.timings`. For a deep performance audit use
Lighthouse/PageSpeed or a dedicated web-performance skill; here, only flag
what would lose launch visitors.

## D. Try-ability & conversion

**D1 · Try before paying.** 🟠 (🔴 for consumer or prosumer tools with no way in at all)
Offer a free plan, a free trial without a card, an open-source/self-host path,
or a public demo/playground. Community-observed: launches with no free way
in struggle to get featured [§11].
Web/Repo: `free_offer`, `no_card_required`, `credit_card_required`,
`trial_config` vs `card_optional_config`.

**D2 · Low-friction sign-up.** 🟠
One-click OAuth or email plus password; no long qualification forms, no
phone number and no card for a trial.
Repo: sign-up page fields. Web: forms `field_count`.

**D3 · Not sales-gated.** 🟠 (🔴 if "Book a demo" / "Contact sales" is the only way in)
Web: `signals.demo_or_sales_only_ctas`.

**D4 · Fast time-to-value after sign-up.** 🟡
Sample data, templates, a guided first run. Empty dashboards lose visitors.

**D5 · A welcome for Product Hunt visitors.** 🟡 [§3, §7]
Optional banner or offer shown for `?ref=producthunt`, plus the promo code.
It must never ask for upvotes.

## E. Launch-day robustness
A featured launch can bring thousands of visitors in a few hours, concentrated
around 12:01 AM PT and US mornings.

**E1 · Hosting handles a spike.** 🟠, ⚪
Use static or cached pages where possible, serverless/autoscaling, and DB
connection pooling. Check free-tier limits of hosting, DB and auth providers.
Repo: `hosting_hints`, `dependencies_detected.database`, caching config.

**E2 · Paid APIs protected.** 🔴 if a public endpoint calls a paid AI/API with no auth or rate limit
Otherwise 🟠: rate limits, per-user quotas, spend caps and billing alerts
on OpenAI/Anthropic/etc. Unprotected endpoints get abused, run up costs or
exhaust quotas, and the product dies mid-launch.
Repo: `ai_endpoints[].has_auth_or_rate_limit_guard`,
`dependencies_detected.rate_limiting`, `bot_protection`.

**E3 · Sign-up abuse protection.** 🟡 (🟠 when free usage costs money)
Captcha or Turnstile, email verification, per-IP limits.

**E4 · Transactional email can keep up.** 🟠 when sign-up needs email verification
Free tiers are often capped at around 100 emails a day, so check the
provider's daily cap, and that SPF/DKIM are set up.
Repo: `dependencies_detected.email`.

**E5 · Analytics, with Product Hunt attribution.** 🟠
You need to measure the launch. Product Hunt appends `?ref=producthunt` to
outbound links; analytics must keep it, and the app must not break on
unknown query params. Track the conversion (sign-up, install, checkout) as
an event, not just page views. A form that posts to a third-party page
(Formspree, Typeform, a hosted checkout) loses the visit unless it sends an
event or the source first.
Web: `third_party.analytics`, `ref_param_check`. Repo:
`dependencies_detected.analytics`, `copy_signals.ref_or_utm_handling`.

**E6 · Error monitoring and uptime alerts.** 🟠
You'll need to fix things live. Web: `third_party.error_monitoring` (only
client-side tools are visible there). Repo:
`dependencies_detected.error_monitoring`.

**E7 · Support channel staffed on launch day.** 🟡
Chat widget, support email or Discord.
Web: `third_party.chat_support`, `links.contact`.

**E8 · No known critical vulnerabilities in dependencies.** 🔴 for a critical, remotely exploitable flaw in internet-facing code; 🟠 for high severity
Launch day puts the most eyes you'll ever have on the product, attackers
included.
Repo: `npm audit --omit=dev`, `pnpm audit` or `pip-audit`. If there's no
lockfile, run `npm install --package-lock-only --ignore-scripts` in a
scratch copy first, and never write into the user's repo. Do this only when
the registry is reachable; otherwise mark it ⚪.
Fix: upgrade to the patched release the audit suggests, rebuild and re-test.
Rotate secrets if a vulnerable build was public.

## F. Trust & polish

**F1 · Social preview works.** 🟠
og:title, og:description and an absolute og:image (about 1200×630) that loads,
plus `twitter:card=summary_large_image`. No localhost or relative URLs in
production.
Web: `social_image.issues`. Repo: `metadata.og_image`, `metadata_base`,
`missing_local_assets`, `localhost_urls`.

**F2 · Favicon and app icons.** 🟡
They should be consistent with the Product Hunt thumbnail.

**F3 · Privacy policy and terms.** 🟠 when the product collects personal data or payments (🟡 otherwise)
Add cookie consent where the law requires it (EU/UK). Web: `links.legal`.
Repo: `routes.privacy`, `routes.terms`.

**F4 · Contact information.** 🟡
Web: `links.contact`. Repo: `copy_signals.contact_links`.

**F5 · No placeholders, boilerplate or dead ends.** 🟠 (🔴 when the placeholder is on the main CTA path)
Lorem ipsum, "Acme", framework README, `href="#"` links, "coming soon"
sections in navigation. Also look for placeholder service IDs that silently
drop users: form endpoints like `formspree.io/f/xyzabc`, chat widget IDs
like `…-demo`, Stripe `price_pro_monthly`-style IDs, and `example.com` API
hosts.

**F6 · Indexable.** 🟠 if `noindex` or `robots.txt Disallow: /` is left on production
People search for you after the launch.

**F7 · HTTPS everywhere.** 🔴 if the production site isn't HTTPS

**F8 · Hero copy without hype.** 🟡
The same standard as the tagline, because visitors compare them.
Web: `signals.hype_in_headlines`. Repo: `copy_signals.hype_in_headlines`.

**F9 · Claims are true and checkable.** 🟠
User counts ("2,000+ on the waitlist"), customer logos ("used by Fortune
500"), testimonials, benchmarks and "infinite"/"unlimited" promises. The
Product Hunt crowd tests them in the comments, and unsubstantiated claims
can also be a consumer-protection problem.
Fix: substantiate each claim, soften it, or remove it. Never invent
replacements.

## G. Rules & promotion

**G1 · Nothing asks for upvotes.** 🔴 [§4, §5]
Site banners, emails, social drafts, DMs and the first comment should ask
people to check it out, try it, comment or share feedback, never to vote.
Web: `signals.upvote_asks`. Repo: `copy_signals.upvote_asks`. Launch kit:
`check_launch_kit.py` scans posts and messages.

**G2 · No upvote services, vote exchanges, paid votes, incentives or fake accounts.** 🔴, ⚪ [§4]
The maker is responsible for any consultant's tactics. Ask the user if
anything like that is planned. Never suggest it.

**G3 · No spam plan.** 🟠, ⚪ [§4]
No mass cold DMs or emails, and no posting in communities you aren't part of.

**G4 · Sharing plan ready.** 🟡, ⚪ [§4, §5]
Drafted posts for your channels, an email to users and newsletter,
personal messages to people who'd genuinely care, and community posts
where you're a member. Sharing the direct launch link is fine.

**G5 · Official badge or embed only.** 🟡 [§4, §7]
Use Product Hunt's embed and badge code (live-upvote embed on launch day,
award badge afterwards), not custom "vote for us" widgets.

## H. Account, schedule & team

**H1 · The posting account is at least 1 week old.** 🔴 if not, ⚪ [§2]

**H2 · Makers are active community members with complete profiles.** 🟡, ⚪ [§2]

**H3 · The launch is scheduled in advance, with a Coming Soon page to collect followers.** 🟠, ⚪ [§2, §10 #4]

**H4 · Launch time and day are chosen deliberately.** 🟡 [§1, §2, §5]
12:01 AM PT gives the full day. Pick weekday or weekend on purpose. Run
`launch_timeline.py` for local times.

**H5 · The team covers the whole Pacific day for replies.** 🟠, ⚪ [§5]
Put a rota in place; replying to every comment is the main job of the day.

**H6 · Your community can take part genuinely.** 🟡, ⚪ [§2, §11]
Tell your users and community early, and invite them to follow the Coming
Soon page. Activity from brand-new accounts carries little weight and can be
flagged as spam. Frame this as joining the conversation, never as "we need
your vote".

**H7 · Not colliding with another launch from the same company that day.** 🟡, ⚪ [§6]

## I. After the launch

**I1 · Follow-up plan.** 🟡, ⚪ [§7]
Thank commenters, email new sign-ups, remind them of the offer, and keep
replying for days.

**I2 · Two-week plan.** 🟡 [§8]
Promote the launch page for two weeks, then point links to the Product
Page, add the badge or award to the site, ask for reviews, and post updates
in the Product Forum.

**I3 · Next significant release planned for a future launch.** 🟡 [§8]
Allow at least 6 months between launches.

## J. Product-type add-ons
Apply the rows that match `product_type_guess` (or what you see).

| Type | Extra checks |
|---|---|
| **Mobile app** | 🔴 Live on the App Store / Google Play in the main markets (TestFlight or beta-only counts as a closed beta). 🟠 Store screenshots and description match the listing. 🟡 Deep links from the site to the stores. |
| **Browser / IDE extension** | 🔴 Published and approved on the store (store review can take days, so don't launch while it's pending). 🟠 Store listing icon (128×128) and screenshots. 🟡 Onboarding page after install. |
| **Desktop app** | 🟠 Signed and notarised builds (unsigned apps trigger scary OS warnings; see `copy_signals.desktop_signing_config`). 🟠 Downloads for the platforms you claim. 🟡 Auto-update. |
| **Developer tool / library / CLI** | 🟠 README is the landing page: a one-line "what & why", install command, quickstart, a GIF or screenshot. 🟠 Package published and install works. 🟡 Docs site, examples, license badge. |
| **Open source** | 🔴 Repository public and license present (`license`). 🟠 README quality as above, CONTRIBUTING, issues enabled. 🟡 Tick the open-source option and add the GitHub link. |
| **API / infrastructure** | 🟠 Self-serve API key or sandbox, docs, pricing. 🟡 Interactive playground. |
| **AI product** | 🔴 E2 (protected paid APIs). 🟠 Output quality demonstrated with real examples in the gallery. 🟠 Clear data/privacy statement. |
| **Integrations & OAuth** (Google, Microsoft, Zoom, Slack, GitHub…) | 🔴 Core-flow OAuth apps verified and marketplace listings approved. An unverified Google app requesting sensitive scopes shows a warning screen and is capped at 100 users, and Zoom/Slack apps need marketplace review for public installs, so never launch while a review is pending. ⚪ when you can't see the status. |
