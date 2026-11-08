---
name: landing-page-marketing
description: Landing-page and sales-copy specialist, with scripts that screenshot the page on desktop and mobile, check every claim against real facts and score perceived value. Use it whenever someone wants a page to sell better (homepage, landing, product or store page, subscription page, pricing or plans section, features page, hero, headline, offer, CTA or testimonials). Use it to review, critique, redo or rewrite a page from pasted copy, a URL or a page file. Sales symptoms are the main signal, even when marketing or copywriting is never mentioned, such as the page "doesn't sell" or "no vende", low add-to-cart despite good reviews, bounces from ads or social traffic, few sign-ups, visitors who can't tell plans apart or pick the wrong one, or the value doesn't come across. Any language. Prefer it over UX, SEO or performance skills when the goal is getting visitors to buy. Not for ads, emails, social posts, articles, choosing a pricing model, or pure design-to-code or accessibility work.
---

# Landing page marketing

A landing page has one job: make the right visitor believe the product is worth more to them than
it costs, and make the next step easy. Everything below serves that.

**Perceived value** is not what the product is; it's what the visitor *believes* they'll get,
weighed against what they believe it will cost them. A useful working model (Hormozi's value
equation, set in the context of the visitor's alternatives, per April Dunford) is:

```
                     dream outcome  ×  perceived likelihood of getting it
perceived value  =  ─────────────────────────────────────────────────────   compared with the price
                     time to get it ×  effort & sacrifice  ×  risk            and the real alternative
```

A page raises perceived value by making each term *visible and believable*: a vivid, specific
outcome; proof that it works for someone like me; a fast first win; low effort; little risk; and a
price that looks small next to the alternative. It never does it by inventing things. Fake
scarcity, invented numbers and made-up testimonials borrow trust that the page then loses, and in
most markets they're illegal.

The principles that make this work, and that the rest of the skill applies:

1. **Research first.** Ogilvy studied a product until he found the fact that sold it: the
   Rolls-Royce clock headline came out of weeks of reading. Good copy is mostly *found*, in the
   product's facts and in customers' own words, not invented.
2. **Specific beats general.** Hopkins: platitudes "roll off the human understanding like water
   from a duck". A number, a name, a scene the reader can picture, a mechanism.
3. **Enter the conversation already in the reader's mind** (Collier). Where the page starts
   depends on what the visitor already knows: Schwartz's awareness levels decide the opening and
   the length.
4. **Clarity before persuasion.** Visitors decide within seconds whether to stay. If the first
   screen doesn't say what it is, who it's for and why it matters, nothing below it gets read.
5. **Proof multiplies the promise.** An unbelieved promise adds nothing. Put proof next to each claim.
6. **Value is relative.** Price is judged against an anchor. Choose the honest one: what the
   buyer does today and what that costs.
7. **Show, don't claim.** Show the product working, a real result, a named customer. Adjectives
   ("powerful", "seamless") are what's left when facts are missing.

Script paths are relative to this skill's directory. Python scripts need only the standard library;
`capture_page.cjs` needs Node and Playwright.

## 1. Scope the job

Work these out from the request and the files, without interrupting the user:

- **Mode.**
  - **Audit**: a URL, HTML file, repo page or pasted copy to critique.
  - **Create / rewrite**: a new page or a new version of an existing one.
  - **Focused**: just a hero, headline, pricing section, offer, CTA or testimonials. Do only that
    part, with the same evidence standard, and offer the full treatment afterwards.
- **Product and offer.** What it is, the price, plans, trial, guarantee.
- **Page goal.** The one action: buy, start a trial, book a call, join a list.
- **Traffic.** Where visitors come from (ads, search query, social, newsletter, Product Hunt,
  direct) and therefore what they already know. If unknown, assume the most likely source and say so.
- **Language and market.** Write in the language of the page or the user. Use local currency and
  norms.
- **Deliverable.** A copy deck, page code in the user's stack (edit the real components when
  there's a repo), a standalone HTML file, or an audit report. If they asked for "a page", build it.

## 2. Gather evidence

Make an output folder (default `landing-page/` in the working directory, or where the user says).
Keep evidence under `landing-page/evidence/`.

**The existing page** (audit or rewrite):

```bash
node scripts/capture_page.cjs --url <url or file:///abs/path.html> --out <out>/evidence --dump-html
python3 scripts/extract_page.py <url or file> --json <out>/evidence/page.json
python3 scripts/copy_lint.py <url or file> --facts <facts file> --json <out>/evidence/lint.json
```

- `capture_page.cjs` saves desktop (1440×900) and mobile (390×844) first-screen shots, a full-page
  shot, and `fold.json`: exactly which headings, CTAs, images and prices are visible in the first
  screen, load timings and mobile overflow. **Look at the screenshots.** They are the best evidence
  for the 5-second test. If Playwright is missing, say so and continue with the extractor.
- `extract_page.py` gives the message hierarchy in page order: hero, sections, CTAs, forms (field
  count = friction), prices, quotes. If it warns about a client-rendered page, pass
  `--html-file <out>/evidence/rendered.html`.
- `copy_lint.py` flags hype, unproven claims, fake-urgency language, generic CTAs, placeholders,
  unsourced numbers (with `--facts`), and you/we balance and readability. It finds signals; you judge them.

**In a repo**, find the page's source (e.g. `app/page.tsx`, `index.html`, `src/pages`, CMS
content, i18n files), the pricing source of truth, and any facts in README/docs. Run the page
locally if that's cheap, then capture it.

