# Pain-point analysis: from symptom to decision

A pain point is a place where the user wanted to do something and the site prevented it or made it costly. The analysis always runs in this order: **what they wanted to do → what signal it leaves → the most likely cause → how to confirm it → what to do**. Skipping confirmation produces fixes that fix nothing.

## 1. How to read each symptom

For each row of the friction table (phase 2), fill in:

| Field | How to obtain it |
|---|---|
| User's pain (what they wanted) | entry query, element clicked before/after, recording, on-site search |
| Observed pain (the signal) | type, magnitude, traffic affected, segment where it is worst |
| Root cause | tree in section 2, with confidence level: *confirmed* / *probable* / *hypothesis* |
| Cost | traffic affected × failure rate, and the funnel stage it blocks |
| Decision | fix / redesign / remove / leave (section 3) |

Abbreviated five-whys rule: ask "why?" until the answer is something that can be changed on the site (an element, a copy, a load time, a structure). "Because users don't read" is not a root cause; "because the label is light grey on white at 2.1:1" is.

## 2. Diagnostic tree

Causes are ordered by observed frequency; check them in that order. "Confirm" is the cheapest test that turns a hypothesis into a confirmed cause.

### Rage click

1. **Slow response or no feedback** (the click worked but nothing showed it) → confirm: replay + page INP; the element takes > 300 ms to react. Fix: immediate feedback, loading state, optimize the handler.
2. **Looks clickable but isn't** (card, image, heading, decorative icon) → confirm: click heatmap on the element + inspection. Fix: make it clickable if it has a logical destination; otherwise remove the affordance (cursor, shadow, link color).
3. **Overlay or intercepting element** (cookie banner, chat widget, sticky header covering the button) → confirm: mobile replay; the click lands on the layer. Fix: z-index, overlay size, close after accepting.
4. **Small or crowded target** on mobile → confirm: segment rage by device; size < 44 px or spacing < 8 px. Fix: size and spacing.
5. **Disabled button with no explanation** (silent validation) → confirm: form replay. Fix: message saying what is missing, or enable and validate on submit.
6. **JS error** → confirm: error clicks / console in the affected browser. Fix: technical.

### Dead click

1. **Text or image that looks like a link** (underline, brand color, card with shadow) → fix: link it or remove the affordance.
2. **Accordion, tab or carousel that does not signal it can be opened/moved** → fix: state icon, animation, or flatten it into plain content if it holds little.
3. **Element that only responds on hover** (dropdown menu on mobile) → fix: touch behavior.
4. **Broken link or `href="#"`** → fix: technical.
5. **Image the user wants to enlarge** → fix: lightbox or larger image.

Confirm: click heatmap + inspection of the element's DOM. The fastest diagnosis of all.

### High exposure, low interaction (nobody clicks)

1. **Not seen**: low contrast, size, mistaken for a banner, below the fold on mobile though not on desktop → confirm: scroll and click heatmaps, segment by device.
2. **Not understood**: generic copy ("Submit", "Learn more"), does not say what you get → confirm: 5-second test (what do you think happens if you press it?).
3. **No reason**: the benefit is not in view, or the user has not received value yet (prompt before motivation, U5) → confirm: position relative to the strong content; CTR of the same CTA placed after the value.
4. **No trust**: asks for data without saying why, hidden price, no social proof → confirm: replay (they hesitate, hover and leave), exit survey.
5. **Wrong moment**: appears on entry (popup) or on a page with a different intent (a pitch inside an informational article) → confirm: compare CTR by source page and query intent.
6. **Already done**: returning visitors are already subscribed/registered → confirm: segment new vs. returning. Fix: hide it from those who converted and offer the next step.

### Form abandonment

