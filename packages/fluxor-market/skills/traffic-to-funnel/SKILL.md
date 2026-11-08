---
name: traffic-to-funnel
description: Turns real website traffic and behavior data (GA4, Plausible, Umami, Matomo, PostHog, Clarity, Hotjar, Search Console, logs, CSV or screenshots) into an actionable diagnosis and a per-product funnel. Identifies what visitors consume and which elements they interact with; detects weak elements, rage clicks, dead clicks, quick backs, form abandonment and leaks; amplifies what works using the SEO, UX and useful-innovation guidelines bundled in the skill; repairs what fails with a pain-point analysis; defines the monetization that closes the conversion; and synthesizes one funnel per product with metrics, hypotheses and experiments. Use it WHENEVER web analytics data is on the table or the user asks "what works on my site", "why doesn't it convert", "where do people drop off", "what should I amplify", "how do I monetize this" or "design my funnel"; and when auditing, optimizing or monetizing a landing page, blog, free tool, portfolio or digital product, even if funnel, CRO or analytics are not mentioned.
---

# Traffic to funnel

Turns observed behavior into a plan with a fixed order: first amplify what already attracts, then repair what pushes people away, finally place monetization where intent peaks. The deliverable is a report with a fixed structure and one funnel per product with metrics, hypotheses and prioritized experiments.

The skill is tool-agnostic: it works from any analytics, behavior or search export, normalized into the CSV schema in `references/data-sources.md`. If `ux-psychology` or `research-radar` (in this repository), a technical SEO/performance-audit skill or a content-judging skill is installed, use it to go deeper in its own area. This skill is self-sufficient without them: the SEO, UX and innovation guidelines it needs are in `references/`.

## Principles that govern the whole analysis

1. **Evidence before opinion.** Every claim about the site comes from a concrete data point (page, element, metric, period). When there is no data, write "no data" and ask for it; never fill the gap with a plausible guess. A short, true report beats a long, decorated one.
2. **Amplify → repair → monetize, in that order.** Amplifying strong elements increases the traffic that later reaches the weak points and the close. Repairing before amplifying optimizes on noise; monetizing before acquisition is stable burns the trust of the little traffic there is.
3. **Thresholds are relative to the site itself.** "Strong" and "weak" are defined by the site's own percentiles (P75 / P25), never by generic internet figures. External benchmarks only calibrate expectations.
4. **Segment before concluding**, at minimum by device, traffic source and new vs. returning. An element that looks "weak" in aggregate is usually broken on mobile, or a CTA only returning visitors see.
5. **Nothing that deceives the user.** Neither UX nor monetization recommendations may use dark patterns (fake urgency, confirmshaming, obstructed cancellation, drip pricing, pre-ticked boxes). Beyond being illegal in the EU (DSA art. 25, consumer law), they destroy the trust the funnel rests on.
6. **Every recommendation carries a hypothesis, a metric and a success criterion.** Without those it is an idea, not a recommendation, and ideas do not enter the backlog.
7. **Correlation is not cause.** Data says *what* happens; *why* is a hypothesis until a session recording, a user test or an experiment confirms it. The report always separates observation from interpretation.

## Inputs

Ask for or locate these sources. The first two are enough to work; the rest sharpen the analysis.

| Priority | Source | What it provides |
|---|---|---|
| Essential | Page analytics (GA4, Plausible, Umami, Matomo, PostHog) | views, sessions, entrances/exits, time, scroll, sources, conversions |
| Essential | Interaction events (CTA clicks, forms, video, downloads, copy) | what they interact with and how much |
| Very useful | Behavior tools (Clarity, Hotjar, PostHog replay) | rage clicks, dead clicks, error clicks, quick backs, heatmaps, recordings |
| Very useful | Search Console (or equivalent) | queries, impressions, CTR and position per URL |
| Useful | Business data (CRM, payments, newsletter, forms) | the real close of the funnel, not just the proxy |
| Useful | Server logs, CrUX/PageSpeed | bots, 4xx/5xx errors, real-world performance |
| Context | From the user: products, business goal, current model, period, recent changes | without this the funnel cannot be synthesized |

`references/data-sources.md` explains what to export from each tool, how to normalize it into the skill's CSV schema and exactly what each signal means (definitions and minimum samples). With normalized CSVs, run `scripts/analyze_traffic.py`: it returns consumption rankings, strong/weak elements, friction flags and SEO opportunities computed with the site's own percentiles, so the analysis starts from numbers rather than mental arithmetic.

If the user only has screenshots or a dashboard, work with what exists and mark in the report which conclusions are provisional and which data point would confirm them.

## Workflow

The six phases map to the six deliverables. Do not skip phases: 3 depends on 1, 4 on 2, 5 on 3 and 4, and 6 on all of them.

### Phase 0 — Context and scope

Before looking at a single number, settle with the user:

