# Data sources: what to ask for, how to normalize, what each signal means

## 1. What to export from each tool

| Tool | Export | Where |
|---|---|---|
| **GA4** | Pages and screens report (views, users, average engagement time, key events); Traffic acquisition (source/medium per landing page); Funnel exploration if one exists | Reports → Engagement → Pages and screens → Share → Download CSV. Per-element events need a parameter (`element_id`/`link_text`) on the `click` event or custom events |
| **Plausible / Umami** | Top pages (visitors, pageviews, bounce, time), Entry/Exit pages, Sources, Goals/Events with their properties | Export CSV button on the dashboard; Umami via API `/api/websites/{id}/metrics?type=url` |
| **Matomo** | Behavior → Pages, Entry/Exit pages, Events, Transitions (paths), Heatmaps and Session Recordings if the plugin is active | Export on each report (CSV/JSON); API `Actions.getPageUrls` |
| **PostHog** | Trend insights on `$pageview` and `$autocapture` (element), Funnels, Session replay with rage clicks (`$rageclick`), toolbar Heatmaps | Insight → Export; events API |
| **Microsoft Clarity** | Dashboard: Rage clicks, Dead clicks, Quick backs, Excessive scrolling, JS errors per page; click/scroll/area heatmaps; recordings filtered by those signals | Filter by URL → export dashboard CSV; percentages are over sessions |
| **Hotjar** | Heatmaps (click/move/scroll), Recordings tagged *rage click* and *u-turn*, Funnels, Surveys | Export heatmap as click CSV; recordings are watched, not exported |
| **Google Search Console** (or Bing Webmaster Tools) | Performance → Search results: Queries and Pages with impressions, clicks, CTR, position; compare two periods to see decay | Export (CSV/Sheets); best per page with the Queries tab filtered by URL |
| **Server logs (nginx, Traefik, Apache, Caddy)** | Requests per path, 4xx/5xx status, user agents (bots), latencies | `goaccess` or an `awk` pass over the access log |
| **CrUX / PageSpeed Insights** | Real-world LCP, INP, CLS per URL (field) and lab data | pagespeed.web.dev or the CrUX API |
| **Business** | Leads (CRM), subscribers (newsletter), payments (Stripe/gateway), sign-ups and cancellations | Native exports |

Always ask for the **period** and whether the export is **filtered** (bots, internal traffic, country).

## 2. Normalized CSV schema

`scripts/analyze_traffic.py` accepts these three files. Only `url` is required; every additional column enables an analysis. It reads comma-, semicolon- or tab-separated files (whichever the header uses) and numbers as exports write them: `12,500` and `1,234,567.8` (comma thousands), `12.500` and `1.234.567,8` (dot thousands, comma decimals), plain `12.5` or `12,5`, spaces as group separators, and percentages with `%`. A single three-digit group (`12,500`, `12.500`) is read as thousands unless another cell in the same file shows that separator is the decimal one (`45.2`, `0,75`); a leading zero (`0,125`) always means a decimal. It recognizes common aliases from tool exports (`pageviews`, `visits`, `entries`, `time_on_page`, `key_events`, `goal_completions`, `keyword`, `element_id`) and Spanish headers (`vistas`, `sesiones`, `entradas`, `salidas`, `impresiones`, `clics`, `posicion`, `consulta`). <!-- lang:es: real accepted column-header aliases -->

### `pages.csv`

| column | meaning |
|---|---|
| `url` | page path or URL |
| `views` | page views |
| `sessions` | sessions with at least one view of the page |
| `entrances` | sessions that started on this page (landing) |
| `exits` | sessions that ended on this page |
| `avg_time_s` | average time on page or engagement time, in seconds |
| `scroll_50_pct`, `scroll_90_pct` | % of views reaching 50 % / 90 % of the page height |
| `conversions` | conversions (key events, goals) attributed to the page |
| `quick_backs` | sessions that entered and went back within seconds (Clarity) |
| `bounces` | single-page sessions that started here |

### `elements.csv`

| column | meaning |
|---|---|
| `url` | page where the element lives |
| `element` | id, selector, text or name of the element |
| `type` | `cta`, `nav`, `link`, `form`, `button`, `card`, `video`, `accordion`, `download`, `copy`, `search`… |
| `impressions` | times the element was visible (viewport). If not measured, use page views and note it |
| `clicks` | clicks or taps |
| `rage_clicks`, `dead_clicks`, `error_clicks` | count of each signal on the element |
| `conversions` | conversions attributed to the click (last touch or funnel) |