**Product facts.** Build a numbered fact list (F1, F2…) from the user, their files, the site and
public reviews, each with its source. These are the only facts the page may state.

**Voice of the customer.** Collect customers' exact words: testimonials the user supplied, reviews
(G2, Google, App Store, Amazon, Trustpilot), support tickets, interviews, community threads. Sort
them into pains, desired outcomes, objections and reasons they chose it. Headlines and section
titles work best in these words. If you can't reach any, ask for them. Until then, write from
product facts and mark where customer language should go.

**Ask only what blocks you.** At most 3–5 questions, batched, about facts that change the page
(price, guarantee terms, a result number, permission to use a quote). For everything else proceed
and mark `[TODO: …]`.

## 3. Build the value brief

Read `references/value-perception.md`. Fill `assets/value-brief.template.md` into
`<out>/value-brief.md`:

- the facts table;
- who it's for and their trigger moment;
- customer language;
- **awareness level and market sophistication** of the main traffic, with the evidence for your call;
- **the alternatives** (including doing nothing) and what each costs the buyer;
- unique attributes → value → proof;
- **the value ledger**: each lever with what you can show and what's missing;
- the big idea and headline options;
- objections → answers → proof;
- the offer;
- a **claims register**.

For a focused task, a short version of the relevant parts is enough, but always keep the facts and
claims register.

