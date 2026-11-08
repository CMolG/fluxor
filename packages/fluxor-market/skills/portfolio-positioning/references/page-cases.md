# Page cases (C1–C8) — designing the positioning case by case

Every indexed page is classified into one of these eight cases. The case determines what proof the
page provides, where the identity layer goes, which copy is used and which specific risk has to be
mitigated. If a page fits two cases, the one with the more likely evaluating reader wins. Levels
N1/N2/N3 come from Decision 0 in SKILL.md; `{key}` placeholders come from the config.

---

## C1 · Studio or product home page

- **Original task:** understand what the site (studio, company, product) is and what it does.
- **Evaluating reader:** a founder or CTO who arrived from a profile, an article or a product and
  is wondering "who's behind all this?". Answer before they ask.
- **Move:** the home page demonstrates *breadth*: one person able to run one or several products
  or verticals end to end.
- **Treatment by level:**
  - N1: an identity strip below the hero + a signed footer. The site's hero stays untouched.
  - N2: the hero's subhead names the builder — "Every product here was designed, engineered and
    shipped end-to-end by **{name}** — {availability, shortened}" — and a "The builder" section
    is added (photo, `{shortClaim}`, 3 anchor proofs, CTA to the hub).
  - N3: a personal hero ("I design, build and ship {what the owner builds} end-to-end") with the
    products as a grid of clickable proofs leading to their case studies.
- **CTA:** primary to the hub; secondary to the products.
- **Risk:** a home page that tries to sell two things with the same hierarchy sells neither. At
  each level, one proposition is primary and the other clearly secondary; never tied.
- **Behavioral signals:** costly signaling (a portfolio of real products), halo, mere exposure.

## C2 · Product / vertical page

- **Original task:** sell or explain the product.
- **Evaluating reader:** a CTO or engineer assessing real technical depth; they arrive from the
  home page, from the résumé or from a search for the product.
- **Move:** the product **is** the proof. Don't describe the owner: show what they built, and
  sign it.
- **Treatment:** add a **"Behind the build"** section after the product's value sections and
  before the final CTA (peak-end: the signature arrives after the peak of interest):
  - 2–3 architecture decisions and the reasoning behind them (illustrative: a runtime chosen for
    startup time and memory, a retrieval pipeline, queues for concurrency, a caching layer).
  - The stack in one line. A metric with context, if there is one.
  - Signature + CTA: "Engineered end-to-end by **{name}** → Work with the engineer behind this".
  - At N1 this section shrinks to the signature in the product's footer.
- **CTA:** the product's CTA stays primary; the hiring one is secondary and persistent (section +
  footer), visually subordinate.
- **Double risk:** (a) cannibalizing the product's conversion → a subordinate layer, never ahead of
  the value; (b) "if the founder is job hunting, is the product dying?" → continuity framing:
  "built **and maintained** by", never a farewell in the past tense.
- **Signals:** costly signaling (what's hard can't be faked), technical authority, peak-end.

## C3 · Article / blog

- **Original task:** deliver value and capture organic traffic.
- **Evaluating reader:** an engineer or hiring manager who arrived through search or a share; it's
  the most common way in for strangers.
- **Move:** full authorship. The article proves *thinking*; the layer turns it into signed,
  contactable thinking.
- **Treatment:**
  - Byline at the top: `{name}` + `{shortClaim}`, linking to the About page or the hub.
  - An opening that follows `writingStructure` when the config sets one (for example, a short
    introduction and the author's motivation before the subject, so the reader connects with the
    person, not just the content).
  - **Author box** at the end: photo, 2 anchor proofs, `{availability}`, CTA to the hub +
    `{primaryProfile}`. The CTA goes at the end, never interrupting the reading (reciprocity
    first: delivered value predisposes the reader to get in touch).
  - `Article` schema with `author` → the `Person` entity (see identity-and-seo.md).
  - Headline and hook through a headline/engagement-judging skill if one is installed; the
    writing through a content-writing skill if one is installed. Otherwise apply the same
    standards yourself: a concrete headline, a hook that delivers on it.
- **CTA:** author box → hub. No mid-article CTAs.
- **Risk:** a self-centered article that adds nothing → nobody shares it. The value comes first;
  the signature reaps the harvest.