### `search.csv` (Search Console)

| column | meaning |
|---|---|
| `url` | page |
| `query` | search query |
| `impressions`, `clicks`, `ctr`, `position` | as exported by Search Console; `ctr` may be a percentage |

Run:

```bash
python scripts/analyze_traffic.py --pages pages.csv --elements elements.csv --search search.csv \
  --min-impressions 100 --json analysis.json --md analysis.md
```

It returns: a consumption ranking per page with signals (`leak`, `high_quick_back`, `shallow_read`, `no_next_step`, `insufficient_sample`); elements classified `strong`/`medium`/`weak` with signals (`high_exposure_low_interaction`, `rage_click`, `dead_click`, `error_click`, `attracts_but_no_conversion`); queries flagged `striking_distance`, `low_ctr_for_position`, `asset_to_defend` plus an `opportunity` score (impressions × lost CTR). The thresholds used are printed at the end so the report can cite them.

If the data comes as screenshots, transcribe it into this schema (even with 10 rows) before analyzing: it forces you to make explicit what is missing.

## 3. Signal definitions

- **Element impression**: the element entered the viewport (IntersectionObserver ≥ 50 % for ≥ 1 s is a reasonable definition). Without impressions there is no honest CTR: a CTA at the foot of a long page gets few clicks because few people see it, not because nobody likes it.
- **Element CTR** = clicks / impressions. Compare only elements with enough sample.
- **Rage click**: three or more clicks/taps in the same small area within roughly one second (Clarity, Hotjar and PostHog use similar definitions). It signals frustration: something does not respond, responds slowly or looks clickable without being so.
- **Dead click**: a click with no observable effect (no navigation, no DOM change, no network). It signals a broken expectation of interactivity.
- **Error click**: a click immediately followed by a JavaScript error. A technical failure, not a design one.
- **Quick back**: the user enters a page and returns to the previous one within seconds. From a search engine this is *pogo-sticking*: the page does not deliver what the result promised.
- **Excessive scrolling**: far more scrolling than the page height would predict; the user is looking for something they cannot find.
- **U-turn**: A → B → A within seconds; B was not what they expected.
- **Form abandonment**: interaction with at least one field without a submit. Measure per field (last field touched) to locate the blocker.
- **Leak**: high exit rate on a page that is not the end of a path. Exiting on a "thank you" page or a purely informational article is normal; on a pricing or product page it is a problem.
- **Average time**: skewed by open tabs and by how each tool measures it (GA4 only counts time with the tab in the foreground). Use it as a relative range between pages, not as an absolute figure.
- **Bounce**: in GA4 it is the inverse of the engagement rate (session < 10 s, no conversion, no second view); in Plausible/Umami it is a single-page session. They are not comparable across tools.

## 4. Data quality: checks before analyzing

1. **Bots and internal traffic filtered**. Bot signs in client-side analytics: traffic spikes from a single country or browser, 0 s time, impossible paths. Server logs confirm them by user agent and request pattern.
2. **Period**: at least two full weeks; better four. Check it does not include launches, outages, paid campaigns or a half-finished redesign (if it does, split the period).
3. **Consent**: with a banner and client-side analytics, only people who accept are measured (in the EU often a fraction). Absolute volumes are biased; ratios between pages less so. Cookieless tools (Plausible/Umami) measure everyone but cannot reliably identify returning users.
4. **SPAs**: verify each route change fires a page view; if not, inner pages "do not exist" in the data.
5. **Sampling**: GA4 samples high-volume explorations; standard reports do not.
6. **Minimum sample per judgment**: 100 impressions for a CTR; 30 sessions for a friction rate; 2 weeks for a page. Below that, group by template or page type, or mark as provisional.
7. **Conversion attribution**: clarify whether it is last click, first click or funnel-based. A CTA "that doesn't convert" on last click may be the one that starts most paths.
8. **Conversion definition**: contrast the tool's definition with the business one (a form submission is not a qualified lead; a sign-up is not a customer).

## 5. If there is no behavior data

Without Clarity/Hotjar/PostHog, rage and dead clicks cannot be seen. Alternatives while a tool is installed (Clarity is free; PostHog has a free tier with replay):

- Click events with `element_id` in the current analytics, and repeated clicks within < 1 s on the same `element_id` as a proxy for rage clicks.
- A 5-user test (concrete tasks, thinking aloud) uncovers most dead clicks in an hour.
- The browser console on a real mobile device for error clicks.

Propose the installation in the report's "Missing data" section, with the concrete benefit it will bring.
