---
name: portfolio-positioning
description: Turns an existing website (a studio, a product, a blog) into a hiring surface for the site owner or author. Designs, page by page, how every indexed page shows the owner's full name, signals availability and leads to one conversion (email or a profile) without hurting the product's credibility or sounding needy. Covers a canonical identity read from project config, entity SEO (schema.org Person, sameAs), answers for recruiters who ask AI assistants, behavioral levers (costly signaling, halo, mere exposure, peak-end, B=MAP, Von Restorff) and copy templates. Use it ALWAYS when the talk is about turning a site into a portfolio, personal branding or positioning, "open to work", "put my name on every page", a /hire page, personal SEO, "make recruiters find me", or presenting products and ventures as proof of work, even if the words portfolio and marketing never come up.
---

# Portfolio positioning — from product site to hiring surface

> **Every indexed page is a job interview that happens without you.** The product this skill sells
> is a person: the site owner. The existing site isn't replaced: it becomes the proof. A product
> in production is the hardest signal there is to fake; no adjective on a résumé can compete with
> that.

This skill decides **what proof each page provides, how it's signed, how availability is framed,
and where the page converts**. It complements (it does not replace) `ux-psychology` (the UX
psychology skill in this repository; the added layer must respect its invariants) and the
optional skills listed under *Sister skills* below.

## How to use this skill

0. **Load the identity** (see *Configuration*). Nothing is written about a person until their
   identity is confirmed; with no config file, ask for it.
1. **Identify the working mode:**
   - **Design** the positioning of a site or a page → the full *Procedure*.
   - **Audit** a site that has already been worked on → *QA checklist* + a findings brief per page.
     An audit can start without the config (report what the site says and where it contradicts
     itself), but any copy you propose waits for a confirmed identity.
   - **Implement** one specific layer (copy, component, schema) → read the matching reference.
2. **Apply the invariants first.** They are boundary conditions: a broken invariant is a blocking
   finding, however beautiful the page is.
3. **Load the detail you need:**
   - `references/page-cases.md` — the C1–C8 taxonomy and how to treat each case. Read it
     **every time** you classify or design a page.
   - `references/behavior-and-copy.md` — behavioral levers applied to hiring, the copy templates
     and the anti-patterns. Read it whenever you write any text for the layer.
   - `references/identity-and-seo.md` — title/meta patterns, the JSON-LD template (Person/
     Organization/Article), entity SEO, answers for AI assistants and OpenGraph. Read it when you
     touch the technical layer.
4. **Deliver in brief format** (below): each page with its case, its positioning move, its copy
   and its verification. No vague recommendations.

**Precedence when things conflict:** this skill's invariants > `ux-psychology`'s invariants >
hiring conversion > product conversion > aesthetics. If signaling availability would mean
breaking the visitor's task, find another placement; don't break the task.

## Configuration — the owner's identity

The identity lives in `.harness/config/portfolio-positioning.json` (under `$HARNESS_DIR/config/`
when that variable is set). The project root is `$CLAUDE_PROJECT_DIR`, else
`git rev-parse --show-toplevel`, else the current directory; the harness is `$HARNESS_DIR`, else
`<root>/.harness`. The file is the **single source of truth** for everything this skill writes
about the owner: if the role, the availability or a link changes, edit the file and propagate the
change; never improvise per-page variants.

**No config file → ask, never guess.** Before designing any copy, ask the user in one message for
the required keys (and offer the optional ones), then offer to write the file. You may draft
values from the site's own public pages (its About page, an existing footer) and present them as
a draft to confirm. Never fill the identity from git metadata, the OS user, other conversations,
or the example below (Alex Rivera is fictional). If the user declines the file, keep the
confirmed identity for this session only and say that the next session will ask again. If
`.harness/` doesn't exist, create `.harness/config/` only with the user's consent, and say so.

**A config with gaps → ask only for what's missing.** A missing required key is asked for; a
missing optional key takes its default. A `$`-prefixed key (for example `"$comment"`) is
ignored; any other unknown key is reported, because it is almost always a typo.
`config.schema.json` in this skill is the file's JSON Schema (it describes a complete file, so
the four required keys are required there) and `config.example.json` is the example below.

