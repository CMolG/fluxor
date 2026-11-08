# Proof and compliance

Proof is what turns a promise into perceived value, and the same rules that make proof believable
keep it legal. This file covers the claims register, how to find and present proof, what the law
says (US, EU, UK) and how to respond when someone asks for something deceptive. It is practical
guidance, not legal advice. For regulated categories (health, finance, earnings, children, alcohol)
or large campaigns, tell the user to get a legal review.

Status as of September 2026. Laws move; if you can reach the sources, spot-check anything you
quote to a client.

## Contents

1. The claims register
2. Kinds of proof, strongest first
3. Testimonials and reviews
4. Numbers and results
5. Urgency and scarcity
6. Prices, discounts and subscriptions
7. Comparisons and competitors
8. Special claim types
9. The legal map
10. When the user asks for something deceptive

## 1. The claims register

Every claim that could be true or false goes in the claims register in the value brief:

| Field | Why |
|---|---|
| Claim, as worded on the page | Wording changes meaning ("up to", "trusted by") |
| Evidence (fact ID, source, date) | What substantiates it *before* it's published |
| Scope | Who/what/when it applies to (e.g. "318 restaurants active for 3+ months, Jan–Jun 2026") |
| Typical? | Is this what a normal customer gets, or a best case? |
| Permission | For quotes, names, logos, photos: did the person or company agree? |
| Status | ok · needs proof · soften · cut |

`copy_lint.py --facts value-brief.md` catches numbers with no source. The register catches the
rest: names, quotes, logos, superlatives, and claims that are accurate but misleading.

**Accurate but misleading is still misleading.** "Trusted by 50,000 teams", where 50,000 is every
account ever created and 3,800 are active, is a count that doesn't mean what readers will take it to
mean. Say what the number is: "3,800 restaurant teams schedule with Rotawise every week". A precise, smaller
number usually reads as more credible than a round, inflated one (precise numbers can signal
competence: Xie & Kronrod 2012, [PR]).

## 2. Kinds of proof, strongest first

1. **Demonstration**: the product visibly doing the job (live demo, screenshot of the real
   result, video, free tool, sample). Hopkins's "samples" principle: let them experience it.
2. **Specific, attributed results**: "Median time to payment fell from 31 to 11 days across 412
   customers (Jan–Jun 2026)". Scope and source on the page.
3. **Named testimonials matched to the reader**: full name, role, company or city, photo if
   allowed, a specific before/after or number. Similarity to the reader drives the effect (NN/g).
