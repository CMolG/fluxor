# Innovation guidelines for useful elements

Principle: innovating on a strong element means turning passive consumption into active usefulness, giving the visitor a capability they did not have before. The test for every idea is a single question: **does it let them reach their goal faster, better or cheaper than before?** If the answer is not a concrete yes, it is decoration.

Walk through the nine rules for each strong element and produce proposal cards (format at the end). Expect one or two good cards per element, not ten.

## I1. Job to be done

State the job the visitor hires the strong element for: *When [situation], I want [motivation], so that [outcome]*. Infer it from entry queries, from the element they interact with next and from what they type into on-site search. An article about "the cost of X" usually has the job "when I have to budget, I want a defensible number, so I can decide/convince". That job, not the article, is what gets amplified.

## I2. Usefulness ladder

Every element sits on a rung; useful innovation climbs one, rarely two:

1. **Static content** (article, guide, product page)
2. **Interactive content** (checkable checklist, diagnostic quiz, comparator with filters, editable example)
3. **Tool** (calculator, generator, simulator, validator, converter, fill-and-download template)
4. **Continuous service** (monitor, alert, periodic report, API, connector/MCP, browser extension)
5. **Product** (the tool with an account, history, collaboration and support)

Questions to choose the rung: what does the user do *after* consuming the element (computes in a spreadsheet, copies it elsewhere, comes back to re-check)? That manual "after" is the next rung.

## I3. Kano model

Classify every proposal:

- **Basic**: its absence annoys, its presence does not excite (search, filter, copy, print). Implement it if missing; do not announce it.
- **Performance**: more is better (precision, speed, case coverage). Invest in the ones people already use.
- **Delighter**: unexpected and valuable (a result shareable by link, a comparison with the sector average, an export ready to present). Differentiation lives here; prioritize the cheap ones.

Delighters become basics over time; what differentiates today is demanded tomorrow.

## I4. Real-usefulness criteria

A proposal passes if it meets at least four:

1. **Solves an observed pain** in the data (queries, on-site searches, rage clicks, comments, support questions), not an imagined one.
2. **Reusable**: the user has a reason to come back (data that changes, new cases).
3. **Shareable**: the result has value when shown to someone else (social currency) or solves something for a third party.
4. **Generates proprietary data**: each use produces information the site did not have (compounding advantage and content material).
5. **Measurable**: use, return and conversion can be counted from day one.
6. **Controlled marginal cost**: if it uses AI or paid APIs, per-user and per-day limits exist by design.

## I5. The tool as a magnet

Proven pattern: a free tool aligned with the job of the strong content captures better than any form. Rules:

- Genuinely free and without sign-up for the first use; sign-up is requested to **save, receive, compare or repeat**, never to see the result.
- The result is concrete (a number, a document, a verdict), not "contact us to learn more".
- Linked from the strong content with context ("calculate it for your case") and with its own URL to rank (S3 in the SEO guidelines).
- Results with a shareable link are the largest source of inbound links a small site can manufacture.

## I6. Personalization and AI

Valid when the strong element admits per-user variants: next-content recommendation based on what was read, conversational answers over the content itself, a summary adapted to the profile, a draft generated from the result. Rules:

- Do not hide the strong content behind the AI; the AI is one more rung, not a wall.
- Transparency: what is generated and its limits are stated.
- Bounded cost per use (daily quota, cache of frequent answers, small model for simple cases).
- No personal data collected for personalization without a legal basis (GDPR).

## I7. Programmatic pages with proprietary data

When the strong element answers a question with many variants ("cost of X in [region]", "[tool A] vs [tool B]", "[product] for [sector]"), generate one page per variant **only if** each contributes distinct, real data (figures, comparisons, tool results). A template with the name swapped is thin content and penalizes the strong element. Start with the 10-20 highest-demand variants, measure indexing and clicks, scale afterwards.

## I8. Telling innovation from smoke

Before proposing, the proposal must answer yes to all three:

1. Has someone asked for or searched for it, with evidence (query, message, behavior)?
2. Would they use it a second time?
3. Would someone pay for it, or bring someone else to use it?

Technical novelty (a chatbot, a 3D map, an animation) without the three is smoke even if it looks great in the demo. If the `research-radar` skill is available, apply it here to contrast with the state of the art.

## I9. Cheap prototypes with a kill criterion

- Minimum version in a week or less, even without design, behind a URL and linked from the strong element.
- Usage metric from day one: uses, uses per user, 7-day return rate, conversion to the next step.
- **Kill criterion** written before launch: "if in 4 weeks it does not exceed N uses or X % return, it is removed". Removing is cheap; keeping zombies costs attention and cognitive load.
- Only what passes the criterion receives design, SEO and monetization.

## Proposal card

One per idea that passes I4 and I8 (illustrative card for a home-energy site):

| Field | Content |
|---|---|
| Source strong element | /blog/heat-pump-guide (3.1k views, 240 s, 90 % scroll 62 %) |
| Job | when I consider replacing my boiler, I want to know how much a heat pump would change my yearly heating bill, so I can decide whether it pays off |
| Current → proposed rung | static content → tool |
| Proposal | estimator: enter home size, insulation level and current fuel and bill, and get a yearly cost and payback range with and without a heat pump, comparable and shareable by URL |
| Kano | performance (precision) + delighter (shareable comparison) |
| I4 criteria met | observed pain (query "heat pump running cost", 5k impressions), reusable, shareable, generates data, measurable |
| Effort | 3-5 days (MVP with a reference table, no live tariff data) |
| Metric and kill criterion | ≥ 150 uses and ≥ 15 % 7-day return within 4 weeks; otherwise removed |
| Next funnel step it feeds | Capture (save result by email) → Conversion (installer quote request) |
