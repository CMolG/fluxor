# Prior art search — mapping the state of the art

Phase 2 turns "we think this might be new" into "here is the closest existing work and here is
the exact delta". The search is the load-bearing wall of every verdict: a weak search makes
false novelty (embarrassment) and false dismissal (waste) equally likely.

## The nearest-neighbor doctrine

For every candidate there exists a **nearest prior art** — the closest thing anyone has
published, shipped or open-sourced. It always exists; the only question is how near. The
search is over when you can name it and articulate the delta. Framing the search as "find the
nearest neighbor" instead of "check if this exists" changes behavior: you can't answer "does
it exist?" honestly without knowing the landscape, but you *can* always return the closest
point you found, with links, and let the delta speak.

The delta against the nearest neighbor is the entire contribution. "We do X" is not a claim;
"unlike [nearest neighbor], we do X under constraint Y, which they cannot" is.

## Sources, in working order

Work down this list; stop when marginal searches stop changing the picture.

1. **Semantic Scholar / Google Scholar** — broadest paper coverage; Semantic Scholar's
   citation graph and "related papers" are the best walking tools.
2. **arXiv** — where fast-moving fields (ML, systems, PL, security) actually live; papers
   appear here 6–18 months before venues. Search titles/abstracts, then full text.
3. **Papers with Code** — links papers to implementations and benchmark leaderboards; the
   fastest way to find whether an idea has a maintained implementation and what it's called.
4. **GitHub search (code + issues)** — industrial prior art often never reaches a paper.
   Search distinctive identifiers, error messages, and problem phrasings in issues; an issue
   thread saying "we solved this by..." is prior art.
5. **Venue proceedings for the owning community** — every problem has a community that
   considers it theirs (see vocabulary section). Browse the last 2–3 years of their venue:
   ML → NeurIPS/ICML/ICLR; systems → OSDI/SOSP/NSDI/EuroSys; databases → SIGMOD/VLDB;
   software engineering → ICSE/FSE; PL → PLDI/POPL/OOPSLA; security → S&P/USENIX Sec/CCS;
   HCI → CHI; IR/web → SIGIR/WWW. USENIX venues are fully open access.
6. **Engineering blogs** — Netflix, Cloudflare, Meta, Uber, Shopify, Discord, fly.io and
   dozens more publish production techniques years before (or instead of) academia. Site
   search them for the problem vocabulary.
7. **Google Patents** — mandatory when commercial interest exists; also a surprisingly good
   index of industrial techniques that were never blogged.
8. **HN Algolia search, Lobsters, Stack Overflow** — folk knowledge layer: names, prior
   discussions, "this is just X" comments that hand you the standard terminology for free.

## Vocabulary reformulation — the core technique

Most failed searches fail on vocabulary, not on novelty. Different communities coin different
names for the same idea, and your team's internal name for a thing is almost never the
literature's name. **Minimum three vocabulary families per candidate** before trusting any
absence.

Worked example — the same concept across communities:
- Databases: *incremental view maintenance*
- Programming languages: *self-adjusting computation*, *incremental computation*
- Build systems: *memoization with dependency tracking* (Salsa, Adapton, Shake)
- Spreadsheets/UI: *reactive recomputation*, *dirty marking*

A team that only searches its own phrase ("recompute only what changed") finds none of these
and wrongly concludes novelty.

Another — near-synonyms for one failure pattern: *thundering herd*, *cache stampede*,
*dogpile effect*, *retry storm*, *request coalescing / singleflight* (the mitigation).

How to generate reformulations:

- **Rename by community.** Ask: "which field owns this problem?" — then "what would a
  database person / PL person / networking person call it?" Search each dialect.
- **Search the problem, then the solution, then the mechanism.** Three different query
  shapes: "how to avoid recomputing unchanged results" (problem), "incremental computation
  framework" (solution), "dependency graph dirty propagation" (mechanism).
- **Abstract one level up and one level down.** Your "streaming deduplication for webhook
  events" is an instance of "exactly-once delivery" (up) and uses "content-addressable
  windowed sets" (down). Search all three altitudes.
- **Use an LLM as a thesaurus of communities**: describe the technique plainly and ask what
  it's called in adjacent fields — then verify every suggested term against real sources.
  Suggested names are leads, never evidence.

## Citation graph walking

Once any nearest-neighbor candidate appears:
- **Backward** (its references): finds the foundational work and older names.
- **Forward** (papers citing it — Semantic Scholar / Google Scholar "cited by"): finds the
  current frontier and whether your delta was already taken.
- One hop each way per neighbor is usually enough to stabilize the map; two hops for deep
  dives on N3 candidates.
- The related-work sections of the two or three nearest papers are pre-built maps of the
  field — read them before building your own.

## Closing criteria — when "no prior art found" is a legitimate conclusion

You may write "no prior art found" only when **all** of these hold:

1. ≥ 3 vocabulary families searched, including at least one generated by the
   which-community-owns-this question.
2. Problem-shaped, solution-shaped and mechanism-shaped queries all tried.
3. Implementations searched (GitHub code + issues), not only papers.
4. The owning community's main venue browsed for the last ~2 years.
5. The nearest neighbors that *did* appear had their citation graphs walked one hop.
6. The queries used are **recorded in the prior art map** — an unauditable search is an
   unfinished search.

Even then, phrase it as "no prior art found under these queries", never "no prior art
exists". Reviewers, HN commenters and future-you will test that sentence.

## Time-boxing by mode

- **Sprint scan:** 2–3 quick searches per candidate, nearest-neighbor guess only. The output
  is "deep dive: yes/no", not a verdict.
- **Deep dive:** the full protocol above; typically 1–3 hours of real search per candidate.
- **Claim check:** invert the burden — the claimant's own related-work section (or its
  absence) is the first evidence. A novelty claim with a citation vacuum fails invariant 1
  before you run a single query; your searches then establish what they should have cited.

## The prior art map (output format)

Per candidate:

```
### Prior art map — [candidate]
- Queries run: [list, verbatim]
- Nearest neighbor(s): [name + link] — what it does, in one line each
- Adjacent art: [2–5 links worth knowing about]
- Delta: what the candidate does that the nearest neighbor does not (one falsifiable sentence)
- Vocabulary learned: the standard names the team should adopt from now on
- Confidence in the map: low / medium / high, and what would raise it
```

"Vocabulary learned" matters beyond the verdict: adopting the literature's names is how the
team plugs into the community's knowledge from that day forward — and it makes every future
search cheaper.