4. **Ratings with counts from a third party**: "4.7/5 from 186 reviews on G2", linked.
5. **Customer logos and case studies**: with permission; a logo means a real, current customer.
6. **Third-party credentials**: certifications (state the exact one, e.g. "SOC 2 Type I", not
   "SOC 2 certified" if Type II isn't done), awards, press. Only real ones, named precisely.
7. **Mechanism**: explaining *why* it works makes the result more believable (Schwartz). It
   counts as proof only if the explanation is true and checkable.
8. **Risk reversal**: a guarantee is proof of the seller's confidence ("costly signal", Sutherland).
9. **Transparency**: showing the price, the team, the address and the limitations. Unusual
   honesty ("Not for agencies over 10 people") is itself persuasive.

Evidence on reviews (Spiegel Research Center, Northwestern 2017, [LS], observational, PowerReviews data):

- A product with 5 reviews had about 270% higher purchase likelihood than one with none.
- Displaying reviews lifted conversion more for higher-priced products (+380%) than lower-priced ones (+190%).
- Purchase likelihood peaked at average ratings of **4.0–4.7** and *fell* as ratings approached 5.0,
  because perfect scores look curated.
- Verified-buyer badges helped.

The takeaway: show real ratings with counts; don't hide criticism; a 4.7 with visible negatives
beats a suspicious 5.0.

Baymard ([LS]): 95% of users relied on reviews, and 53% actively sought out negative ones. Make
negative reviews easy to find and reply to them.

## 3. Testimonials and reviews

**Use only real ones, with permission.** Quote them verbatim. You may trim for length, but not
change the meaning or combine two people into one. Identify people as accurately as they allow
(full name, role, company/city). If they only allow initials, use initials. Never invent a name,
title, photo or company.

**Make them specific.** The best testimonials have a before, an action, an outcome with a number
or timeframe, and a feeling. When the user's testimonials are vague ("Great product!"), don't
rewrite them into specific ones. Suggest asking customers:

- "What were you doing before?"
- "What changed, and roughly by how much or how fast?"
- "What almost stopped you from buying?"
- "Would you mind if we used your name and role?"

**Place them where they work:** next to the claim or objection they support, not all in one wall.

**Disclose material connections:** paid, free product, discount, affiliate, employee, family,
investor. Say it clearly, next to the testimonial (FTC Endorsement Guides).

**Results must be typical, or the typical result must be disclosed.** Under the FTC Endorsement
Guides (2023 revision), advertisers must have substantiation that endorsed results are what
customers generally achieve. A "results not typical" footnote alone isn't enough. For courses and
income claims this is enforced strictly.

**Placeholders, not inventions.** When proof is missing, write a labelled slot the user can fill:
`[TESTIMONIAL NEEDED: restaurant manager, about hours saved on scheduling]`. List
every placeholder in the reply.

**AI-generated people are fake people.** No AI-generated faces, names or "customer" quotes.
Illustrations of *your product* are fine, if labelled where they could be mistaken for real results.

**Reviews:**

- Show the overall rating honestly.
- Don't cherry-pick in a way that misrepresents overall sentiment.
- Don't gate who can leave reviews, and don't pay for positive ones.
- In the EU, say whether and how reviews are verified.

## 4. Numbers and results

- **Source every number.** Numbers must come from a fact with a source and date. Round down, not
  up, and keep the precision honest ("about 3×" only if it's about 3×).
- **Define what's counted:** customers vs sign-ups vs users vs downloads; median vs average;
  which period.
- **Don't reinterpret a statistic.** Restate it as measured ("median days from due date to paid,
  412 customers"). Don't turn it into claims it doesn't support ("half of customers did better",
  "you'll get paid 20 days sooner").
- **"Up to" claims** need the typical result too ("up to 70% faster; median 45%"), because readers
  treat "up to" as the expected result.
- **Before/after results** need a comparable before. Say what changed.
- **Savings claims** need the math shown and realistic assumptions ("vs 3 manager hours a week at
  $25/hour"). An anchor must be a real alternative the buyer would consider.
- **Time claims** ("set up in 2 minutes") should be true for a typical new user, not a demo expert.
- **Render ratings exactly.** 4.8 is four full stars and a mostly-filled fifth, not five full stars.
  Never give an individual review a star rating (or `aria-label="5 stars"`) you weren't given.
- **Keep conditions attached every time.** If shipping is free only on the mainland, every
  "free shipping" says so, including in the sticky bar and the final CTA. The same goes for "no
  card" (trial only?), "cancel anytime" (how?), and "from $X".
- **Keep qualifiers accurate.** "Most of our students are designers" doesn't become "2,000+
  designers". "Mostly", "typically" and "median" carry meaning; don't drop them for rhythm.

## 5. Urgency and scarcity

Real urgency is persuasive and legitimate. Fake urgency is a dark pattern and, in the EU/UK
explicitly, an unfair commercial practice.

**Legitimate, when true, with the reason stated:**

- A dated deadline: a launch price until a date, a cohort that starts on a date, enrolment closing.
- Real capacity limits: "We onboard 20 studios a month because setup is done by hand."
- Real stock: a limited batch or seasonal harvest, with the true quantity.
- Price increases announced in advance, with a date.
- Bonuses that genuinely expire, with a date.

**Not legitimate:**

- Countdown timers that reset per visitor or per session.
- "Only 3 left" or "12 people viewing" that isn't real.
- A deadline that quietly rolls forward.
- "Last chance" on a permanent offer.
- Fake "sold out" states.
- Confirmshaming ("No thanks, I like losing money").

The EU UCPD blacklist bans falsely stating that a product will be available only for a very limited
time to elicit an immediate decision. The FTC's 2022 dark patterns report lists false low-stock,
false high-demand and baseless countdown timers.

**When there's no real urgency, don't manufacture it.** Lower the cost of acting now instead: a
free trial, a guarantee, "start free, upgrade later", a low-commitment first step. Risk reversal
often does the work people want urgency to do.

## 6. Prices, discounts and subscriptions

- **Show the total price.**
  - US: fees are judged case by case under FTC Act Section 5. The FTC's fees rule (16 CFR 464,
    in effect since May 12, 2025) covers only live-event tickets and short-term lodging. State laws
    such as California's SB 478 (in effect since July 1, 2024) require all-in prices more broadly.
  - UK: drip pricing is a banned practice under the DMCC Act 2024.
  - Put shipping and mandatory fees where the price is (Baymard: extra costs are the #1 reason for
    checkout abandonment).
- **"Was" prices must be real.** EU Price Indication Directive Art. 6a: the reference price for a
  reduction must be the lowest price charged in the prior 30 days. Anywhere: no invented "value"
  or "regular" prices.
- **Value stacks** (listing what's included) are fine when every item is real. Assigning each item a
  dollar value is risky. Use only prices someone actually pays for that item separately, or
  describe the value in outcomes instead.
- **Subscriptions:**
  - State the price, billing frequency, renewal, trial end and how to cancel, near the CTA.
  - Get express consent to recurring charges.
  - Make cancelling as easy as signing up.
  - US: ROSCA and state auto-renewal laws apply. The FTC's 2024 "click-to-cancel" amendments were
    vacated by the 8th Circuit in July 2025, and the FTC has moved to restart the rulemaking, so
    check its status.
  - EU/UK have their own subscription rules; the UK DMCC subscription regime is being phased in.
- **Honest anchors:** anchor against a real alternative (a manager's hours, a physio visit, an
  agency quote, the cost of the problem), with the math visible. Tversky & Kahneman's anchoring ([PR]) is
  robust; the dishonest version of it is illegal.
- **Decoys:** a third option that makes another look better (Huber, Payne & Puto 1982, [PR]) is
  fine only if every option is a genuine choice someone might sensibly buy. The effect is fragile
  with realistic stimuli (Frederick, Lee & Baskin 2014, [PR]). Ariely's *Economist* example is a
  classroom demo, not a field study. Don't promise lift from it.
- **Hidden fees "work" and are banned for a reason.** In a StubHub field experiment, hiding fees until
  checkout raised revenue (Blake et al. 2021, [PR]). Regulators call this drip pricing. Never
  recommend it.

## 7. Comparisons and competitors

- Compare on **verifiable, material, representative** facts (price, features, limits), with a date
  ("as of Sept 2026"). This follows the EU comparative advertising directive 2006/114/EC. The US
  permits truthful comparative advertising.
- No disparaging claims you can't prove ("X is a scam", "X's support is terrible").
- Don't use a competitor's logo or trademark in a way that implies endorsement.
- "Alternatives" framing ("Instead of spreadsheets and awkward follow-up emails") is often better
  than naming a competitor, and needs no proof beyond honesty.

## 8. Special claim types

- **Health, medical, supplements:** need competent and reliable scientific evidence. No disease
  claims without regulatory approval. Get a legal review.
- **Earnings and "make money" claims** (courses, business opportunities): substantiation and
  typicality are strictly enforced. Say what typical students earn, or make no earnings claim.
  Prefer skill and outcome claims ("build and sell your first client site") to income promises.
- **Environmental claims (EU):** from **27 September 2026**, Directive 2024/825 bans generic
  claims ("eco-friendly", "green", "sustainable") without recognised excellent environmental
  performance, and bans product-level "carbon neutral" claims based on offsets. Be specific and
  provable ("packaging is 100% recycled cardboard") or say nothing.
- **"AI" claims:** the FTC has acted against exaggerated AI claims. Describe what the AI actually
  does ("drafts reminder emails in your tone"), not "AI-powered" fog. It's also better copy: "Powered
  by AI" isn't a value proposition (NN/g 2025).
- **Security and compliance:** name the exact certification and scope (SOC 2 Type I vs Type II,
  ISO 27001, GDPR-compliant hosting in the EU). "Bank-level security" is vague. Say what you do.
- **"Free"**: truly free, or the conditions stated right next to it.

## 9. The legal map

| Jurisdiction | Instrument | What it means for a landing page |
|---|---|---|
| US | FTC Act §5 (deception/unfairness) | Claims must be truthful, not misleading, substantiated before publication. |
| US | Endorsement Guides, 16 CFR 255 (revised June 2023) | Real endorsers and honest opinions; disclose material connections; typical results; advertiser liability. |
| US | Rule on Consumer Reviews and Testimonials, 16 CFR 465 (effective Oct 21, 2024) | Bans fake reviews/testimonials (including AI-generated and non-existent people), buying sentiment-conditioned reviews, undisclosed insider reviews, fake "independent" review sites, review suppression, and buying or selling fake social-media indicators (followers, views). Civil penalties per violation (about $53k after inflation adjustment). An inflated customer or student count on your own page isn't a "fake indicator" under this rule. It's ordinary deception under §5; cite that instead. |
| US | Rule on Unfair or Deceptive Fees, 16 CFR 464 (May 12, 2025) | All-in pricing for live-event tickets and short-term lodging; other sectors are handled under §5 and state law. |
| US | ROSCA; state auto-renewal laws; California SB 478 | Subscription disclosures, consent and cancellation; all-in pricing in California. |
| US | FTC staff report "Bringing Dark Patterns to Light" (Sept 2022) | Enforcement priorities: fake urgency/scarcity, hidden fees, hard-to-cancel, disguised ads. |
| EU | Unfair Commercial Practices Directive + Omnibus Directive 2019/2161 | Blacklist: false limited-time claims, fake reviews, undisclosed paid rankings. Must disclose whether and how reviews are verified. |
| EU | Price Indication Directive Art. 6a | "Was" price = lowest price in the prior 30 days. |
| EU | Comparative Advertising Directive 2006/114/EC | Comparisons must be objective, verifiable and not misleading or denigrating. |
| EU | Digital Services Act Art. 25 | Online platforms may not use deceptive or manipulative interface design. |
| EU | Directive 2024/825 (from Sept 27, 2026) | Generic green claims and offset-based carbon-neutral claims banned. |
| EU | European Accessibility Act (e-commerce, from June 28, 2025) | Accessible e-commerce services. |
| EU | Digital Fairness Act (proposal expected ~late 2026) | Likely to target dark patterns, influencer marketing and personalisation. Check status. |
| UK | Digital Markets, Competition and Consumers Act 2024 (consumer enforcement from April 2025) | CMA can fine directly (up to 10% of global turnover). Fake reviews and drip pricing are banned practices. The subscription regime is being phased in. |

## 10. When the user asks for something deceptive

Users ask for fake timers, inflated numbers or "realistic" testimonials because they want the page
to sell, not because they want to break the law. Serve that goal:

1. **Do everything else in the request, and do it well.** Don't refuse the whole task.
2. **Decline the deceptive part in one or two sentences**, with the concrete reason: it's banned
   (name the rule that actually applies: fake testimonials → 16 CFR 465 and the Endorsement Guides;
   inflated numbers and fake timers → FTC Act §5 deception and the EU/UK blacklists), and it's the kind
   of thing that gets noticed and costs trust. No lecture.
3. **Give the honest version that captures the same value**, ready to paste:
   - Resetting timer → a real deadline (cohort date, launch price end date), or a stronger risk
     reversal instead.
   - "5,000+ members" when it's 870 → "870 members" (precise numbers read as credible), or a
     stronger proof type (a named result).
   - Invented testimonials → labelled placeholders plus the questions to ask real customers. Offer
     to turn their real answers into testimonial copy, with permission.
   - Fake "was" price → an honest anchor against the real alternative.
4. **Note it in the reply** under what you removed or declined, so the user sees the trade-off.

Example (short and useful):

> I left out the "only 2 spots left" banner and the "5,000+ members" figure. Fake scarcity and
> inflated counts are treated as deceptive practices (FTC, and explicitly blacklisted in the EU/UK),
> and customers who spot them stop trusting everything else on the page. Instead the offer uses
> your real number ("870 members train with us") and a real limit you can state: you coach 20
> new members a month, so June intake closes when those 20 places are taken. If you'd rather not
> cap intake, the 14-day refund does the same job with no risk.
