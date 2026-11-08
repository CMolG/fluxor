# Novelty rubric — judging candidates, detecting hype, avoiding unfair dismissal

Phase 3 converts a prior art map into a verdict. The rubric exists so the verdict depends on
the evidence and not on who's asking, how excited they are, or how much work it took. Apply it
identically to the team's own candidates and to external claims under a claim check.

## The five axes

### Novelty (N0–N3) — distance from the nearest neighbor

- **N0 — exists under another name.** The candidate is a rediscovery. Worked example: a team
  "invents" collapsing concurrent identical cache-miss lookups into one upstream call. That is
  *request coalescing / singleflight* (Go's groupcache popularized it) — textbook thundering
  herd mitigation. Verdict: known art. Still a win: the team just learned which literature it
  belongs to.
- **N1 — incremental variation.** Known technique, modest twist, same regime. Example: an LRU
  cache with eviction weights adjusted for one workload's skew. Real value, no new idea.
- **N2 — novel combination.** Known parts, but the composition is non-trivial: the parts
  weren't known to work together, the integration required solving real problems, and the
  combination unlocks something neither part does alone. Example: CRDTs applied to a domain
  where coordination-free merge was considered impossible, with the mapping from domain
  operations to CRDT operations being the actual hard part. The test for N2 vs N1: could a
  practitioner who knows both parts assemble this in an afternoon? If yes, it's N1.
- **N3 — new technique, insight or problem framing.** A mechanism, bound, algorithm, or
  reframing with no close prior. Rare. Most honest careers produce a handful. If phase 2 was
  shallow, what looks like N3 is almost always an unfound N0 — treat any N3 rating as a
  trigger to *extend the search*, not to celebrate.

Rate the candidate at the level the *delta* supports, not the level the whole system occupies.
A large impressive system built entirely of known parts assembled in known ways is N0/N1 as a
research object, however excellent it is as engineering.

### Non-obviousness (low / medium / high)

Would a competent practitioner, facing the same problem with the same constraints, arrive here
as a natural next step? Beware two distortions: hindsight ("obvious once you see it" — most
good ideas are; judge from *before* the insight), and difficulty worship (months of hard work
can produce an obvious result, and an afternoon can produce a non-obvious one — effort is not
an axis).

### Utility (metric, not adjective)

A measurable improvement on a problem someone **outside this codebase** has. "Much faster" is
an adjective; "p99 latency −38% at equal cost on workload class X" is utility. If nobody
outside the repo has the problem, the candidate may still be worth an internal doc — but it is
not a contribution to the community, because contribution implies an audience with the problem.

### Generality (untested / partial / demonstrated)

Does it survive outside its birth context — second dataset, different stack, 10× the scale,
adversarial inputs? Most false novelty dies here: the technique was real but was secretly a
property of one context. Generality untested caps the verdict at promising-unproven regardless
of N-level.

### Evidence (E0–E3)

- **E0 — anecdote.** "It felt faster", one demo, no numbers.
- **E1 — internal metrics.** Real numbers, no comparison, or comparison against the team's own
  previous version only.
- **E2 — fair-baseline comparison.** Measured against the strongest available alternative,
  configured competently, same tuning budget both sides.
- **E3 — reproducible benchmarks + ablations.** Anyone can re-run it; each component's
  contribution isolated; failure cases reported.

Evidence gates publication: below E2, nothing public stronger than "promising". The N-axis
says how new it is; the E-axis says how much you're allowed to claim.

## Hype detectors

Run every candidate through this list. Each triggered detector is written into the verdict
card; two or more triggered usually caps the verdict at promising-unproven until fixed.
These are the patterns by which non-innovation gets dressed as innovation:

1. **No baseline, or strawman baseline.** Compared against nothing, or against a weak,
   misconfigured, or obsolete alternative. The classic tell: the baseline got minutes of
   attention and the method got weeks.
2. **"Novel" means "new to us".** No prior art search was run; novelty is asserted from the
   team's own surprise. Invariant 1 violation.
3. **Renaming.** A known technique wearing a new brand name. Detector: describe the mechanism
   without the brand name and search that description.
4. **Vanity metrics and cherry-picking.** Improvements on a metric nobody cares about, best-of-N
   runs reported as typical, no failure cases anywhere. Honest work reports where it loses.
5. **Confounded improvement.** The gain is inseparable from a simultaneous change in hardware,
   data volume, tuning budget or engineering hours. Without an ablation, the technique gets
   credit for the confound.
6. **Single-context results, unacknowledged.** Works on one dataset/workload/stack and the
   writeup quietly generalizes. (Single-context *acknowledged* is fine — it's called
   limitations.)
7. **Demo gradient.** Impressive in the demo, collapses on the second question. Research
   survives interrogation; demos survive presentation.
8. **Claims scale with enthusiasm, not evidence.** The abstract promises a revolution; the
   evaluation section is one table. Read claims and evidence side by side; the gap is the hype.
9. **Irreproducibility by construction.** No code, no data, no seeds, moving target ("the
   latest version fixes that"). Unfalsifiable claims are not contributions.
10. **Effort presented as contribution.** "Eighteen months of engineering" is a cost, not a
    result. Hard ≠ novel.
11. **Citation vacuum.** Zero engagement with related work. Nobody works in a vacuum; a
    writeup with no neighbors hasn't looked for them.

## False-dismissal detectors

The symmetric list — the reflexes by which genuine contributions get killed. Check them
whenever the verdict is heading toward "nothing here", especially when it's heading there
*fast*:

1. **"Surely someone has done this."** Certainty without a search. The feeling of familiarity
   is not a citation; run phase 2 and produce the nearest neighbor or withdraw the objection.
2. **"It's just X + Y."** Novel combinations are a real contribution class (N2) when the
   integration is where the difficulty lives. The question is never whether the parts are
   known — it's whether the composition was.
3. **"Too simple to publish."** Simplicity with evidence is a *feature* — simple methods that
   match complex ones are among the most cited results in every field. Complexity is not
   rigor.
4. **"It's negative, so it's nothing."** "We show X fails under Y, and why" saves the entire
   community from re-running the failure. Negative results with understood causes are
   publishable and there are venues and workshops that want them.
5. **"It's engineering, not science."** Systems venues, industry tracks and experience
   reports exist precisely for rigorous accounts of built things. The bar is rigor and
   transferable insight, not lab coats.
6. **"No theory, just measurements."** A robust, reproducible empirical regularity without an
   explanation is how half of systems research starts. The missing theory is future work, not
   a disqualification.
7. **"Someone kind of did this in 2009."** Distant prior art doesn't erase the delta. If the
   2009 work is the nearest neighbor, state the delta against it; "related work exists" is
   the *normal condition* of research, not a rejection.

## Composing the verdict

1. Confirm the prior art map is closed (criteria in `prior-art-search.md`). No map → no
   verdict.
2. Score the five axes against the nearest neighbor.
3. Run both detector lists; record triggers.
4. Map to the verdict scale in SKILL.md (Known art / Incremental / Novel combination / Novel
   contribution / Promising-unproven). When axes disagree, evidence wins: a thrilling N3 with
   E0 is promising-unproven, full stop.
5. Attach the **one specific next action** — a verdict without a next action is trivia.

Calibration honesty: across a normal codebase expect most candidates to land N0–N1, a few N2,
and N3 almost never. A radar that keeps finding N3 in its own repo is measuring its owner's
excitement. The distribution being skewed toward known art is not the skill failing — it is
the skill working, and every N0 verdict ships with free education: the name, the paper, the
community the team didn't know it belonged to.
