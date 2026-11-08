---
name: research-radar
description: >-
  Mines a codebase for potentially novel techniques, compares each finding against the current
  state of the art (papers, open source, industry practice, patents), and separates genuine
  innovation from hype — classifying every candidate as known art, incremental improvement,
  novel combination, or novel contribution, and turning the promising ones into papers,
  preprints, talks, blog posts or open-source releases. Use it ALWAYS when scanning a repo, PR,
  sprint or architecture decision for research potential; when anyone asks "is this new?",
  "has anyone done this before?", "is this publishable?", "is this paper-worthy?" or "is this
  claim real?"; when comparing an internal solution against existing literature or tools; when
  vetting an external paper, library or product announcement for substance; and when preparing
  a research note, related-work section, preprint or tech-blog piece from engineering work.
  Apply it even if the words research, novelty, paper or state of the art never appear.
---

# Research Radar

Development now moves faster than reading. AI-assisted sprints produce non-obvious solutions
weekly, and almost nobody stops to ask whether any of it is *new* — so genuine contributions die
unnamed in private repos while renamed known techniques get announced as breakthroughs. This
skill is the copilot for that gap: it finds what a team has actually discovered, positions it
against the state of the art, and delivers an honest verdict with a concrete next action.

> **A novelty claim is worth exactly as much as the prior art search behind it.** The default
> verdict is "this already exists" — novelty must be earned against an honest search, honest
> baselines and honestly stated limitations. And "already exists" is a *successful* outcome:
> it names the literature the team can now adopt, cite and stop reinventing.

Two symmetric failure modes, both expensive:

- **False novelty (hype).** Announcing as new something that exists under another name, or
  something whose "improvement" is an artifact of weak baselines. Cost: public credibility,
  reviewer rejections, and a community that stops listening to you.
- **False dismissal.** Killing a genuine contribution with "surely someone has done this"
  without searching, or "it's just X + Y" when the integration is exactly where the difficulty
  and the value live. Cost: the contribution dies in a private repo and the community never
  benefits.

This skill exists to make both failures hard. It complements — does not replace — any
content-writing or engagement-judging skill that is installed: once a finding becomes a public
piece, those own the writing and the engagement judgment. Without them, this skill still owns the
substance and the honesty of the claim (see `references/dissemination.md`).

## How to use this skill

1. **Pick the operating mode.** They differ in depth, not in standards:
   - **Sprint scan** (~15 min, agile copilot mode) — run over a sprint's diff, a PR, or a
     feature branch at close-out. Output: a candidate inventory with quick triage. No final
     verdicts — only which candidates earn a deep dive. Designed to fit inside sprint cadence.
   - **Deep dive** (one candidate) — full prior art search, rubric, verdict card, next action.
   - **Codebase audit** — systematic pass over a whole repo. Produces a prioritized inventory,
     then deep dives on the top candidates.
   - **Claim check** — someone (a teammate, a paper, a library README, a product launch)
     claims novelty. Run phases 2–3 against *their* claim with the same rubric. This is the
     hype-detection mode, and the rubric is applied with the same severity as to your own work.
2. **Walk the pipeline in order.** Discover → Map → Judge → Harden → Share. Never skip Map:
   a verdict issued without a prior art search is an opinion, not a verdict.
3. **Load detail as needed:**
   - `references/discovery-signals.md` — what novelty looks like in code, the developer
     interview protocol, and how to scan large repos. Read it whenever you run phase 1.
   - `references/prior-art-search.md` — sources by domain, vocabulary reformulation, citation
     graph walking, and the criteria for closing a search. Read it whenever you run phase 2.
   - `references/novelty-rubric.md` — the full rubric with worked examples per level, plus the
     hype detectors and false-dismissal detectors. Read it whenever you issue a verdict.
   - `references/dissemination.md` — channel selection, the research note template, the IP
     clearance checklist, and how to promote without hype. Read it whenever a verdict is
     "novel combination" or better, or the user wants to publish anything.
4. **Record everything in the radar log** (see "Working at sprint speed") so candidates are
   never re-evaluated from scratch and verdicts accumulate into team knowledge.

## The pipeline

### Phase 1 — Discover (mine the codebase)

