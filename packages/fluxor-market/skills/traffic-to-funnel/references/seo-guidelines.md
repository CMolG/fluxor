# SEO guidelines for amplifying what already attracts

Principle: SEO amplifies demand that exists. An element is amplified through SEO when (a) it already receives searches or (b) it answers a question people type into search engines or AI assistants. If neither holds, the lever is UX or innovation, not SEO.

Walk through the ten rules for each strong element. Record only the actions that apply; most elements activate three or four.

## S1. Search intent

Classify the dominant intent of the queries bringing traffic to the page: **informational** (wants to know), **commercial** (compares), **transactional** (wants to do/buy), **navigational** (looks for a brand). The page must answer that intent in the first viewport: an informational article that opens with a sales pitch loses the quick-back battle; a product page that opens with theory does too.

Check: does the first paragraph or first block resolve the main query? Does the format (guide, comparison, tool, list) match what the search engine shows in the top 5 for that query?

## S2. Striking-distance queries

With Search Console, sort the page's queries by impressions and separate:

- **Position 1-3 with low CTR for its position** → a title/description/rich-result problem (see S4). The cheapest improvement there is.
- **Position 4-20 with high impressions** (*striking distance*) → strengthen the page for that query: a dedicated section, a heading with the query, internal links using that anchor, data or examples the top 3 lack.
- **Queries the page receives without addressing them** → either add the section, or create a linked satellite page (S3).

Indicative organic CTR by position (only to spot anomalies): 1st ≈ 25-30 %, 2nd ≈ 15 %, 3rd ≈ 10 %, 4th-5th ≈ 6-8 %, 6th-10th ≈ 2-5 %, 11th-20th < 2 %. A CTR below half the indicative value is anomalous.

## S3. Topic cluster and internal linking

A strong element becomes a **hub**: a pillar page covering the topic in breadth, with satellites covering subtopics in depth and linking back. Rules:

- Descriptive anchors ("heat pump running-cost calculator"), never "here" or "read more".
- Each satellite links to the pillar and to at least two sibling satellites; the pillar links to all of them.
- Strong pages distribute authority: link from them to the funnel pages (product, pricing, tool) with an anchor that keeps the context ("to estimate the cost for your case, use the calculator").
- No **cannibalization**: two URLs must not compete for the same query. If Search Console alternates the URL it shows for a query, merge (301 to the better one) or differentiate the intent.

## S4. On-page

- `<title>` ≤ 60 characters, main query at the start, benefit or differentiator after. It is the biggest driver of CTR.
- Meta description of 120-155 characters that promises what the page delivers and contains the query (it gets bolded in the result).
- A single `<h1>`, which may differ from the title.
- `<h2>` written as the real sub-questions (People also ask, search suggestions).
- Short URL, containing the query, without dates or parameters.
- Images with descriptive `alt`, meaningful filenames, modern format (AVIF/WebP) and declared dimensions.
- The first paragraph answers in 2-3 sentences; the development comes after.

## S5. Structured data

Schema.org in JSON-LD, validated with the rich results test. By element type: `Article`/`BlogPosting` (with `author`, `datePublished`, `dateModified`), `SoftwareApplication` or `WebApplication` for tools, `Product` with `offers` for product pages, `Organization` and `Person` for E-E-A-T, `BreadcrumbList` on every inner page. `FAQPage` only produces a rich result on recognized government or health sites and `HowTo` no longer produces one; use them for semantics, not expecting stars. Never mark up content that is not visible on the page.

## S6. Technical and Core Web Vitals

Without this nothing else counts:

- Indexable: no accidental `noindex`, self-referencing `canonical`, in the sitemap, not blocked by `robots.txt`, main content not dependent on consent to render.
- Core Web Vitals in the field (CrUX): LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 at the 75th percentile. Measure on mobile.
- Mobile first: content that only exists on desktop does not exist for the index.
- Server response (TTFB) < 800 ms; caching and compression on; images with `loading="lazy"` except the LCP one.
- No redirect chains or broken internal links.

## S7. E-E-A-T (experience, expertise, authority, trust)

- Visible authorship with name, role and profile link; real "about" and contact pages.
- First-hand experience made explicit: what was done, with which data, what went wrong. It is what separates the content from a generic rewrite.
- Sources cited and linked; figures with dates.
- A real `dateModified`: updating the date without changing content is detectable and counterproductive.

## S8. Freshness, decay and consolidation

Compare Search Console with the same period a year earlier. A strong page losing clicks with stable impressions is **decay**: update data, examples, screenshots, versions; add what the current top 3 has and it lacks; change the year in the title only if the content justifies it. Old content receiving nothing and providing no links: merge into the strong page with a 301, or remove (410).

## S9. Distribution and links

A strong element deserves distribution beyond the search engine: snippets for LinkedIn/X (if a content-judging skill is installed, run the snippets through it; otherwise lead each one with the element's single most useful finding), newsletter, niche communities. **Inbound links** go mostly to free tools, original data and comparisons; if the strong element is content, a tool version of it (see `innovation-guidelines.md`) is usually the most effective way to earn them.

## S10. Citability for AI search

AI-generated overviews and assistants cite pages that:

- Answer the question in the first paragraph, in complete, self-contained sentences.
- Use question-shaped headings and tables for comparable data.
- Define terms concisely and with a source.
- Have clear authorship and dates (S7) and do not block the AI crawlers the user wants to allow (an explicit decision in `robots.txt`).

An `llms.txt` file is optional and not a standard adopted by search engines; do not present it as a main lever.

## Forbidden

Keyword stuffing, mass-generated pages without proprietary data, cloaking, paid links, doorway pages, marking up invisible content, changing dates without changing content. Beyond being penalizable, they degrade the element that works.

## Output of the SEO lever

Per strong element (illustrative row):

| Rule | Concrete action | Metric | Current | Target | Timeframe |
|---|---|---|---|---|---|
| S2 | Strengthen "heat pump vs gas boiler" (pos 6.4; 12k impressions): comparison section with a table, H2 with the query, 3 internal links | position / clicks | 6.4 / 180 | ≤ 3 / 900 | 6-8 weeks |

Valid SEO metrics are impressions, CTR, position and organic clicks per query and per URL; "ranking" without a query is not a metric.