| Key | Type | Required | Default when absent |
| --- | --- | --- | --- |
| `name` | string | yes | Ask. The full canonical name, exactly as it must appear (diacritics included). |
| `shortClaim` | string | yes | Ask. The role claim, under 10 words, always identical (e.g. "Senior Software Engineer — Data Platforms"). |
| `extendedClaim` | string | no | `shortClaim`. A longer line for the hub, the About page and the schema `description`. |
| `availability` | string | yes | Ask. The availability status stated as a fact, not a plea (e.g. "Open to senior roles & select contracts · Remote (US/EU)"). |
| `availabilityUpdated` | `YYYY-MM` or `YYYY-MM-DD` | yes | Ask. Rendered as "Availability last updated {Month YYYY}" (INV-08). Older than about three months → ask the user to reconfirm. |
| `anchorStack` | list of strings | no | `[]` → ask. The 4–8 technologies the owner wants to be hired for; also feeds `knowsAbout`. |
| `anchorProofs` | list of `{text, artifactUrl, context}` | no | `[]` → ask for 2–5. `text`: the claim with its number; `artifactUrl`: where it can be verified; `context`: the owner's role, scale and dates. A proof with no artifact is flagged (INV-03); a missing one is left as a labeled placeholder, never invented. |
| `sameAs` | list of URLs | no | `[]` → ask. External profiles, **primary first**: the first entry is the hub's second exit (INV-06). |
| `publicEmail` | string | no | Ask once. The address meant for public contact; never a private address found elsewhere. If the user declines, the hub's exits are the first two `sameAs` entries. |
| `hubPath` | path | no | `/hire` |
| `hiringLanguage` | language tag | no | `en`. The language of all hiring-facing copy (INV-07). |
| `siteUrl` | URL | no | Autodetected from the site's canonical tags, `og:url` or sitemap; ask if none is found. Used for JSON-LD `@id`s and absolute URLs. |
| `organizationName` | string | no | Autodetected from the site (Organization schema, logo alt text, title suffix). Without one (for example, a personal blog), the Organization node and `worksFor`/`founder` are omitted. |
| `imageUrl` | URL | no | None: `image` is omitted from the schema and the photo slots stay empty; recommend adding one for C4/C8. |
| `resumeUrl` | URL | no | None: the hub omits the résumé download and the brief says so. |
| `timezone` | string | no | None: the availability line is used as written. |
| `location` | string | no | None: factual prose omits where the owner is based. |
| `category` | string | no | Derived from `shortClaim` + the strongest proof, and confirmed with the user (behavioral lever 9). |
| `writingStructure` | string | no | None: long pieces use the content-writing skill's default or a plain structure. |
| `voice` | string | no | None: clean and direct; first person on personal pages. |

A complete example (a fictional person; every value is illustrative):

```json
{
  "$comment": "Identity for the portfolio-positioning skill. Fictional example.",
  "name": "Alex Rivera",
  "shortClaim": "Senior Software Engineer — Data Platforms",
  "extendedClaim": "Senior data platform engineer · Go & Python · streaming pipelines · Remote (UTC-5) · Open to contract (US/EU)",
  "availability": "Open to senior roles & select contracts · Remote (US/EU)",
  "availabilityUpdated": "2026-09",
  "anchorStack": ["Go", "Python", "Kafka", "PostgreSQL", "Kubernetes", "AWS"],
  "anchorProofs": [
    {
      "text": "Rebuilt a logistics platform's ingestion pipeline: p95 latency from 4 s to 300 ms",
      "artifactUrl": "https://example.com/work/ingestion-rewrite",
      "context": "Lead engineer, team of four, 2024-2025"
    },
    {
      "text": "Maintains an open-source schema-migration tool used by 300+ teams",
      "artifactUrl": "https://example.com/oss/migrate-kit",
      "context": "Sole maintainer since 2022"
    },
    {
      "text": "Designed, built and runs the two products on this site",
      "artifactUrl": "https://example.com/products",
      "context": "End to end, in production since 2023"
    }
  ],
  "sameAs": [
    "https://www.linkedin.com/in/alex-rivera-example",
    "https://github.com/alex-rivera-example",
    "https://example.social/@alexrivera"
  ],
  "publicEmail": "alex@example.com",
  "hubPath": "/hire",
  "hiringLanguage": "en",
  "siteUrl": "https://example.com",
  "organizationName": "Rivera Labs",
  "imageUrl": "https://example.com/assets/alex-rivera.jpg",
  "resumeUrl": "https://example.com/alex-rivera-resume.pdf",
  "timezone": "UTC-5 (US Eastern)",
  "location": "Austin, Texas",
  "category": "senior engineer who ships data platforms to production",
  "writingStructure": "Open long pieces with a short introduction and the author's motivation before the subject.",
  "voice": "Plain, first person, numbers over adjectives, no hype words."
}
```