Hunt for candidates, not conclusions. The strongest signals that something non-obvious happened:

- **Reimplementations**: code that rebuilds what a library "should" do, with comments like
  "nothing existing handled X". Someone hit the edge of the state of the art and kept going.
- **Workaround markers**: `HACK`, `XXX`, "counterintuitively", "for some reason this is
  faster". Anomalies the team routed around often encode an unexplained discovery.
- **Anomalous numbers**: internal benchmarks that beat expectations, or degrade *less* than
  they should under load. Surprise is a research smell.
- **Novel compositions**: known techniques imported from a foreign domain and made to work
  together where the integration was genuinely hard.
- **Problem reframings**: the team solved a *different* problem than everyone else solves, and
  that reframing made the original problem easy.
- **Home-grown abstractions**: internal DSLs, protocols or invariants that map to nothing
  standard. Also: tests encoding behavior documented nowhere (empirically discovered edge cases).
- **Documented dead ends**: approaches tried and abandoned with reasons. Negative results are
  candidates too.

Interview the developer — the code rarely tells the whole story. The single highest-yield
question: *"What did you build yourself because nothing you found actually worked?"* Full
protocol and more signals in `references/discovery-signals.md`.

Output: a **candidate inventory**. Each entry: name, 2–3 sentence description, where it lives,
the problem it solves, why it *might* be novel. Cap a sprint scan at ~5 candidates — triage
beats completeness at this stage.

### Phase 2 — Map (establish the state of the art)

For each candidate, find the **nearest prior art**: the closest existing work. It always
exists. The delta against it *is* the contribution — or the proof there isn't one.

- Search the **problem**, not just your solution. Your solution may exist under a name you've
  never heard, coined by a community you don't read.