- **Signals:** reciprocity, authority, curiosity gap in the headline, peak-end.

## C4 · About / Team

- **Original task:** say who is behind the site.
- **Evaluating reader:** everyone ends up here before writing. It's the strongest personal page
  and the default answer, for humans and for AI assistants, to "who is {name}".
- **Move:** from "about the studio/product" to the person's professional story.
- **Treatment:** a narrative structure, not a flat chronology:
  1. `{shortClaim}` + a real photo (`imageUrl`; processing fluency: face + name + role at a
     glance).
  2. Proofs anchored in a story: the `anchorProofs` entries, each with its context and a link to
     its artifact, plus the site's own products.
  3. How the owner works (end to end, `{timezone}` if set, production quality).
  4. `{availability}` + CTA to the hub + a downloadable résumé (`resumeUrl`; the same story and
     numbers, checked with a résumé skill if one is installed).
  - Also write it in plain, factual prose (subject-verb-fact sentences) so an AI assistant can
    quote it without making anything up.
- **Risk:** listing adjectives without artifacts (violates INV-03). One proof per paragraph.
- **Signals:** authority, social proof, fluency, consistency with the other surfaces.

## C5 · Technical case study

- **Original task:** (it often doesn't exist; it gets created at N2/N3 from products or projects).
- **Evaluating reader:** the technical person who decides on the interview.
- **Move:** show *process and judgment*, not just the result.
- **Treatment — a fixed structure:** context → problem → architecture decisions and the reasoning
  behind them → result, with numbers and context → stack → **"What I'd do differently"** →
  signature + CTA. The self-critique section is costly signaling: perfect case studies look made
  up; admitting a real trade-off is what makes them believable.
- **Risk:** breaching NDAs or inflating numbers → only metrics the owner could defend in an
  interview.
- **Signals:** costly signaling, authority, honesty as a differentiator.

## C6 · Acquisition landing page (ads / campaigns)

- **Original task:** convert the product's paid traffic. **The most delicate case.**
- **Treatment:** while it receives paid traffic, N1 only (a signed footer + schema, no new
  sections): every element unrelated to the offer lowers the ad's ROI and violates INV-04. If the
  campaign is switched off or the landing page no longer receives paid traffic, it gets
  reclassified as C2.
- **Verification:** decide with campaign data, not by gut feeling.

## C7 · Utility pages (404, legal, contact, changelog, docs)

- **Legal/privacy:** a signed footer + schema. Nothing more. They can be `noindex`, but they keep
  the layer for any human who lands on them.
- **Contact:** add the direct route to the owner, with `{publicEmail}` and `{primaryProfile}`,
  kept separate from the product's support channel.
- **404:** the one page where personal humor works and gets remembered (Von Restorff at the site
  level): *"This page doesn't exist. My availability does. — {name}, {availability, shortened} →
  {hubPath}"*.
- **Changelog/docs:** every entry signed ("shipped by {name}") — proof of living, ongoing work,
  and the antidote to "is the product dead?".

## C8 · Hiring hub (`{hubPath}`, default `/hire`) — always create it

- **Function:** the single conversion sink (INV-06). Every path on the site ends here, and from
  here there are only two ways out: `{publicEmail}` and `{primaryProfile}`.
- **Fixed structure:**
  1. Hero: claim + availability + time zone (see the hub hero template in
     behavior-and-copy.md).
  2. 3–5 hand-picked proofs: one per product or vertical + the strongest metric from
     `anchorProofs` + open source, if any. Each one linked to its artifact (C2/C5, repo, store
     listing).
  3. What working with the owner looks like: kinds of engagement (senior role, contract,
     fractional), process, `anchorStack`.
  4. A downloadable résumé (`resumeUrl`; the same story, the same numbers).
  5. Two exits: `mailto:{publicEmail}` + `{primaryProfile}`. **No form** (B=MAP: maximum
     ability = one click).
  6. "Availability last updated {Month YYYY}" from `availabilityUpdated` (INV-08).
- **Technical layer:** indexable, linked from the global footer of every page (internal
  authority), a complete `Person` schema, its own OG image with name + claim (links to this page
  travel through recruiters' chat and email: the preview is a micro-interview).
- **Risk:** turning it into a second, never-ending résumé. One phone screen per block; the depth
  lives in the linked C2/C5 pages.