**Placeholders.** Throughout this skill, camelCase placeholders are config keys (`{name}`,
`{shortClaim}`, `{availability}`, `{hubPath}`, `{publicEmail}`); `{proof1}`, `{proof2}` … are the
`anchorProofs` entries in order (their `text`, linked to their `artifactUrl`); `{primaryProfile}`
is the first `sameAs` entry. Title Case placeholders (`{Product}`, `{Headline}`) are facts of the
page being worked on. A template whose key is absent loses that fragment; it never gets a
made-up value.

## The governing tension: available, not desperate

The central risk of turning a studio's or product's website into a portfolio is that "the founder
is looking for a job" reads as "the products are dying." Three rules keep it in check:

1. **The site isn't a past being left behind: it's the proof the owner negotiates with.** Products
   and ventures are presented as living work ("built and maintained by"), never as relics.
2. **Availability is announced, not justified.** Never explain *why* the owner is available
   (giving reasons sends people looking for the flaw). "Open to senior roles & select contracts"
   is a status, like a store's opening hours.
3. **Frame it as choice, never as need.** Someone who picks projects is in demand; someone who
   begs isn't. The table of allowed and forbidden phrases is in `references/behavior-and-copy.md`.

## Invariants (INV) — never negotiable

- **INV-01 · One canonical identity.** `{name}` always in full and identical (diacritics
  included), the same `{shortClaim}`, the same links, across the whole site and every external
  profile. The entity (for search engines, for AI assistants and for the reader's memory) is built
  through exact repetition; every variant dilutes it.
- **INV-02 · A minimum triple layer on every indexed page.** (a) The full name visible (the footer
  counts), (b) an availability signal, (c) a conversion path ≤1 click from the hub. A page that
  can't carry all three gets deindexed or removed from the sitemap.
- **INV-03 · Proof before adjectives.** Every claim about the owner is anchored to a verifiable
  artifact: a product in production, a repo, a metric with context, an article. Anything without
  an artifact gets rewritten or removed. The reasoning: text is now cheap to generate, so an
  evaluator has every reason to discount a claim they can't check.
- **INV-04 · The layer doesn't break the visitor's task.** No modals, interstitials or attention
  hijacking for the hiring message (it inherits INV-03 from `ux-psychology`). The evaluator must
  be able to discover the layer; the product's user must be able to ignore it.
- **INV-05 · Machine-readable.** Valid `Person` JSON-LD with `sameAs` on every page, the site's
  `Organization` (if there is one) linked through `founder`, authorship marked up on articles.
  Recruiters hand part of their research to applicant tracking systems and AI assistants: if the
  graph doesn't say it, those tools can't pick it up.
- **INV-06 · A single conversion sink.** Every path converges on the hub (`{hubPath}`), and from
  there on two exits: `{publicEmail}` and `{primaryProfile}`. Never a private address. No forms
  with more than one step.
- **INV-07 · One hiring language.** Everything hiring-facing is in `{hiringLanguage}` (default
  English, for an international and remote market). Other languages only where an equivalent
  version in the hiring language exists alongside.
- **INV-08 · Visible freshness.** Availability carries a date ("Availability last updated
  {Month YYYY}" from `availabilityUpdated`, on the hub). An undated "open to work" smells like an
  abandoned site and costs credibility instead of adding it.

## Decision 0 — Level of intervention

Choose it (or confirm it with the owner) before designing anything. The skill works at all three
scales:

- **N1 · Identity layer (small scale).** The site stays intact: a signed global footer, bylines,
  the hub, schema and meta tags. For when the products are still selling and you don't want to
  touch their conversion. Effort: hours.
- **N2 · A builder's studio (hybrid, the default case).** N1 + a "Behind the build" section on
  each product, identity in the home page's subhead, and the About page turned into a personal
  page. The primary goal is now hiring, but the products keep operating and supplying proof.
- **N3 · Pivot to portfolio (large scale).** The site is reorganized around the owner: a home page
  with a personal value proposition, products converted into case studies (C5), person-centered
  navigation. For when the site is a showcase, not a business.

All eight invariants hold at all three levels; what changes is how much each page gets
reorganized, not whether it gets signed.

## Procedure

1. **Load and confirm the identity** (*Configuration*). Flag a stale `availabilityUpdated` and any
   proof without an artifact before going further.
2. **Inventory the indexed surface.** `sitemap.xml`, a `site:{domain}` search, Search Console if
   you have access. List every indexed or indexable page; note which ones receive paid traffic
   (that affects case C6).
3. **Classify every page into a case, C1–C8** (read `references/page-cases.md`). If a page fits
   two, the case with the more likely evaluating reader wins.
4. **Set the level (Decision 0) and the availability framing** according to the governing tension.
5. **Design each page's brief**: positioning move, layers to add, copy (read
   `references/behavior-and-copy.md`), placement according to peak-end.
6. **Design the technical layer** (read `references/identity-and-seo.md`): titles, meta tags,
   JSON-LD with a shared entity `@id`, OG, sitemap. An `llms.txt` file is optional (see that
   reference); never present it as a main lever.
7. **Create the hub** (`{hubPath}`, case C8) if it doesn't exist, and link it from the global
   footer of every page.
8. **Close the entity triangle**: every `sameAs` profile linking back to the hub; the site, the
   résumé and the profiles telling exactly the same facts.
9. **QA** with the checklist below; when implementing code, audit performance, accessibility and
   technical SEO (a slow site signed by a senior engineer is an anti-portfolio).
10. **Measurement.** Events on the hub's CTAs, UTMs on outbound profile links, a review after 2–4
    weeks: hub visits, outbound clicks, messages received and their quality.

## Delivery format — positioning brief per page

```
### {URL or page name}
- Case: C{n} — {type}          Level: N{1|2|3}
- Visitor's original task: {what they came to do}
- Likely evaluating reader: {technical recruiter / CTO / founder}
- Positioning move: {one sentence: what this page proves about the owner}
- Layers to add/change (in page order):
  1. {element} — {placement} — copy: "{proposed text in hiringLanguage}"
- Technical layer: title · meta · JSON-LD · OG
- CTA: {primary} → {destination}   ({secondary, if any})
- Risk for this case and mitigation: {…}
- Verification: {concrete checks}
```

## QA checklist

Per page: exact `{name}` visible · availability signal present · hub ≤1 click away · valid
`Person` JSON-LD (Rich Results Test / validator.schema.org) · title/meta following the case's
pattern · CTA after the value peak · a single distinctive availability element (Von Restorff: two
is noise) · no phrase from the forbidden list · email = `{publicEmail}` · copy in
`{hiringLanguage}` · every number traceable to an `anchorProofs` entry · the original task can
still be completed with no added friction.

Site-wide: the hub exists, shows the `availabilityUpdated` date and is linked from the global
footer · sitemap up to date · external profiles pointing back to the hub · the same facts on the
site, the résumé and the profiles · no Lighthouse regressions.

## Sister skills — when to invoke them

- `ux-psychology` (this repository): **always** when designing or placing any component of the
  layer (strips, author boxes, footers, hub).
- **A technical web-quality / SEO-audit skill**, if one is installed: every implementation in code
  (Core Web Vitals, technical SEO, accessibility). Otherwise run Lighthouse or PageSpeed Insights
  and the Rich Results Test yourself; if the project uses the market, the `web-vitals`,
  `seo-meta` and `structured-data` mods cover the same ground.
- **A headline / engagement-judging skill**, if one is installed: article and hub headlines, and
  deciding whether a piece gets a CTA at all. Otherwise: a concrete headline that names the
  outcome, and a CTA only at the close.
- **A content-writing skill**, if one is installed: long-form pieces (the narrative About page,
  articles, case studies); pass it `writingStructure` and `voice`. Otherwise apply them yourself.
- **A résumé skill**, if one is installed: keeping the résumé and the site telling the same story
  with the same numbers. Otherwise compare the facts against `resumeUrl` by hand.
