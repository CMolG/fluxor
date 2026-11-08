# Behavior and copy — why each piece works, and in what words

Three blocks: (A) behavioral levers specific to hiring positioning, (B) copy templates over the
config, (C) anti-patterns that switch off everything above. For the general psychology of
components (cognitive load, friction, placement), invoke `ux-psychology`.

---

## A · Behavioral levers

Each lever: mechanism → application → where it's used.

1. **Costly signaling (Spence).** A signal is credible in proportion to how much it costs to fake.
   A product in production, a repo with history, an app in the stores or a metric with context
   can't be faked; an adjective can. → Always put the artifact ahead of the description; explain
   2–3 hard decisions (a runtime chosen for startup time, a caching or queueing design, a data
   model) instead of listing ten technologies. → C2, C5, hub. Self-critique ("what I'd do
   differently") is a costly signal in its own right: it exposes judgment that a generated text
   can't fake cheaply.
2. **Aesthetic-usability halo.** The first work sample is the website itself: if it's fast, clear
   and bug-free, everything it claims inherits credibility; one broken detail contaminates the
   whole thing (an anti-portfolio). → Audit performance and accessibility on every
   implementation. → The whole site.
3. **Mere exposure.** Familiarity is processed as trust. The exact name, repeated on every page,
   means that by the third time `{name}` already sounds like someone the reader knows. That's why
   INV-01/INV-02 demand identical repetition, not creative variants. → Footer, bylines.
4. **Social proof and authority.** Numbers with context and a role, straight from
   `anchorProofs`: "{proof text} — {context}". Rule: number + context + the owner's role in a
   single sentence; a number without context is noise. → C4, hub, author boxes.
5. **Peak-end.** People remember the peak and the end. The hiring CTA goes right after each page's
   value peak and at the close; never before the page has given anything. → Every case.
6. **B=MAP (Fogg).** Behavior = Motivation × Ability × Prompt. The *motivation* comes from the
   proof; the *ability* has to be maximal (mailto + `{primaryProfile}` one click away, no forms,
   no "book a 30-minute call" as the only route); the *prompt* is the CTA placed at the peak. If
   the hub doesn't convert, work out which of the three is missing before rewriting anything.
7. **Von Restorff.** What's distinctive gets remembered; what's repeated becomes invisible. **One**
   visually distinct availability element per page. Two is noise; three is spam.
8. **Choice framing.** The same fact, two readings:

   | Never | Always |
   |---|---|
   | "I'm looking for a job" | "Open to senior roles & select contracts" |
   | "Currently unemployed / between jobs" | "Currently taking on new work" |
   | "Please check my profile" | "See how I work → {hubPath}" |
   | "I left my previous job because…" | (availability is never justified) |
   | "Limited spots! / Act now!" | "Availability last updated {Month YYYY}" |
   | "Hire me!" (as the H1 on product pages) | Signature + "Work with the engineer behind this" |

9. **Category positioning (Dunford, applied to a person).** Each page's claim answers "why this
   person and not the next résumé in the pile?". Competitive alternative: another generic
   engineer at the same level, or an agency. Unique attribute: the strongest `anchorProofs` entry
   (what the owner has done, at what scale) + end-to-end product work shown on the site. Chosen
   category: `{category}` — not a generic title like "full-stack developer" but the specific
   thing the owner ships (illustrative: "senior engineer who ships data platforms to
   production").
10. **Fluency and transmissibility.** The recruiter has to be able to describe the owner to their
    hiring manager in one sentence: hand them that sentence in writing. `{shortClaim}` (under 10
    words), always the same, easy to repeat. What can't be repeated from memory doesn't get
    passed on.

## B · Copy templates

Adapt them, don't clone them; every `{key}` comes from the config (see *Placeholders* in
SKILL.md). The templates are written in English; when `hiringLanguage` is another language, write
them natively in that language instead of translating word for word. Microcopy is clean and
direct; for long pieces (About, articles), apply `writingStructure` and `voice` from the config,
through a content-writing skill if one is installed.

A missing proof is never filled in: leave a labeled slot such as
`[PROOF NEEDED: a metric with context for the hub hero]` and list it in the brief.

- **Identity strip (C1/C2, N2):**
  "Designed, engineered & shipped end-to-end by **{name}** — {shortClaim}. {availability} →
  Work with me"
- **Global footer (every page):**
  "Built by **{name}** · {shortClaim} · {availability} · [{primaryProfile label}] [other
  `sameAs` labels] [Email]"
- **Byline (C3):**
  "By **{name}** — {shortClaim}."
- **Author box (C3, at the close):**
  "**{name}** {one-line summary of what the owner builds, from `extendedClaim`} — {proof1}.
  {availability}. → Work with me · {primaryProfile label}"
- **Behind the build (C2, template):**
  "**Behind the build** — {Product} runs on {one-line stack}. {Decision 1 and why}.
  {Decision 2 and why}. {Metric with context, if there is one}. Engineered end-to-end by
  **{name}** → Work with the engineer behind this."
- **404 (C7):**
  "This page doesn't exist. My availability does. — **{name}**, {availability, shortened} →
  {hubPath}"
- **Hub hero (C8):**
  "{One sentence on what the owner designs, builds and ships}. {proof1}. **{availability}.**"
- **Availability line, variants by goal** (write the chosen one into `availability`):
  - Full-time role first: "Open to senior engineering roles ({timezone or remote regions}) — and
    select contracts."
  - Contracts first: "Taking on select contracts & fractional engagements — open to the right
    senior role."

Illustrative rendering with the fictional example from SKILL.md (Alex Rivera), footer: "Built by
**Alex Rivera** · Senior Software Engineer — Data Platforms · Open to senior roles & select
contracts · Remote (US/EU) · [LinkedIn] [GitHub] [Email]".

## C · Anti-patterns (they switch off the entire skill)

- **Manufactured urgency or scarcity.** A professional who's in demand doesn't run countdowns.
- **Justifying the availability.** "Since leaving my last job…" invites people to go looking for
  the flaw.
- **"Hire me" as the H1 on product pages.** It kills the product's credibility and the author's.
- **Hiring modals or interstitials.** They violate INV-04; desperation interrupts.
- **Keyword-stuffing the name.** The name appears where a human would expect it (byline,
  signature, footer, schema), not wedged into every H2.
- **Inconsistency across surfaces.** Different numbers or dates on the site, the résumé and the
  profiles: humans stop trusting them, and automated summaries may drop or misstate the
  conflicting data point.
- **Deleting or hiding the studio or products.** It destroys the proof; they get reframed, not
  buried.
- **Invented testimonials or metrics.** Everything has to be defensible in an interview (INV-03).
- **Undated availability.** A fossilized "open to work" signals a dead site (INV-08).
- **Multi-step contact forms.** Every extra field lowers the Ability in B=MAP; email and one
  profile are enough.
