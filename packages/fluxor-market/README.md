# Fluxor's market

**The catalog Fluxor online serves.** It is where the skills, mods, roles, steps and flows are
gathered: Fluxor is an online tool connected to local projects, the way Officium is (harness
management and agentic flow design), and the catalog it offers is the one built here. A piece
proven in a real project's harness is generalized and lands here, and the improvements made here
flow back to the projects that use it. It was the separate `useful-skills` repository until
2026-09-29 (JAVA-270); its history came with it, under this path.

My own agentic building blocks, in one place:

- **[Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)**
  (`skills/`): folders of instructions, references and scripts that Claude loads when a task
  calls for them.
- **Meta-skills** (`meta-skills/`): skills that depend on a form. What they produce is shaped by a
  person's answers; the CEET family interviews a professional and renders their cognitive clone
  into a pack of agents, skills, commands, rules and hooks. See [`meta-skills.md`](doc://contracts/meta-skills).
- **The Fluxor market** (`market/`): the roles, mods, steps and flows that Fluxor composes into an
  agentic session.

This repository is the **single source of truth for the base marketplace**: the one I design. A
deployment pipeline builds it into a content-addressed bundle to seed or update the marketplace
database (see [`catalog-format.md`](doc://contracts/catalog-format)); community atoms can live in
other namespaces later. Everything here is written in American English.

```
packages/fluxor-market/
├── marketplace.json        namespace, publisher, language exceptions
├── marketplace.lock.json   version + content hash of every atom (written by `tools/marketplace.py lock`)
├── schemas/                JSON Schemas: one per atom kind, the marketplace config and the bundle index
├── tools/                  marketplace.py (validate · list · inventory · lock · build) and its tests
├── skills/<id>/            SKILL.md + skill.json (manifest) + references/, scripts/, assets/, evals/
├── meta-skills/<id>/       the same, plus the form: interview/form.json, templates/ (packaging "meta")
└── market/
    ├── <kind>s/<id>.md     the prompt of each role, mod, step and flow…
    ├── <kind>s/<id>.json   …and its manifest
    ├── hooks/<id>.*        one hook per event: manifest, fallback .md, .sh and/or .ps1
    ├── presets/<id>.json   a named bundle of skills and hooks a project adds in one step (`officium`); it may also carry `precedenceTemplates`, rule lists an owner imports into a project's precedence
    ├── inventory.json      GENERATED Fluxor projection of the manifests (never edit by hand)
    ├── engine.json         manifest for the runtime files below
    ├── lexicon.json        intent vocabulary (incl. Spanish) → catalog vocabulary, used by motor.py
    └── motor.py            deterministic atom assembler used by the `atoms` skill and its hook
```

## Skills

| Skill | What it does |
|---|---|
| [`product-hunt-launch-readiness`](skills/product-hunt-launch-readiness/SKILL.md) | Audits a repository, a live URL, or both against Product Hunt's official launch guide and featuring guidelines. It produces an evidence-backed readiness report (blockers → polish), a validated, ready-to-paste launch kit, and a launch timeline in your timezone. |
| [`landing-page-marketing`](skills/landing-page-marketing/SKILL.md) | Writes, audits and builds landing pages and sales pages that sell by making the product's value obvious: grounded in real facts and customer language, structured by the visitor's awareness level, rendered and checked on desktop and mobile, linted, and scored with an evidence-based value-perception rubric. |
| [`ux-psychology`](skills/ux-psychology/SKILL.md) | Designs and audits interfaces with cognitive psychology and neuroscience: cognitive load, the gulfs of execution and evaluation, Fogg's B=MAP, processing fluency and trust, dark patterns versus desirable difficulties, cognitive accessibility (COGA/WCAG 2.2) and DSA/GDPR compliance. Ships a friction scanner. |
| [`layout-discipline`](skills/layout-discipline/SKILL.md) | Builds and reviews UI so elements breathe, nothing collapses or overlaps at any width, overflow always wraps, truncates or scrolls, and components are reused or evolved instead of duplicated. Ships a layout auditor. |
| [`ui-fluidity-verification`](skills/ui-fluidity-verification/SKILL.md) | Verifies that a UI is fluid, not just functional: frame, interaction and layout-shift invariants, 18 algorithmic layout checks in real engines across widths and font scales derived from the CSS, the honest limits of headless emulation, and a PASS/FAIL/INCONCLUSIVE gate that tells regressions from noise. Ships an in-page probe, a breakpoint matrix, a statistical gate and a structural layout diff. |
| [`traffic-to-funnel`](skills/traffic-to-funnel/SKILL.md) | Turns real analytics and behavior data (GA4, Plausible, PostHog, Clarity, Search Console, logs, CSV…) into a diagnosis and one funnel per product: amplify what works, repair what leaks, monetize where intent peaks. |
| [`research-radar`](skills/research-radar/SKILL.md) | Mines a codebase for potentially novel techniques, checks each against the state of the art, separates real innovation from hype, and turns the promising ones into papers, talks, posts or releases. |
| [`portfolio-positioning`](skills/portfolio-positioning/SKILL.md) | Turns an existing website (a venture studio, a product, a blog) into a hiring surface for its owner, page by page, without hurting the product's credibility: canonical identity, entity SEO, AEO/GEO for recruiters asking LLMs, behavioral levers and copy banks. The owner's identity lives in `.harness/config/portfolio-positioning.json`. |
| [`atoms`](skills/atoms/SKILL.md) | Inspects, explains or changes the market atom set (role, mods, steps) mounted for a task, and adds new atoms to the market. Drives `market/motor.py` and ships the `UserPromptSubmit` hook that mounts the set on every prompt. |
| [`reduction`](skills/reduction/SKILL.md) | Runs a code-reduction campaign (measure first, apply only after approval) with 21 techniques for Java, React and cross-cutting code; source roots, the shared UI package and already-decided techniques come from config or autodetection. |
| [`topology`](skills/topology/SKILL.md) | Derives a workspace's real package graph from the code and checks it: no cycles and no phantom dependencies always; layering rules (forbidden edges, isolated groups, leaf packages, exceptions with a reason) from config; `route` maps domain vocabulary to Maven contexts or packages. |
| [`review-harness`](skills/review-harness/SKILL.md) | Verifies any project harness that follows the [harness convention](doc://contracts/harness-convention): provider bridges, versioned wiring, load chain, pointer-only `AGENTS.md`, broken links, hook test benches, skill front matter, market copy integrity. |
| [`backlog`](skills/backlog/SKILL.md) | A provider-agnostic session protocol for an MCP-backed backlog (resume before pick, unblock the sprint before leaving it, action plan before code, status reports, review before done, human "walls", Radar-style `card://KEY` references in code and commits, the documentation changelog). Officium is the first adapter; the guide covers GitHub Issues, Linear and Jira. |
| [`autoloop`](skills/autoloop/SKILL.md) | `backlog`'s complement for running many sessions at once: `/autoloop [n]` starts a detached supervisor that keeps N background Claude sessions alive, one card each in its own git worktree, recycling each between cards; an atomic per-card claim keeps two sessions off one card, and every review ends by merging the card into one control branch and pushing, retried and never forced. Standard-library Node. |
| [`jira-agentic-requirements-pipeline`](skills/jira-agentic-requirements-pipeline/SKILL.md) | Turns an ambiguous Jira ticket into a validated functional contract: rule-based discovery, a prioritized business questionnaire answered in a resumable CLI, and a base-branch plan with traceability. `backlog` uses it, when installed, to select the questions a card that is not ready needs. |

Every skill is project-agnostic. The ones that work on a project's harness (`atoms`, `autoloop`, `backlog`,
`reduction`, `review-harness`, `topology`) follow the [harness convention](doc://contracts/harness-convention):
they locate the project from `$CLAUDE_PROJECT_DIR` or git, and read project facts from
`.harness/config/<skill>.json`, autodetecting what is missing.

## Meta-skills

A meta-skill depends on a form: what it produces is shaped by the answers a person gives to the
questions it declares (`packaging: "meta"`, see [`meta-skills.md`](doc://contracts/meta-skills)). The
family came from the `cognitive-skills` repository; its state of the art and improvement plan are in
[`2026-09-29-meta-skills-review.md`](doc://history/reports/2026-09-29-meta-skills-review).

| Meta-skill | What it does |
|---|---|
| `ceet-<role>` (15: [`backend-engineer`](meta-skills/ceet-backend-engineer/SKILL.md), [`frontend-engineer`](meta-skills/ceet-frontend-engineer/SKILL.md), [`devops-sre`](meta-skills/ceet-devops-sre/SKILL.md), [`data-analytics`](meta-skills/ceet-data-analytics/SKILL.md), [`product-manager`](meta-skills/ceet-product-manager/SKILL.md), [`ux-researcher`](meta-skills/ceet-ux-researcher/SKILL.md), [`ui-designer`](meta-skills/ceet-ui-designer/SKILL.md), [`copywriter`](meta-skills/ceet-copywriter/SKILL.md), [`marketing`](meta-skills/ceet-marketing/SKILL.md), [`sales`](meta-skills/ceet-sales/SKILL.md), [`customer-success`](meta-skills/ceet-customer-success/SKILL.md), [`financial`](meta-skills/ceet-financial/SKILL.md), [`legal-compliance`](meta-skills/ceet-legal-compliance/SKILL.md), [`people-ops`](meta-skills/ceet-people-ops/SKILL.md), [`founder-ceo`](meta-skills/ceet-founder-ceo/SKILL.md)) | Cognitive Extraction Engines. Each interviews a professional in its role from its `interview/form.json` (49–75 questions: a required core and real-decisions module, then optional depth modules), synthesizes the answers into a cognitive profile with every directive traced to the question it came from, and renders the profile into a pack of agents, skills, commands, rules and (engineering roles) hooks for Claude, ChatGPT, Cursor, Copilot, Gemini and other tools. The pack goes to the project, `.harness/packs/<role>-<person>/` by default. |

| Companion | What it does |
|---|---|
| [`ceet-core`](meta-skills/ceet-core/SKILL.md) | The shared method of the CEET roles: methodology, consent, synthesis rules, pack contract v2, loading a pack into each AI tool, adding a role, and the tools that record an interview, render, validate and erase a pack, retrieve its decisions, run its checks and measure its fidelity. Every role requires `ceet-core@2`. |
| [`ceet-autodiscover`](meta-skills/ceet-autodiscover/SKILL.md) | Detects which role a request needs from each role's `routing.keywords`, checks whether the project has a filled pack for it, and gates the run (initialize, use a labeled example, or continue without CEET). |
| [`ceet-impersonator`](meta-skills/ceet-impersonator/SKILL.md) | Drafts a simulated pack from evidence (a public figure's public work, or anyone else with their own recorded consent), with the Simulation Notice on every file, an evidence row for every directive and ceet-core's validator. |
| [`ceet-sub-agent-orchestration`](meta-skills/ceet-sub-agent-orchestration/SKILL.md) | Splits complex work across sub-agents bound to role packs, validating every handoff against the `OrchestrationPlan` and `SubAgentResult` contracts. |

## Documents (pages in Officium's Documentation, project Javadaba)

- [`harness-convention.md`](doc://contracts/harness-convention): the `.harness/` layout, its two
  laws, precedence, load chain, provider bridges and hook split, and the rules that keep a skill
  generic.
- [`catalog-format.md`](doc://contracts/catalog-format): manifests, versions and the lock, the
  Fluxor projection, the bundle, how the database is seeded and how a project receives its
  harness.
- [`2026-09-27-useful-skills-architecture-review.md`](doc://history/reports/2026-09-27-useful-skills-architecture-review): quality review of every atom and
  skill, and the target architecture for Fluxor as a web harness designer + local sync MCP + flow
  board.
- [`meta-skills.md`](doc://contracts/meta-skills): what a meta-skill is, the form → profile → pack
  lifecycle, what the catalog checks, and how Fluxor serves one.
- [`2026-09-29-meta-skills-review.md`](doc://history/reports/2026-09-29-meta-skills-review): the meta-skills against the state of
  the art, what the move changed, and the improvement plan.

## The market

The market holds the composable pieces of an agentic configuration for the
Fluxor IDE:

| Kind | Count | Rule |
|---|---|---|
| Roles | 14 | Only one active at a time: mixing personas dilutes judgment. |
| Mods | 37 | Stackable; conflicts resolve as security > correctness > scope > style. Mods sharing an `exclusiveGroup` (e.g. `design-system`) never stack. They attach to steps (flow steps included), not to a flow as a whole. |
| Steps | 7 | Atomic units that compose into a plan. |
| Flows | 12 | Pre-planned pipelines (finite or looping) with their own constraints. |

Every atom is **two files**: a `.md` with its prompt and a `.json` manifest next to it (a skill:
`SKILL.md` and `skill.json`). `market/inventory.json` is generated from the manifests. Each kind's
conventions are in `.harness/rules/projects/fluxor-market-atoms.md`, which each kind's `AGENTS.md`
imports: read it before adding an atom.

## Changing the catalog

```bash
python3 tools/marketplace.py validate      # schemas, references, lock, inventory, language
python3 tools/marketplace.py list [kind]   # the catalog
# after editing an atom: bump its "version", then
python3 tools/marketplace.py inventory     # regenerate the Fluxor projection
python3 tools/marketplace.py lock          # record the new version and content hash
python3 -m unittest discover -s tools/tests
python3 tools/marketplace.py build --out dist/marketplace   # the bundle a pipeline publishes
```

A content change without a version bump fails validation, and published atoms are deprecated,
never deleted. The workspace attestation runs the same checks (`scripts/lib/attestation.mjs`). Details and the publishing contract are in
[`catalog-format.md`](doc://contracts/catalog-format).

Fluxor reads a project's own `market/inventory.json` before its bundled one, so opening this
repository in Fluxor shows this catalog. To check how an intent would be assembled without Fluxor:

```bash
python3 skills/atoms/atoms.py mount "build an accessible signup form in React"
python3 skills/atoms/atoms.py list mods
```

## Installing a skill

- **Claude Code:** copy the skill folder from `skills/` into `~/.claude/skills/` (available
  in every project) or `<your-project>/.claude/skills/` (that project only).
- **Claude apps / API:** zip the skill folder (the `evals/` directory isn't
  needed) and upload it wherever your plan manages skills.
- **Meta-skills** install the same way, from `meta-skills/`. Copy what their manifest `requires`
  alongside: every `ceet-<role>` and every CEET companion needs `ceet-core` in the same skills
  folder, because they read its references as a sibling (`../ceet-core/`).
- **A whole harness** (skills, roles, mods, steps, flows, hooks, presets and the engine) installs from a selection,
  `<project>/.harness/harness.json`: `python3 tools/marketplace.py install` writes the copies and a
  lock, and `install --check` reports a copy edited by hand. The workspace this catalog lives in
  installs its own harness that way (see "How a project receives its harness" in
  [`catalog-format.md`](doc://contracts/catalog-format)).

---

## product-hunt-launch-readiness

Getting featured is what makes a Product Hunt launch. Featuring is editorial,
and a handful of avoidable mistakes rule a launch out: a waitlist instead of
a product, no maker comment, a broken link, an unclear tagline, asking for
upvotes. This skill checks for all of them, plus the practical things that
waste launch-day traffic.

**Ask things like:**

- "Is this repo ready to launch on Product Hunt next Tuesday? I'm in Madrid."
- "Check https://myapp.com before our PH launch."
- "Review my Product Hunt listing and give me a fixed version I can paste: …"
- "Prepare everything for our Product Hunt launch and fix what you can in the code."

**What you get** (in `product-hunt-launch/`):

- `readiness-report.md`: a verdict (🔴 Not ready · 🟡 Ready with fixes ·
  🟢 Ready · 🏆 Launch-perfect), findings with `file:line` or URL evidence
  and a concrete fix each, a scorecard, featuring potential (Useful / Novel /
  High craft / Creative), and questions for what can't be verified from code.
- `launch-kit.json` / `launch-kit.md`: name (≤40), tagline (≤60),
  description (≤500, core message in the first ~260), up to 3 launch tags,
  thumbnail and gallery plan, first comment, shoutouts, pricing, promo, and
  sharing messages that never ask for upvotes. All of it is validated by a
  script, not counted by eye.
- `evidence/`: raw audit JSON and screenshots, including a 1270×760
  gallery-ready shot of your site.

**How it works:**

| Piece | Role |
|---|---|
| `SKILL.md` | Workflow, severity and verdict rules, and the rules that can't be gotten wrong. |
| `references/product-hunt-guide.md` | The official launch guide (all nine pages), featuring guidelines and definitions, distilled, with volatile limits flagged. |
| `references/audit-checklist.md` | About 60 checks with severities, where to find the evidence, and the fix. |
| `references/launch-kit-guide.md` | How to write each listing field, with the gallery storyboard and first-comment template. |
| `scripts/audit_repo.py` | Repo evidence: metadata, assets with real pixel sizes, copy signals with `file:line`, routes, providers, unguarded AI endpoints. Never reads real `.env` files. |
| `scripts/audit_url.py` | Live-site evidence: head metadata, social image and icon sizes, CTAs, copy signals, third-party tools, broken links, `?ref=producthunt`. |
| `scripts/capture_screenshots.cjs` | Playwright screenshots (1270×760 gallery, full page, mobile), console errors, rendered HTML, and a 240×240 thumbnail. |
| `scripts/check_launch_kit.py` | Validates every listing field against the form's limits and rules. |
| `scripts/launch_timeline.py` | 12:01 AM PT → your local time (DST-safe), plus T-30 to T+6 months milestones. |

**Requirements:** Python 3.9+ (standard library only). Screenshots
additionally need Node.js and Playwright
(`npm i -D playwright && npx playwright install chromium`).

**Tests:** `evals/` contains three realistic scenarios (a Next.js repo with
planted launch issues, a waitlist-only landing page, and a flawed draft
listing for a well-built site) with graded expectations. `evals/evals.json`
explains how to serve the fixtures. `evals/trigger-evals.json` holds 20
should/shouldn't-trigger queries, including near misses such as "scrape the
Product Hunt leaderboard" and "write a Show HN post". Use them to tune the
description with Anthropic's `skill-creator` optimizer, from a normal local
Claude Code session:
`python -m scripts.run_loop --eval-set <path>/evals/trigger-evals.json --skill-path <path> --model <model> --max-iterations 5`.

---

## landing-page-marketing

A landing page has one job: make the right visitor believe the product is worth more to them than
it costs, and make the next step easy. This skill treats that as a *value perception* problem. It
makes each driver of perceived value visible on the page and backs it with evidence:

- the outcome;
- proof that it works;
- time to the first win;
- effort;
- risk;
- an honest price frame;
- differentiation from the real alternative.

It never invents facts, testimonials or urgency.

**Ask things like:**

- "Our landing page converts at 0.9%. Here's the HTML and my notes: tell me what's wrong and rewrite it."
- "Hazme una landing en HTML para la suscripción de mi tostadero de café." <!-- lang:es: a Spanish request, on purpose -->
- "Audit https://myapp.com: why aren't visitors starting the trial?"
- "Write the hero and pricing section for my course's sales page."
- "Our pricing table confuses people. Redo it so the value of each plan is obvious."

**What you get** (in `landing-page/` unless you name another place):

- `value-brief.md`. It contains:
  - a sourced fact list and customer language;
  - awareness level and market sophistication;
  - alternatives;
  - the value ledger;
  - headline options;
  - objections;
  - the offer;
  - a claims register.
- `copy-deck.md`, the page copy section by section, each section with its job. Or the page itself:
  the real components edited in your repo, or a self-contained, mobile-first HTML file.
- `audit-report.md` for audits. It contains:
  - a value perception score out of 100;
  - "the one thing" to fix first;
  - a 5-second test on desktop and mobile;
  - ranked fixes with evidence;
  - a claims and compliance review;
  - before → after rewrites.
- `evidence/`: first-screen screenshots (1440×900 and 390×844), a full-page shot, `fold.json`, the
  extracted page outline and lint results.

**How it works:**

| Piece | Role |
|---|---|
| `SKILL.md` | Workflow (scope → evidence → value brief → architecture → copy → build → verify), and the rules that protect the client. |
| `references/value-perception.md` | The value model and each lever. Mining customer language, alternatives, price framing, offer design, costly signals. |
| `references/page-architecture.md` | Section order and length by awareness level, price, traffic source and page type; the hero; CTAs and forms. |
| `references/copywriting.md` | Headlines by angle, benefit-feature-proof blocks, testimonials, CTAs, pricing copy, FAQs, editing passes, before/after examples, Spanish notes. |
| `references/advertising-canon.md` | Ogilvy, Hopkins, Schwartz, Caples, Sugarman, Halbert, Collier, Sutherland, Ries & Trout, Dunford, Hormozi, Cialdini, and behavioural-economics findings with replication status. |
| `references/proof-and-compliance.md` | Claims register, proof hierarchy, testimonials and reviews, real vs fake urgency, pricing and subscriptions. The US/EU/UK legal map (FTC 16 CFR 255/465, UCPD, Omnibus 30-day price rule, DMCC Act, Directive 2024/825), and how to decline deceptive asks helpfully. |
| `references/audit-rubric.md` | Eight weighted levers with anchored 0–5 scores, trust-destroying caps, bands, the 5-second test and a section checklist. |
| `scripts/capture_page.cjs` | Renders the page (Playwright). Records exactly which headings, CTAs, images and prices are visible in the first screen on desktop and mobile, plus mobile overflow and load timings. |
| `scripts/extract_page.py` | The message hierarchy in page order: hero, sections, CTAs, forms (field counts), prices, quotes, meta. |
| `scripts/copy_lint.py` | Flags hype words, unproven claims, fake-urgency language, generic CTAs and placeholders; checks you/we balance and readability (English and Spanish). With `--facts`, flags every number not found in your facts file. |
| `scripts/value_score.py` | Turns per-lever scores (each needing evidence) into the weighted score, applies caps, and names the biggest gaps. |

**Requirements:** Python 3.9+ (standard library only). Screenshots and first-screen checks also need
Node.js and Playwright (`npm i -D playwright && npx playwright install chromium`).

**Research behind it:**

- **The classic canon:** *Ogilvy on Advertising*, *Confessions of an Advertising Man*, *Scientific
  Advertising*, *Breakthrough Advertising*, *Tested Advertising Methods*, *Alchemy*, *Obviously
  Awesome*, *$100M Offers*, *Influence*.
- **Conversion research, graded by evidence strength:** NN/g eyetracking and scanning studies,
  Unbounce benchmarks, Baymard, Spiegel Research Center, Google/Deloitte speed data, and the
  peer-reviewed pricing literature.
- **Existing marketing skills,** notably coreyhaines31/marketingskills and several copywriting and
  offer skills, with a gap analysis. The skill's own content is original.

**Tests:** `evals/` holds three scenarios with graded expectations:

- a flawed SaaS page plus founder notes (fake timer, inflated count, anonymous testimonials, demo
  form on a self-serve product);
- a Spanish coffee-subscription page built from scratch;
- a course sales page where the user asks for a resetting timer, an inflated student count and
  invented testimonials.

`evals/trigger-evals.json` has 20 should/shouldn't-trigger queries, including near misses (ads,
emails, PageSpeed fixes, Product Hunt listings, Figma-to-code).

**Results so far** (two iterations, each scenario run once with the skill and once without):

| | Pass rate | Time | Tokens |
|---|---|---|---|
| With the skill | 100% (47/47) | ~7 min | ~145k |
| Without the skill | 75% (36/47) | ~3.5 min | ~70k |

The base model already refuses fake timers and invented testimonials when asked directly, and it
writes decent copy. The skill's gains are in the details:

- It doesn't fill gaps with invented facts (coffee origins, grind options, plan policies, contact
  details, course requirements).
- Placeholders never show to visitors.
- Mockups are labelled as examples.
- It answers the buyer's key objection.
- It checks real first-screen renders.

The skill takes about twice the time and tokens.

The description was tuned with skill-creator's trigger loop (train/held-out split). In headless
`claude -p` runs the skill triggers on only a minority of should-trigger queries, and never on the
near misses. The model often does copy tasks without consulting any skill, so ask for it by name
(or `/landing-page-marketing`) when you want the full workflow.
