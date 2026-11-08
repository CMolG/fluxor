# Identity and SEO — the indexable technical layer

Goal: every indexed page declares the owner's entity (`{name}`) in a form that search engines,
applicant tracking systems and the AI assistants recruiters use can all read. The data always
comes from `.harness/config/portfolio-positioning.json` (see *Configuration* in SKILL.md); the
placeholders below are its keys. When implementing, audit performance, accessibility and
technical SEO (with a technical web-quality skill if one is installed).

## 1 · `<title>` and meta description patterns by case

- **C2 (product):** `{Product} — {what it is} | Built by {name}`. The name goes at the end of the
  title and in the meta description; it doesn't steal the product's keyword.
- **C3 (article):** `{Headline} — {name}`.
- **C4 / C8 (About, hub):** `{name} — {shortClaim} · {availability, shortened}` (for example
  "Alex Rivera — Senior Software Engineer (Data Platforms) · Open to roles & contracts",
  illustrative). These are the pages whose search target IS the person: the name opens the title.
- **General rule:** visible name + meta + schema on all of them; the name in the title only where
  search intent justifies it (C3, C4, C8 and, optionally, C1). Write the C4/C8 meta description as
  a factual answer: it's the snippet search engines and AI assistants are most likely to quote.

## 2 · JSON-LD — an entity graph with a shared `@id`

A single `Person` node, referenced by `@id` from every page; that way the whole site points at the
same entity instead of creating duplicates.

**Person (on every page, adapting the page's `url`):**

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Person",
      "@id": "{siteUrl}/#person",
      "name": "{name}",
      "jobTitle": "{shortClaim}",
      "description": "{extendedClaim}. {proof1 text}. {availability}.",
      "url": "{siteUrl}{hubPath}",
      "image": "{imageUrl}",
      "email": "mailto:{publicEmail}",
      "knowsAbout": ["{anchorStack[0]}", "{anchorStack[1]}", "…"],
      "sameAs": ["{sameAs[0]}", "{sameAs[1]}", "…"],
      "worksFor": { "@id": "{siteUrl}/#org" }
    },
    {
      "@type": "Organization",
      "@id": "{siteUrl}/#org",
      "name": "{organizationName}",
      "url": "{siteUrl}/",
      "founder": { "@id": "{siteUrl}/#person" }
    }
  ]
}
```

Filling rules:

- **Omit a property whose key is absent** (`image` without `imageUrl`, `email` without
  `publicEmail`); never emit an empty string or a placeholder.
- **`description`** is one or two factual sentences a model could quote verbatim; it uses only
  facts from the config.
- **`knowsAbout`** takes the `anchorStack` entries as individual technology names (split an entry
  like "Go (gRPC, Kafka)" into separate items).
- **The Organization node** exists only when the site has an organization (`organizationName`) and
  the owner really founded or works for it; otherwise drop the node and `worksFor`. Use `founder`
  only when that is the true relationship.

**Article (add on C3):** `"author": { "@id": "{siteUrl}/#person" }`, plus `headline`,
`datePublished` and `dateModified`. **Product (C2, optional):** `SoftwareApplication` with
`creator` → the same `@id`. Validate everything in the Rich Results Test / validator.schema.org.

## 3 · The entity triangle (E-E-A-T)

Search engines and AI assistants consolidate an entity when several independent sources confirm
one another with identical data:

1. **Site → profiles:** `sameAs` + visible links in the footer and the hub.
2. **Profiles → site:** the website field on each `sameAs` profile pointing to the hub (or to the
   domain); the bio where there is no website field.
3. **The same facts everywhere:** the exact name, the same claim, the same numbers and dates on the
   site, the résumé and the profiles. A data point that conflicts across surfaces doesn't get
   averaged: it gets thrown out.

Authorship: a visible byline on every article, linking to the About page or the hub; the About
page acts as the author page.

## 4 · Answers for recruiters who ask AI assistants (AEO/GEO)

Some recruiters and hiring managers ask an AI assistant "who is {candidate}" before searching, or
instead of it. How common this is has not been measured here, so treat it as a cheap hedge that
the rest of the layer already pays for, not as a primary channel. Assistants tend to answer with
whatever is consistent, quotable and written in plain prose.

- **C4 and C8 in factual prose:** subject–verb–fact sentences built from the config ("{name} is a
  {shortClaim} based in {location}. {proof1 text}, {proof1 context}…"; drop the location clause
  if `location` is absent). Quotable paragraphs beat slogans.
- **`llms.txt` at the root (optional, low priority):** a proposal for a plain-markdown summary
  file aimed at language models. Adoption by crawlers and search engines is uncertain and it is
  not a standard; add it only if it is nearly free to maintain (who the owner is, what they have
  built, availability, canonical links), and never present it as a lever.
- **Visible dates** on articles and on the hub (INV-08): they let any reader, human or model,
  judge freshness.
- **Consistency > volume:** ten pages telling the same story build the entity; ten different
  versions dissolve it.

## 5 · OpenGraph / Twitter Cards — the preview is a micro-interview

Links to the site will travel through recruiters' chat tools, email and applicant tracking
systems; many evaluators will only ever see the card.

- `og:title` with the name on C3/C4/C8; `og:description` = `{availability}` + one anchor proof.
- **An `og:image` from a custom template** (`{name}` + `{shortClaim}` + the site's brand) at least
  for C8, C4 and articles. 1200×630, with text legible on mobile.
- `twitter:card = summary_large_image`.

## 6 · Indexing and technical hygiene

- The hub (`{hubPath}`) **indexable** and linked from the global footer of every page (internal
  authority, and it satisfies INV-02 in one click).
- A sitemap kept up to date with the hub and the case studies; correct canonicals; no accidental
  `noindex` on pages that carry the layer (legal pages can be `noindex` while keeping the
  human-facing footer).
- Check coverage with Search Console and `site:{domain}`; inspect that the JSON-LD shows up
  rendered (if the site is an SPA, the schema goes in the served HTML, not injected late).
- Performance: a site signed by a senior engineer gets audited — green Core Web Vitals are part of
  the positioning, not an extra.

## 7 · Measurement

- Events: mailto click, profile clicks, résumé download, hub visits and where they came from.
- UTMs on outbound profile links (`?utm_source={domain}&utm_medium=hire_hub`) for attribution in
  analytics; mailto doesn't take UTMs — measure the click instead.
- Review after 2–4 weeks: the hub's visit→contact ratio, the evaluators' entry pages (C3? C2?),
  and the quality of the messages received. Iterate on the brief for pages that bring traffic but
  don't convert (a B=MAP diagnosis).