- Generate **at least 3 vocabulary reformulations**. Different communities name the same idea
  differently (databases say "incremental view maintenance", PL says "self-adjusting
  computation", build systems say "memoization with dependency tracking" — same concept).
- Search **implementations, not only papers**: GitHub code and issues, engineering blogs,
  Stack Overflow. Industrial prior art often never reaches a paper.
- **Walk the citation graph** of the nearest neighbors one hop backward and forward.
- **Absence of results is never evidence of novelty.** It is usually evidence of wrong
  vocabulary. The closing criteria for a search — when you may legitimately say "no prior art
  found" — are in `references/prior-art-search.md`, along with sources by domain.

Output: a **prior art map** per candidate — what exists, the nearest neighbor(s) with links,
the exact delta, and the queries used (so the search itself is auditable).

### Phase 3 — Judge (rubric + verdict)

Score the candidate against its nearest neighbor on five axes (full rubric with worked
examples in `references/novelty-rubric.md`):

| Axis | Question | Scale |
|---|---|---|
| Novelty | How far from the nearest prior art? | N0 exists under another name · N1 incremental variation · N2 novel combination, non-trivial integration · N3 new technique, insight or problem framing |
| Non-obviousness | Would a competent practitioner facing this problem arrive here naturally? | low / medium / high |
| Utility | Measurable improvement on a problem someone *outside this codebase* has? | metric, not adjective |
| Generality | Does it survive outside its birth context (other data, stack, scale)? | untested / partial / demonstrated |
| Evidence | How strong is the support? | E0 anecdote · E1 internal metrics · E2 fair-baseline comparison · E3 reproducible benchmarks + ablations |

Then run the **hype detectors** (strawman baselines, "novel = new to us", renaming, vanity
metrics, confounded improvements, demo-only results, citation vacuum...) and the
**false-dismissal detectors** ("it's just X + Y", "too simple to publish", "it's engineering,
not science"...). Both lists live in the rubric reference and both must be checked — the skill
is a two-sided filter, not a shredder.

**Verdict scale and default action:**

| Verdict | Condition | Default next action |
|---|---|---|
| Known art | N0 | Adopt the standard name, cite it, teach the team. Optionally an educational post ("we rediscovered X — here's the literature"). |
| Incremental | N1 | Engineering blog post, upstream OSS contribution, internal doc. Workshop paper only with E2+. |
| Novel combination | N2 and E2+ | Experience report, applied paper, conference talk, OSS release. |
| Novel contribution | N3 and E2+ | Preprint now (timestamp priority), then venue. Decide on patents *before* publishing. Potential seed for a research line. |
| Promising, unproven | N2–N3 with E0–E1 | Nothing public yet. Go to phase 4 and define the minimal publishable unit. |

### Phase 4 — Harden (make it defensible)

Only for candidates worth pursuing:

1. **State the claim in one falsifiable sentence.** "X improves Y by Z under conditions W."
   If it can't be falsified, it can't be published.
2. **Define the minimal publishable unit (MPU):** the smallest experiment that would sustain
   the claim in front of a hostile reviewer — strongest-available baseline, at least one
   ablation, one generalization test (second dataset/context), limitations section.
3. **Fair-baseline rule:** the baseline gets the same tuning budget as your method. Three
   weeks tuning yours vs. ten minutes on the baseline is how hype gets manufactured.
4. **Write the limitations before a reviewer finds them.** Where it breaks is part of the
   contribution.
5. **Build the reproducibility pack:** minimal code, data or generator, seeds, run
   instructions.

### Phase 5 — Share (channel, package, promote)

The **IP gate comes first** — before any public word. Whose code is it? Client work under
NDA? Employment or contract IP clauses? The operating rule: **publish the technique, never the
client's code** — abstract it, reimplement clean, demonstrate on synthetic data, and get
written clearance when the work was done for a client. Publishing also creates prior art that
destroys future patentability (yours and others') — that's sometimes exactly the point
(defensive publication), but decide it, don't stumble into it. Full checklist, channel table,
research note template and no-hype promotion guidance in `references/dissemination.md`.

## Verdict card (output format)

Close every deep dive and claim check with this exact card:

```
## [Candidate name]
- What it is: 2–3 sentences
- Where it lives: files / modules / PR
- Nearest prior art: [links] — queries used: [...]
- Delta: what is actually different from the nearest neighbor
- Scores: Novelty N_ · Non-obviousness _ · Utility _ · Generality _ · Evidence E_
- Detectors triggered: [hype or false-dismissal flags, or "none"]
- Verdict: Known art / Incremental / Novel combination / Novel contribution / Promising-unproven
- Next action: one specific step (cite & adopt / blog / MPU experiment / preprint / drop)
- IP status: clear / needs written approval / blocked
```

A sprint scan outputs the compact version: an inventory table with candidate, one-line
description, gut novelty guess, and "deep dive: yes/no/later".

## Working at sprint speed

This skill is a copilot, not a committee. To keep it inside an agile cadence:

- Run a **sprint scan at every sprint close** over the diff, or on any PR that felt harder
  than it should have. Fifteen minutes; inventory only.
- Maintain a **`RESEARCH_RADAR.md` at the repo root** — the radar log. Append every candidate
  and every verdict card. It becomes the team's accumulated research memory: candidates are
  never re-litigated, prior art found once is found forever, and patterns emerge across
  sprints ("this is the third time we work around the same limitation — that limitation is the
  research topic").
- Batch deep dives; they need real search time. One or two per sprint is a healthy rate.
- Promising-unproven candidates get their MPU written into the log so any future slack week
  can pick one up and run the experiment.

## Invariants

Boundary conditions — a broken invariant is a blocking finding regardless of how exciting the
candidate looks:

1. **Every novelty claim names its nearest prior art.** A claim with no nearest neighbor means
   the search wasn't done, not that the idea is unprecedented.
2. **Absence of search results is never evidence of novelty.** Minimum three vocabulary
   reformulations and the closing criteria in `references/prior-art-search.md` before
   concluding "not found".
3. **Verdicts cite evidence levels, not enthusiasm.** Below E2, no public claim stronger than
   "promising".
4. **"Already exists" is delivered as a win**: with the citation, the standard terminology,
   and what the team should adopt from the literature it just discovered it was part of.
5. **No client or proprietary code, data or identifying details ever leave the repo without
   explicit written clearance.** Techniques can be abstracted; code cannot.
6. **One rubric, one severity.** The team's own work and external claims being checked are
   judged with identical standards. A radar that flatters its owner is decoration.