- **Products**: the list of what the site sells or wants to sell (service, SaaS, tool, content, lead). Each product gets its own funnel in phase 6.
- **Business goal for the period**: leads, sales, retention, positioning.
- **Current monetization model** (or "none").
- **Period analyzed** and whether anything contaminates the series (redesign, campaign, outage).
- **Conversion definition** used by the analytics and whether it matches the business definition.

If the user does not provide it, ask for the essentials (products and goal) and state the rest as explicit assumptions in the report's "Data and scope" section.

### Phase 1 — What they consume and what they interact with

Deliverable: the site's **value map**.

1. Run the script or build by hand two tables: pages (views, time, 90 % scroll, entrances, exits, conversion) and elements (impressions, clicks, CTR, attributed conversions).
2. Classify **consumption** per page with the script's score (mean rank of views, time and scroll) and **interaction** per element with CTR over impressions. An element is only classified above the minimum sample (100 impressions by default).
3. Cross both: the quadrants that matter are *high consumption + high interaction* (what attracts and engages) and *high consumption + low interaction* (attention already won but not used).
4. Add the **entry** dimension: which pages are doors (landing pages) and from which source/query. With Search Console, which queries bring people to each page.
5. Segment the top 5 pages and elements by device and by new vs. returning. Note differences above 20 percentage points.

Write the conclusion as one sentence per strong page: "*X* attracts [segment] from [source] because [evidence: time, scroll, query] and the interaction it triggers is [element, CTR]".

### Phase 2 — Weak elements and friction signals

Deliverable: the **friction table**, ordered by traffic affected.

Look for these, in order of severity:

| Signal | What it is | How it is detected |
|---|---|---|
| High exposure, low interaction | element seen by many, clicked by almost nobody | impressions ≥ P75 and CTR ≤ P25 |
| Rage click | repeated clicks in the same spot in < 1 s | Clarity/Hotjar/PostHog; ≥ 1 % of impressions or ≥ site P75 |
| Dead click | click with no visible effect | same; ≥ 2 % or ≥ P75 |
| Error click | click followed by a JS error | Clarity, console |
| Quick back | enters and goes back within seconds | Clarity; or bounce + time < 10 s from search |
| Form abandonment | starts and does not submit | per-field events or replay |
| Leak | exit rate ≥ P75 on a page that is not the end of the funnel | page analytics |
| No next step | high 90 % scroll + high exit | they read everything and leave: the logical link is missing |
| Shallow read | high views + 90 % scroll ≤ P25 | the title promises something the content does not deliver |
| Loops / u-turns | A→B→A navigation repeated | replay, paths |
| Internal search with no results | on-site query returning nothing | search logs |

For each signal record: page, element, signal, traffic affected (impressions or sessions), segment where it is worst. Do not interpret yet; the cause is established in phase 4.

### Phase 3 — Amplify what attracts

Deliverable: the **amplification plan** per strong element, with three levers.

For each element or page in the *high consumption + high interaction* quadrant (and for those in *high consumption + low interaction*, which is attention already won), walk through the three guideline sets and record only the actions that apply:

- **SEO** (`references/seo-guidelines.md`): search intent, striking-distance queries, CTR by position, topic cluster and internal linking, on-page, structured data, technical/CWV, E-E-A-T, freshness, citability for AI search.
- **UX** (`references/ux-guidelines.md`): visibility and hierarchy, CTA clarity, cognitive load, feedback and states, B=MAP, trust, perceived performance, accessibility, mobile, continuity after consumption.
- **Innovation in useful elements** (`references/innovation-guidelines.md`): job to be done, usefulness ladder (static → interactive → tool → service), Kano, real-usefulness criteria, tool as magnet, programmatic pages, prototype with a kill criterion.

Golden rule: **amplifying is not changing what people like**; it is making it more visible, easier to continue from and more useful. If a lever means altering the strong element itself, mark it as an experiment, never as a direct change.

### Phase 4 — Repair what fails

Deliverable: the **pain-point analysis** with a decision per element.

Apply `references/pain-points.md` to each row of the friction table:

1. **User's pain**: what they were trying to do (infer it from the entry query, the element clicked or the recording).
2. **Observed pain**: the signal and its magnitude.
3. **Root cause**: walk the diagnostic tree in the reference (symptom → causes ordered by frequency → how to confirm). Record the confidence level: *confirmed* (replay, console, test), *probable* (known pattern + segment), *hypothesis*.
4. **Cost**: traffic affected × failure rate, and which funnel stage it blocks.
5. **Decision**: fix (technical or copy cause, cheap), redesign (structural cause), remove (the element serves no function in the funnel; fewer elements = less cognitive load) or leave (low cost, outside the funnel).

### Phase 5 — Monetization after acquisition

Deliverable: the **monetization strategy per product** that closes the funnel.