1. **Sensitive field** (phone, company, budget) requested before giving value → confirm: per-field abandonment; the peak is on that field. Fix: remove it, make it optional or move it to a second step.
2. **Length**: more than 4-5 fields in the first step → fix: split into steps with progress and value between steps.
3. **Aggressive or confusing validation**: errors before finishing typing, messages without instructions, unexplained format (date, phone with prefix) → confirm: replay. Fix: validate on blur, messages with an example.
4. **No autofill / wrong mobile keyboard** → fix: `autocomplete`, `inputmode`, `type`.
5. **Losing what was typed** when submit fails or on returning → fix: keep state, error without reload.
6. **Distrust at the last step**: price, terms or card appear → fix: show them earlier (U6).
7. **Submit button does not respond or confirm** → see rage click.

### Leak (high exit on an intermediate page)

1. **Intent satisfied**: a purely informational article; exiting is normal → fix: U10 (contextual next step), not forced "retention".
2. **No next step**: they read everything (high 90 % scroll) and there is no logical link at the end → fix: U10.
3. **Did not find what they were looking for**: compare entry query with content; low time + high exit → fix: S1 (intent), restructure the first viewport, or create the page the query asks for.
4. **Technical dead end**: broken next link, broken pagination, menu that fails on mobile → confirm: replay and 404 logs.
5. **A price or condition that repels** (pricing page with high exit and no click): confirm with replay (they read prices and close) → fix: revisit offer/price/copy, add FAQ and comparison, capture email first ("notify me of discounts" is not a dark pattern if it is real).

### Quick back / pogo-sticking

1. **Title or description promise something the page does not deliver** → confirm: compare snippet with first viewport. Fix: S1/S4, or deliver the promise.
2. **Slowness**: LCP > 4 s on mobile → confirm: CrUX. Fix: S6.
3. **Interstitial on entry**: full-screen cookie banner, newsletter popup, registration wall → confirm: replay. Fix: discreet banner, popups only after interaction.
4. **Wrong page of the same site** (cannibalization): the search engine sends people to the less suitable URL → fix: S3.

### Shallow read (high views, low scroll)

1. **The first viewport does not hook** (long intro, no answer) → fix: answer first (S4), move theory down.
2. **Wall of text** → fix: U3 (chunking, lists, tables, images with a function).
3. **Content does not match the query** → fix: S1.
4. **What they wanted was at the top** (a figure, a download link): not a problem; confirm with the click on that element.

### Loops, u-turns and on-site search with no results

1. **Ambiguous navigation labels** ("Solutions", "Resources") → confirm: replay; a 10-minute card sort. Fix: concrete labels.
2. **The destination page lacks what the label promised** → fix: align them.
3. **On-site searches with no results** → a list of missing content or of synonyms the search does not understand. Fix: create the content or add synonyms/redirects; one of the cheapest sources of ideas there is.

## 3. Decision per element

| Decision | When | Typical cost |
|---|---|---|
| **Fix** | technical, copy, contrast, size or position cause; the element has a clear function in the funnel | hours |
| **Redesign** | structural cause: the element exists at the wrong moment or in the wrong format (long form, CTA before the value, accordion hiding what matters) | days; needs an experiment |
| **Remove** | the element serves no funnel stage and no user task; its only function was "being there". Removing it lowers cognitive load and raises the CTR of what remains | minutes; measure afterwards |
| **Leave** | low cost (little traffic, outside the funnel) and better things to do; note it for review in three months | zero |

A weak element next to a strong one usually calls for removal or merging: the attention it steals is worth more than what it contributes.

## 4. Mandatory segmentation before deciding

Every pain point is examined at least by:

- **Device**: most rage and dead clicks are mobile; a desktop fix does not touch them.
- **New / returning**: "they don't click" may mean "they already did".
- **Source / entry query**: the same page fails for one intent and works for another.
- **Browser / OS**: error clicks usually concentrate on one.

If a segment holds > 60 % of the pain, the fix is designed for that segment and measured there.

## 5. Output

Pain-point table ordered by cost (traffic affected × failure rate), with columns: page · element · user's pain · signal and magnitude · segment · root cause (confidence) · decision · concrete fix · verification metric · ICE. The top three rows generate experiment cards (see `report-template.md`).
