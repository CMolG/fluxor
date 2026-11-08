# Value perception rubric

How to score a landing page (or your own draft) on how well it makes the product *feel worth its
price* to the visitor it actually gets. Use it for audits and as the self-check before delivering
new copy.

The score is a structured judgment, not a conversion-rate prediction. Its job is to make the review
consistent and to point at the lever that is weakest. The weights are a heuristic: proof carries the
most because an unbelieved promise adds no value (Hopkins, Ogilvy and Schwartz all make this point,
and Hormozi's "perceived likelihood" is a multiplier in his value equation). Say this in the report
if someone treats the number as a forecast.

## Contents

1. Scoring procedure
2. The eight levers, with anchors
3. Caps (issues that limit the total)
4. Bands
5. The 5-second test
6. Section checklist

## 1. Scoring procedure

1. Decide who the traffic is (source, awareness level) before scoring. A page can be right for
   product-aware visitors from a newsletter and wrong for cold ad traffic.
2. Score each lever 0–5 against the anchors below. Integers only. Write one line of evidence per
   lever: a quote, a screenshot observation, or a script result. No evidence, no score above 2.
3. Put the scores in a JSON file and run `scripts/value_score.py scores.json`. It applies the
   weights and caps and prints the total and band. Don't compute it by eye.
4. Name **the one thing**: the lowest-scoring lever with the highest weight that you can fix with
   facts you actually have.

## 2. The eight levers

| Lever | Weight | Question |
|---|---|---|
| `clarity` | 15 | In one screen, does a stranger get what it is, who it's for and what to do next? Does it match the ad, search or link that brought them? |
| `outcome` | 15 | Is the result the buyer wants stated concretely and vividly, in their words? |
| `proof` | 20 | Does the page make that result believable for someone like me? |
| `differentiation` | 10 | Is it clear why this instead of the real alternative (including doing nothing)? |
| `time` | 10 | Is it clear how soon the first win arrives? |
| `effort` | 10 | Is it clear how little the buyer must do, learn, switch or give up? |
| `risk` | 10 | Is the cost of being wrong removed or shrunk (trial, guarantee, cancel terms, security)? |
| `price_frame` | 10 | Does the price feel small next to the value and the real alternative, and is it visible and honest? |

### clarity (15)

- **0**: You can't tell what the product is from the first screen. Jargon or slogan only.
- **1**: Category is guessable, but not the audience or outcome. The CTA is generic or missing above the fold.
- **2**: What it is is clear; who it's for or why it matters is not. Message mismatch with the traffic source.
- **3**: What, who and next step are clear on desktop. Mobile hides or crops part of it, or the hero is crowded.
- **4**: Clear on both viewports; one clear primary CTA; headline and sub-headline do different jobs.
- **5**: As 4, plus the first screen echoes the visitor's own search or ad wording, and every later section heading still makes sense if read alone (scanners get the story from headings).

### outcome (15)

- **0**: Only features or company talk ("we", "our platform").
- **1**: Benefits exist but are abstract ("save time", "grow faster").
- **2**: One concrete outcome, buried below the fold or phrased in company language.
- **3**: A concrete outcome leads the hero; features are tied to benefits in most places.
- **4**: The outcome is specific (numbers, time, a scene the reader can picture) and phrased in customer language.
- **5**: As 4, plus the page makes the *before* state painful and the *after* state vivid, with the product as the bridge.

### proof (20)

- **0**: No proof, or proof that looks fake (anonymous "Happy customer", stock headshots, unverifiable big numbers).
- **1**: Generic praise, logos without context, or a single unsourced stat.
- **2**: Some real proof (named testimonial, rating) but far from the claims it should support, or not specific.
- **3**: Named, specific testimonials or data support the main claim, placed near it.
- **4**: Proof of several kinds (named results, rating with count, demo/screenshot of the real product, third-party certification) next to each major claim and objection.
- **5**: As 4, plus the proof matches the reader's situation (same role/size/problem), states typical results honestly, and the product itself is shown working.

### differentiation (10)

- **0**: Could be any competitor's page with the name swapped.
- **1**: Claims to be better with no specifics ("the best", "smarter").
- **2**: One real difference is mentioned but not tied to why it matters.
- **3**: The real alternative is named or implied and one unique attribute is linked to a benefit.
- **4**: Two or more unique attributes → value → proof, framed against what the buyer does today.
- **5**: As 4, plus the page owns a clear position ("the X for Y who Z") that competitors cannot credibly copy.

### time (10)

- **0**: No idea how long before anything good happens.
- **1**: Vague ("quick setup").
- **2**: Setup time or first result mentioned once, without support.
- **3**: A concrete time to first value ("first rota published in 10 minutes", "arrives in 3 days") is stated.
- **4**: Time to first value is stated and shown (steps, timeline, demo), and time to full outcome is honest.
- **5**: As 4, plus the CTA itself promises an immediate first win.

### effort (10)

- **0**: The page implies work, migration, calls or long forms with no reassurance.
- **1**: Effort is not addressed.
- **2**: "Easy" asserted without showing.
- **3**: How it works in 3–4 steps, or "no X needed" stated for the main effort worries.
- **4**: As 3, plus switching costs (import, integrations, learning curve) are addressed and the sign-up path is short.
- **5**: As 4, plus the page shows the buyer what they'll *stop* doing, and the first step asks for almost nothing.

### risk (10)

- **0**: Hidden terms, surprise card requirement, or a demo-request wall with no alternative.
- **1**: Risk not addressed.
- **2**: A trial or refund exists but is hard to find or its terms are unclear.
- **3**: Trial/refund/cancel terms are stated near the CTA.
- **4**: As 3, plus the top anxieties (security, lock-in, quality, time wasted) are answered with proof.
- **5**: As 4, plus a clear, specific guarantee or free tier that makes trying feel safer than not trying.

### price_frame (10)

- **0**: Misleading price presentation (hidden fees, fake "was" prices, drip pricing), or no price where buyers expect one and no reason given.
- **1**: Price present but bare, with no link to value.
- **2**: Price near value statements, but no comparison or unit framing.
- **3**: Price is anchored against a real, relevant alternative or broken into an honest unit (per month, per use, per person).
- **4**: As 3, plus plan differences are expressed as outcomes, the recommended plan is obvious, and the "total" is clear.
- **5**: As 4, plus the price appears only after the value is established (on long pages) and the math the page implies holds up.

If the page legitimately has no price (enterprise sales, a lead magnet), score `price_frame` on how
well it frames the cost of the next step (time, data asked) and say so.

## 3. Caps

Some problems cap the total however good the rest is, because they destroy trust or break the law.
`value_score.py` applies these when you list them under `"caps"`:

| Cap id | Issue | Max total |
|---|---|---|
| `fabricated_proof` | Invented or unverifiable testimonials, reviews, logos, user counts or results | 40 |
| `fake_urgency` | Countdown that resets, "only N left" that isn't true, fake "was" price | 40 |
| `broken_path` | Primary CTA broken, 404, or checkout/sign-up fails | 30 |
| `hidden_costs` | Mandatory fees revealed only at checkout; unclear auto-renewal | 50 |
| `no_first_screen_cta` | No primary CTA in the first screen on mobile or desktop | 70 |

## 4. Bands

| Score | Band | Meaning |
|---|---|---|
| 85–100 | Compelling | The page makes the price feel small. Test refinements. |
| 70–84 | Convincing | Works for warm traffic; one or two levers leak value. |
| 50–69 | Unclear value | Visitors must work to see why it's worth it. Rewrite key sections. |
| 30–49 | Weak | Mostly features or claims. Rebuild the message from the value brief. |
| 0–29 | Broken | Visitors can't tell what it is, can't trust it, or can't act. |

## 5. The 5-second test

From the first screen alone (use `capture_page.cjs` screenshots and `fold.json`, both viewports),
a stranger should answer:

1. What is it?
2. Who is it for?
3. What do I get out of it?
4. Why should I believe that?
5. What do I do next, and what will it cost or risk me?

Mark each ✅ / ⚠️ / ❌ per viewport with the evidence. Questions 1, 2, 3 and 5 feed `clarity`; 4
feeds `proof`.

## 6. Section checklist

Each section must have a job: moving a lever or answering an objection. For each one, ask:

- What is its job? If it has none, cut it or merge it into another section.
- Does its heading carry the message on its own (scanners read headings only)?
- Is every claim in it specific and backed on the spot?
- Does it talk about the reader ("you") more than the company ("we")?
- Would a skeptical buyer object to anything here? Is that objection answered before the next CTA?
- Is there a next step within reach (a CTA roughly every screen or two on long pages)?
