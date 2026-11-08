# UX guidelines for amplifying what already attracts (and for designing every fix)

Principle: amplifying through UX means reducing friction toward what people already like and making it more visible, more understandable and easier to continue from. It is not a redesign. Any change to the strong element itself is wrapped in an experiment with a rollback.

Walk through the ten rules for each element. Each one includes the check and the metric that verifies it.

## U1. Visibility and hierarchy

- What attracts must be seen effortlessly: in the first viewport on mobile, in the main navigation, or as the first action after the content. An element with high CTR but few impressions is underused: move it up.
- Hierarchy by size, contrast and position: one primary action per screen; secondary ones in secondary style. If everything stands out, nothing does.
- Fitts's law: touch targets of at least 44 × 44 px (WCAG 2.2 AA legal minimum: 24 × 24) with spacing between them. On mobile, the comfortable zone is the bottom third of the screen.
- Grouping by proximity: the CTA sits next to the content that motivates it, not in a separate block.

Metric: element impressions, CTR, time to first click.

## U2. Copy clarity

- CTA with verb + outcome ("Calculate my cost", "Download the template"), never "Submit", "Click here" or "Learn more".
- Headings that say what the user gets, not what the company does.
- Form labels always visible (not placeholder-only), and the reason a field is requested when it is not obvious ("phone: only if you prefer a call").
- Expectation microcopy next to the CTA: what happens next, how long it takes, whether it costs anything ("Free, no sign-up").

Metric: element CTR, completion rate, quick backs after the click.

## U3. Cognitive load

- One idea per block; paragraphs of 2-4 lines; lists when there are more than three parallel items.
- Progressive disclosure: advanced content unfolds on demand, it is not shown up front.
- Forms with only the fields needed for the current step; the rest is requested after delivering value. Every extra field lowers completion.
- Browser autofill (`autocomplete`), correct input types (`inputmode`, `type=email`), inline validation on blur, error messages that say how to fix it.
- Limited options: three plans, not seven; five related links, not twenty.

Metric: completion rate per step, abandonment per field, task time.

## U4. Feedback and states

- Everything that looks clickable is, and everything clickable looks like it (cursor, hover, button affordance). It is the main cause of dead clicks.
- Response to every action within < 100 ms (immediate visual feedback) even if the result takes longer: loading state, disabled button with text ("Calculating…"), skeleton.
- Success, error, empty and loading states designed. The error says what happened, what to do, and keeps what was typed.
- Never two clicks for what should be one; never a possible double submit.

Metric: rage clicks, dead clicks, error clicks, double-submit rate.

## U5. Behavior = Motivation × Ability × Prompt (Fogg)

For the visitor to take the next step, all three must coincide:

- **Motivation**: benefit visible before the click (sample result, real social proof, a concrete number).
- **Ability**: the step is small and cheap (one click, one field, no sign-up).
- **Prompt**: the CTA appears at the moment of highest intent, which is almost always *immediately after consuming the strong element*: at the end of the article, after showing the tool's result, after finishing the video. A CTA before the value is a prompt without motivation.

Metric: CTR of the CTA placed after the value vs. the one placed before.

## U6. Trust

- Visual and vocabulary consistency with the rest of the site and with what the search result or the ad promised.
- Verifiable social proof (names, companies, dated figures) or none; anonymous testimonials subtract.
- Price and terms visible before asking for data; no costs that appear at the end.
- Personal data: what is requested, what for, and a link to the policy, right next to the form.
- **Forbidden** (dark patterns; illegal for platforms under DSA art. 25 and contrary to EU consumer law): fake urgency or scarcity, confirmshaming ("No, I prefer to pay more"), pre-ticked boxes, drip pricing, cancellation harder than sign-up, obstacles to rejecting cookies, interfaces that hide the decline option.

Metric: form completion rate, early cancellation rate, complaints.

## U7. Perceived performance

- Fluid interaction: INP ≤ 200 ms; nothing blocks the main thread on click.
- Visible loading in phases: main content first, secondary after; no layout shifts (CLS ≤ 0.1) that make people click where they did not intend.
- Optimistic UI where safe (mark as sent while confirming).

Metric: INP, CLS, rage clicks on slow elements.

## U8. Accessibility (WCAG 2.2 AA) and cognitive accessibility

- Contrast 4.5:1 for text, 3:1 for components; visible focus; full keyboard navigation; labels associated with every field; never rely on color alone.
- Minimum target 24 × 24 px (criterion 2.5.8) and consistent help in the same place on every page (3.2.6).
- Plain language: short sentences, no unnecessary jargon, instructions before the action, the same word for the same thing.
- Motion and autoplay can be turned off; nothing flashes.

Metric: automated audit (Lighthouse/axe) with no critical errors + manual keyboard review.

## U9. Mobile

- Thumb zone: primary action reachable with one hand; sticky bottom CTA when the page is long and the CTA is the goal.
- No interactions that depend on hover.
- Tables that turn into cards or allow explicit horizontal scroll.
- Inputs with the right keyboard; no forced zoom (font-size ≥ 16 px in fields).
- Check on a real mid-range device, not just the emulator.

Metric: all of the above segmented mobile vs. desktop; a difference above 20 points is a mobile defect until proven otherwise.

## U10. Continuity after consumption

The rule that saves the most traffic. When the user finishes consuming the strong element (reaches the end of the article, gets the result, finishes the video), the page offers **one** logical, contextual next step:

- Informational content → the tool or resource that applies what was read, or the next article in the same cluster; never a generic "latest posts" list.
- Tool → save/share the result, a more complete version, or the person/service that solves the specific case.
- Product → the comparison, the trial or the FAQ that unblocks the decision.

If the strong page has high 90 % scroll and high exit (`no_next_step` in the script), this rule is the first fix.

Metric: exit rate of the strong page, CTR of the next step, pages per session from that entry.

## Output of the UX lever

Per element:

| Rule | Concrete change | Hypothesis | Metric | Current | Target | Change type |
|---|---|---|---|---|---|---|
| U10 | After the calculator result, a "Save and get the breakdown by email" block instead of the generic footer CTA | users who already have their number want to keep it; today there is nowhere to | CTR save-result | 1.5 % | ≥ 8 % | experiment (A/B or 2-week before/after) |

"Direct" changes (objective fixes: contrast, target size, label) versus "experiment" (anything that touches the strong element or the copy that already works).
