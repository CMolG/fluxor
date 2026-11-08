# Report template, per-product funnel and cards

Always use this structure. Sections can be short; they cannot be missing. If the user asked for a single phase, deliver that section in full with its table and offer the rest.

## Report

```markdown
# Traffic to funnel — [site] — [period]

## 1. Executive summary
- What works: [element/page, evidence in one figure]
- What fails: [element/page, signal and cost]
- Main opportunity: [action, expected impact]
- Next step this week: [one action]
- Overall confidence of the diagnosis: high / medium / low, and why

## 2. Data and scope
Sources | Period | Filters applied (bots, internal) | Segments available | Limitations and biases (consent, sampling, SPA) | Explicit assumptions

## 3. What they consume and what they interact with (value map)
Page table: url · views · time · 90 % scroll · entrances (main source/query) · exit · conversion · consumption
Element table: url · element · type · impressions · clicks · CTR · conv. · classification
Quadrants: high consumption + high interaction / high consumption + low interaction / rest
Segment differences > 20 pp
One concluding sentence per strong page

## 4. Weak elements and friction signals
Table: page · element · signal · magnitude · traffic affected · worst segment

## 5. Amplification plan for what attracts
Per strong element: SEO table (rule · action · metric · current · target · timeframe), UX table (rule · change · hypothesis · metric · current · target · type), innovation cards

## 6. Repair plan for what fails (pain points)
Table: page · element · user's pain · signal · segment · root cause (confidence) · decision · fix · metric · ICE

## 7. Monetization strategy per product
One card per product (format in monetization.md §7)

## 8. Funnel per product
One table per product (format below)

## 9. Prioritized backlog and experiments
Ordered ICE table; experiment cards for the top 3 actions

## 10. Open questions and missing data
Which data point would confirm each hypothesis marked "probable" or "hypothesis"; which instrumentation to install and what it will provide
```

## Funnel per product

Fixed stages. If a stage has no page or element serving it, write **gap**: it is the most valuable finding.

| Stage | What it measures | Page / element serving it | Metric | Current | Target | Lever (phase) | Experiment | Priority |
|---|---|---|---|---|---|---|---|---|
| Discovery | how they arrive | landing page + source/query | entrances, organic impressions, SERP CTR | | | SEO (3) | | |
| Consumption | they receive the free value | strong page | 90 % scroll, time, quick backs | | | UX/SEO (3) | | |
| Interaction | they act on the value | strong element | element CTR, rage/dead | | | UX (3-4) | | |
| Capture | they leave a data point or a channel | form, save, newsletter, sign-up | capture rate, abandonment per field | | | UX/innovation (3-4) | | |
| Activation | they reach the moment of value | activation event | % activated, time-to-value | | | product (5) | | |
| Conversion | they pay or hire | offer, checkout, call | activated→paid, lead→customer | | | monetization (5) | | |
| Retention / expansion | they return, renew, expand, refer | continued use, upgrade, referrals | 30-day return, churn, NRR | | | product (5) | | |

Below each table:

- **Ratios between stages** (stage n+1 / stage n) and which one is the bottleneck (the lowest ratio relative to the site's own P75 or, without an internal comparison, relative to the indicative figures in `monetization.md`).
- **Whole-funnel target**: visitors → customers current and target, with the effect of closing the bottleneck computed (not guessed: multiply the ratios).
- **Dependencies**: which amplification lever feeds this funnel and which repair unblocks it.

Targets come from the site itself: whatever sits at P25 aims at the current P75; what already works aims at +20 % relative. A target copied from an external benchmark is marked "indicative".

## ICE backlog

| # | Action | Phase | Impact (1-5) | Confidence (1-5) | Ease (1-5, 5 = trivial) | ICE | Sprint |
|---|---|---|---|---|---|---|---|

Impact = traffic affected × expected lift × closeness to the close. Confidence = quality of the evidence (5 confirmed, 3 known pattern, 1 intuition). Ease 5 = an afternoon, 1 = a sprint or more. ICE = product. The top three form the initial sprint; "direct" fixes of trivial cost (contrast, target size, label) always go in even if their ICE is low.

## Experiment card

```markdown
### Experiment [n]: [short name]
- Origin: [phase, page, element, signal]
- Hypothesis: if [change], then [metric] will go from [current] to [target], because [root cause and evidence]
- Exact change: [what is touched; screenshot or description]
- Primary metric: [one] · Guardrail metrics: [what must not get worse: exit, rage, CWV, downstream conversion]
- Segment: [all / mobile / new]
- Design: 50-50 A/B · before/after (2 equivalent windows) · rollout with rollback
- Required sample and duration: [calculation or "A/B not reachable → 2+2 weeks before/after"]
- Success criterion: [metric ≥ target with the planned sample] · Rollback criterion: [guardrail metric worsens > X %]
- Owner and date
```

Sample rule: detecting a 20 % relative lift on a 3 % baseline conversion with α 0.05 and power 0.8 needs ≈ 13-14k sessions per variant; with a 10 % baseline, ≈ 3.5k. If the traffic is not there, say so and use before/after by segment over equivalent windows (same duration, same weekdays, no campaigns). Never stop a test on seeing "significance" before the planned sample.

## Innovation proposal card

Format in `innovation-guidelines.md`. Included in section 5 of the report only if it passes I4 and I8.

## Monetization card

Format in `monetization.md` §7. One per product in section 7.