Follow `references/monetization.md`. The essentials:

- Monetization goes **after the moment of value** (the "aha") and at the point of maximum intent, never before the value and never on the element that attracts. If an article or a free tool is what brings traffic, it stays free; the next step is what gets monetized.
- Pick the model by type of strong element and audience using the reference's table (content → lead magnet/services/affiliate; tool → freemium/pay-per-use/API; data → subscription/alerts; community → membership; services → discovery call).
- Define the **activation event** and *time-to-value*; ask for payment once the user has reached it.
- Price is a hypothesis with a test, not a fixed number. Full transparency, cancellation as easy as sign-up, double opt-in for email.
- Minimum unit economics: CAC, LTV, margin, payback; if LTV/CAC < 3 the model needs revision before scaling acquisition.

### Phase 6 — Funnel synthesis per product

Deliverable: **one funnel per product** in the table from `references/report-template.md`.

Stages: Discovery → Consumption → Interaction → Capture → Activation → Conversion → Retention/Expansion. For each stage: page or element serving it, metric, current value, target, lever (from phases 3-5), experiment and priority. If a stage has no page or element serving it, write **gap** in bold: gaps are the most valuable finding in the report.

Close with the **prioritized backlog** (ICE from the template) and the **experiment cards** for the top three actions.

## Rigor rules

- **Minimum sample**: do not judge a CTR with fewer than 100 impressions, a friction rate with fewer than 30 sessions, or a page with fewer than 2 full weeks of data (ideally 4, with at least one complete weekly cycle). On small sites, group (by page type, by template) before discarding.
- **A/B tests only with enough traffic**: detecting a 20 % relative lift on a 3 % baseline conversion needs roughly 13-14k sessions per variant (α 0.05, power 0.8). Below that, propose sequential changes with before/after comparison by segment over equivalent windows, and say so.
- **Filter bots and internal traffic** before computing anything; server logs are the best place to see them.
- **Consent bias**: with cookie banners, client-side analytics only sees people who accept; flag it when interpreting absolute volumes and prefer ratios.
- **Seasonality**: compare with the same period a year earlier when it exists, not with the immediately preceding one.
- **Privacy**: any new tracking you propose complies with GDPR (legal basis, consent for non-essential cookies, IP anonymization, defined retention) and never records sensitive form data in replays.

## Prioritization (adapted ICE)

Score each action 1 to 5:

- **Impact** = traffic affected × expected lift × closeness to the funnel's close (an action at Conversion weighs more than one at Discovery for the same traffic).
- **Confidence** = quality of the evidence (5 cause confirmed by replay or test; 3 known pattern; 1 intuition).
- **Ease** (5 = an afternoon; 1 = a sprint or more).

ICE = I × C × E. Sort descending and mark the top three as the initial sprint.

## Output format

Always use the structure in `references/report-template.md`:

1. Executive summary (max. 6 lines: what works, what fails, main opportunity, next step)
2. Data and scope (sources, period, filters, limitations, assumptions)
3. What they consume and what they interact with (value map)
4. Weak elements and friction signals
5. Amplification plan (SEO / UX / innovation per strong element)
6. Repair plan (pain points with decision)
7. Monetization strategy per product
8. Funnel per product
9. Prioritized backlog + experiment cards
10. Open questions and missing data

Scale length to the site: a one-page landing does not need ten long sections, but it does need the ten sections. If the user asks for a single phase (e.g. "tell me what's weak"), deliver that phase with its table and offer the next ones; do not deliver the whole report unasked. If they ask for a file, deliver Markdown unless another format is requested. Write in the language the user writes in.

## When to read each reference

| File | Read it when |
|---|---|
| `references/data-sources.md` | you are about to request, export, normalize or interpret data; you are unsure what a signal means or whether the sample is enough |
| `references/seo-guidelines.md` | phase 3, SEO lever; Search Console data exists; the strong element is content |
| `references/ux-guidelines.md` | phase 3, UX lever; phase 4 when proposing the fix; any interface change |
| `references/innovation-guidelines.md` | phase 3, innovation lever; the user asks "what else could I offer" |
| `references/pain-points.md` | phase 4; there are rage/dead clicks, abandonment, leaks or quick backs |
| `references/monetization.md` | phase 5; any question about price, model or how to close the sale |
| `references/report-template.md` | when writing any deliverable, the per-product funnel, the backlog or an experiment card |

## What this skill does not do

- It does not invent data or "estimate" metrics that are missing; it proposes how to measure them.
- It does not recommend buying traffic as a substitute for fixing the funnel.
- It does not propose dark patterns or tracking without a legal basis.
- It does not change the element that attracts without wrapping it in an experiment with a rollback criterion.
- It does not hand out external benchmarks as targets; targets come from the site itself (current P75 as the goal for whatever sits at P25, +20 % relative for what already works).