This brief is where the persuasion is decided. The copy only expresses it. If the brief is thin
(no proof, no clear outcome), the fix is more facts, not more adjectives. Tell the user what
evidence would raise perceived value most (a result metric, three named testimonials, a guarantee
they're willing to offer).

## 4. Choose the page architecture

Read `references/page-architecture.md`. Pick the section order and length from:

- awareness level (it decides the opening);
- price and risk (higher stakes need more proof and more objection handling);
- traffic source (the first screen must match the ad or query that brought them);
- page type (SaaS, e-commerce product, service, course or info product, app, dev tool).

Give each section a **job**: which lever it moves or which objection it answers. A section without
a job gets cut.

## 5. Write the copy

Read `references/copywriting.md` (rules and examples) and `references/advertising-canon.md` (the
principles behind them) as needed. Fill `assets/copy-deck.template.md` into `<out>/copy-deck.md`:

- **Headline:** write several on different angles (outcome, news, mechanism, pain, identity,
  offer) and pick the one that is most specific, most believable and most clearly *only yours*.
  Keep 2 runners-up for testing.
- Tie every feature to the outcome it produces. Put proof next to the claim it supports.
- CTAs say what the visitor gets, with the risk reducer right under the button.
- Write the price frame with real math, and check it.
- Every number, name and quote traces to a fact ID. Tag claims `[F#]` in the deck and remove the
  tags from visible copy when building. Record derived math (per-unit prices, differences, ratios)
  as facts too, with the calculation, so it can be checked.

**Honest is not thin.** A page built only from true facts must still sell as hard as one that
invents. It gets there with structure and demonstration, which need no new facts:

- **Show the experience:** a sample of what the product produces (a reminder email, a lesson list,
  what's in the box, a before/after), clearly labelled "Example" on screen. Also a timeline of
  what happens after the click.
- **Persuasive blocks built from what you know:**
  - a before → after bridge in the customer's words;
  - "how it works" steps;
  - a comparison with the real alternatives;
  - a "for you / not for you" fit block;
  - objections answered with proof;
  - a sticky mobile CTA on long pages.
- **Write with conviction.** Use the strongest framing the facts support, in plain declarative
  sentences. Hedge only where the facts are uncertain.
- **When the buyer's key question can't be answered from the facts** (what exactly arrives, what
  happens when the trial ends), design the section so the page reads complete without it. Ask the
  owner for the answer. Don't guess it.

## 6. Build the page (when the deliverable is a page)

- **Existing repo:** edit the real components, content files and i18n strings in the project's
  style. Keep the design system. Don't rewrite what doesn't need it.
- **No stack:** one self-contained, semantic, mobile-first HTML file. Inline CSS, no external
  dependencies (system fonts, inline SVG), fast, accessible (landmarks, alt text, contrast, visible
  focus, 44px tap targets). Include the title, meta description and Open Graph tags.
- **Design serves the message.** Build visual hierarchy around the headline and primary CTA. Show
  the product or the outcome (real screenshots, a real product photo, a demo) rather than stock
  imagery; where no asset exists, leave a clearly labelled placeholder that says what to shoot or
  capture. Keep one primary CTA style and repeat it after key sections.
- Only **truthful urgency**: a real deadline or real stock, stated with its reason. No fake timers,
  no fake "was" prices.
- **Publishable as delivered.** Visitors must never see a TODO. Missing facts go in HTML comments;
  sections that depend on them go in `hidden` elements with a `data-todo` note (a testimonial slot
  that appears once real quotes are added); unknown links go to `#` with a comment. List every
  placeholder in the reply. The visible page must read as complete and honest today.
- **Illustrative content is labelled on screen** ("Example", "Sample reminder"). Mock invoices,
  names, amounts and dates must not read as real customers or results.
- **Placeholder details aren't facts.** Don't make up a domain, email, social handle, phone number,
  address, delivery time, plan feature or policy (trial end, fees, returns). Use a comment or a
  neutral link and ask.

## 7. Verify before delivering

1. `python3 scripts/copy_lint.py <out>/copy-deck.md --facts <out>/value-brief.md`, and again on the
   built page (the page lint reads only visible text: comments and `hidden` sections are skipped).
   Resolve every `unsourced`, `placeholder` and `urgency` hit: source it or remove it. A
   `placeholder` hit on the page means a visitor would see it. Review each `claim` hit against the
   claims register.
2. Render the built page with `capture_page.cjs`. Look at both first screens: the 5-second test
   must pass on mobile too, with no overflow and the primary CTA visible.
3. Score it with `references/audit-rubric.md` and `scripts/value_score.py`. Iterate on the weakest
   lever you can fix with facts you have. Fixing the page is your job. Filling missing facts is the
   user's, so list those.

## 8. Audit reports

For an audit, fill `assets/audit-report.template.md` into `<out>/audit-report.md`:

- verdict and score (from `value_score.py`);
- **the one thing**;
- the 5-second test per viewport;
- the value ledger;
- the top fixes ranked by impact on perceived value, each with evidence;
- claims and compliance;
- rewrites of at least the hero, before → after, each tied to a finding;
- experiments worth running;
- questions.

Keep each finding to what it is, the evidence and the fix. Scope findings to where they occur. If
the user wants the rewrite too, continue with steps 3–7.

## 9. Reply

Keep the chat reply short; the files hold the detail.

- What you made and where it is.
- The core idea: the promise and why it's believable.
- For audits, the score, the one thing and the top 3 fixes.
- What you removed or refused and why, in one line each.
- The `[TODO]`s and questions that would raise perceived value most.

## Rules that protect the client

These keep the page persuasive *and* safe; details and legal sources are in
`references/proof-and-compliance.md`.

- **Never invent facts:** no numbers, results, customer counts, testimonials, reviews, names, logos,
  awards, press mentions, certifications, guarantees, policies or plan features. Mark gaps as
  `[TODO: …]` in the working files (hidden or commented out on a built page) and list them.
  If the user asks you to fabricate, decline that part briefly, explain the risk (FTC rules on fake
  reviews and testimonials, EU and UK unfair-practice law, lost trust) and offer the honest version
  that still sells.
- **Results must be typical or clearly qualified.** "Up to" and best-case numbers need the typical
  result stated.
- **Urgency and scarcity only if true.** A real deadline or real limit, stated with its reason.
  No resetting timers, fake stock counters or "only 3 left" that isn't so.
- **Honest prices:** all mandatory fees in the headline price, a real reference price behind any
  "was", and clear renewal and cancellation terms for subscriptions.
- **Don't disparage competitors with unprovable claims.** Compare on verifiable facts.
- **Testimonials:** real, used with permission, identified as accurately as the customer allows,
  with material connections (paid, free product, employee) disclosed.

## Reference files

| File | Read it when |
|---|---|
| `references/value-perception.md` | Building the value brief; deciding how to raise perceived value; offers, pricing and anchoring. |
| `references/page-architecture.md` | Choosing sections, order and length; the hero; page-type blueprints. |
| `references/copywriting.md` | Writing or editing headlines, body, CTAs, testimonials and FAQs; before/after examples. |
| `references/advertising-canon.md` | You need the principle or source behind a rule (Ogilvy, Hopkins, Schwartz, Caples, Sugarman, Sutherland, Dunford, Cialdini), or research evidence and its strength. |
| `references/proof-and-compliance.md` | Any claim, testimonial, review, urgency, price or comparison; when a user asks for something that may be deceptive. |
| `references/audit-rubric.md` | Scoring any page, including your own draft. |
| `assets/*.template.md` | Writing the value brief, copy deck or audit report. |
