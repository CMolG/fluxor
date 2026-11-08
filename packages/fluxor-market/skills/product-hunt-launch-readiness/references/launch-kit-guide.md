# Writing the launch kit

How to draft each Product Hunt listing field so it passes the form's limits and
reads the way editors and the community expect. Draft only from facts you saw
in the repo, the site, or what the user told you. Never invent features,
numbers, customers or testimonials. Where a fact is missing, write a clearly
marked `[TODO: …]` and add it to the questions for the user. The same goes
for launch-day states that aren't true yet ("now open to everyone", "the
demo is live"): write them only if the user said that's the plan, and
otherwise mark them `[TODO: confirm …]`.

Put the fields in `launch-kit.json` (shape: `assets/launch-kit.template.json`),
then run:

```bash
python3 scripts/check_launch_kit.py <out>/launch-kit.json --markdown <out>/launch-kit.md
```

Fix every FAIL before calling the kit ready. The script counts characters the
way the form does, so trust it over your own count.

Contents: Name · Tagline · Description · Launch tags · Thumbnail · Gallery ·
Video & interactive demo · Makers · First comment · Shoutouts · Pricing ·
Promo · Sharing messages

---

## Name (≤ 40)
Use just the product name as it appears on the site. Put descriptors in the
tagline.
Good: `Tallyfox`. Bad: `Tallyfox — The Smartest Invoice Tracker`.

## Tagline (≤ 60)
This is the most important line on the listing. It should say what the
product does or how it helps, in plain words. Don't use hype, superlatives,
emoji, the product name (it already sits right above) or buzzword stacks.

Patterns that work:
- *[Category] for [audience]*: "Email for developers" (Resend), "Usage metering for engineers" (OpenMeter)
- *Open-source alternative to [known product]*: "Open-source alternative to Stripe Billing and Chargebee" (Lago)
- *[Outcome] without [pain]*: "Write SQL without knowing SQL" (Supabase)
- *Never [chore] again*: "Never build permissions again" (Permit.io)
- *[Verb] [object], [qualifier]*: "Build AI agents with a modern TypeScript stack" (Mastra)

Avoid superlatives and buzzwords. Product Hunt's own list of ways to not
get featured names an unclear tagline: "Don't say 'The best ever', say how
the product helps people". The same problem shows up as "Revolutionize…",
"The ultimate…" or "AI-powered platform for everything" (these are our
examples, not Product Hunt quotes).

Offer 2–3 options, all validated by the script, and recommend one.

## Description (≤ 500; first ~260 visible)
1. What it is and who it's for, in one sentence.
2. What's new or different compared with the alternatives.
3. Two or three standout features, concretely.
4. Optionally, the way in: free plan, open source, self-host, platforms.

Only about the first 260 characters show before truncation, so sentences 1
and 2 must land inside them.

## Launch tags (up to 3)
Choose the most specific existing topics. Specific topics beat broad ones for
discovery. Common topics include Developer Tools, Artificial Intelligence,
Productivity, Open Source, SaaS, Design Tools, Marketing, Analytics, Fintech,
Task Management, No-Code, Chrome Extensions, iPhone, Android, Mac, Web App,
API, GitHub, Education, Health & Fitness, Writing, Sales, Customer Success.
Exact names change, so tell the user to pick the closest match in the form.

## Thumbnail (square, 240×240)
Use the logo mark rather than the wordmark, with high contrast, legible at
about 48 px. A subtle animated GIF plays on hover. The source must be at least
240×240 or a vector. `capture_screenshots.cjs --thumbnail logo.svg` renders
one at exactly 240×240. Look at it on both a light and a dark background,
since Product Hunt has a dark theme. Transparent marks can vanish, and
opaque fragments (a white centre, a white box) show up as artifacts.

## Gallery (≥ 2 required, 3–6 ideal, 1270×760, first image = social preview)
Suggested storyboard:
1. **Hook**: product UI plus a one-line value proposition. This is the
   preview people see when the launch link is shared, so make it readable at
   thumbnail size.
2. **The "aha" moment**: the core workflow, with a short caption.
3. **Feature 2**, then **Feature 3** or integrations.
4. **Proof**: testimonials, logos, metrics or a comparison. Use only real ones.
5. **Way in**: free plan, promo, open source, platforms.

Use real UI, large text and a consistent frame and background. Don't use stock
photos or text walls. Design at 1270×760 and keep the key content inside the
central ~1200×630 area so any crop survives. Capture or crop at that size
rather than resizing a screenshot of another aspect ratio, because squashed
UI reads as careless. Correct dimensions don't prove an image isn't
distorted, so look at every image. `capture_screenshots.cjs` saves
`gallery-1270x760.png` straight from the live site as a starting point.

## Video & interactive demo
A 30–90 second YouTube or Loom demo showing the product doing its job, or an
interactive demo (Arcade, Storylane, Hexus, Supademo, Layerpath, ScreenSpace;
free for Product Hunt launches). This matters most for dev tools, AI agents
and workflows that stills can't explain.

## Makers
Tag everyone who built it. Each maker needs a complete profile (photo,
headline, links), because the first comment's author profile is on display.

## First comment (first ~800 characters visible)
Posted by a maker right at launch. Make it personal, specific and short:

```
Hi Product Hunt! I'm <name>, <role> at <product>.

<The problem, in one or two lines — ideally something you lived through.>

<Why existing options didn't work / why you built this.>

What <product> does:
• <concrete capability 1>
• <concrete capability 2>
• <concrete capability 3>

<What's new in this launch, or what makes it different.>
<Offer for the Product Hunt community, if any: code + what it gets you.>

We'd love your feedback: <one specific question, e.g. "which integration should we build next?">
```

Don't ask for upvotes, paste marketing copy, or write a wall of text.

## Shoutouts (up to 3)
Name the tools you genuinely used to build the product (e.g. Supabase,
Vercel, Stripe), with a sentence on how each helped. Your launch then appears
on their product pages.

## Pricing
| Reality | Form option |
|---|---|
| Everything is free (including open source with no paid tier) | Free |
| Paid only, no free plan or trial | Paid |
| Free plan, freemium, or a free trial (card or not) | Paid (with a free trial or plan) |

Cross-check with the pricing page. A mismatch is a finding.

## Promo
Fill in all three fields (offer, code, expiration), e.g. "3 months of Pro
free" / `PRODUCTHUNT` / 30 days after launch. Test the code in checkout
before launch day.

## Sharing messages (`social_posts`, `outreach_messages`, `community_messages`, `email_announcement`)
Ask people to look, try, comment, share feedback or pass it on. Never ask
them to upvote, and never offer anything in exchange for a vote.

- **Social:** "We just launched <product> on Product Hunt: <tagline>. It's
  <free/open source/…>. I'd love to hear what you think: <link>"
- **Personal message** (only to people who'd genuinely care): "Hey <name>, we
  launched <product> today. It <does X>, and I thought of you because
  <reason>. If you have a minute, honest feedback in the comments would mean a
  lot: <link>"
- **Email to users:** what's new, the Product Hunt offer, and an invitation
  to ask questions or request features in the comments.
- **Communities you belong to:** follow each community's self-promotion
  rules; lead with the problem solved, not the launch.

Sharing the direct launch link is fine. Write it as `<launch link>` rather
than guessing a URL: the real one only exists once the post is scheduled,
and slugs often get a suffix.
