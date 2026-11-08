# Discovery signals — finding candidates in a codebase

Phase 1 is archaeology, not judgment. The goal is to surface everything that *might* be a
discovery and write it down; phases 2–3 decide what it actually is. Err toward inclusion here
— a candidate costs three sentences in the inventory, a missed contribution costs everything.

## Where discoveries hide

Discoveries almost never sit in a file called `novel_algorithm.py`. They hide in the places
where the team fought reality and won (or lost informatively):

### 1. Reimplementation scars
Code that rebuilds something a library "should" have provided. Search for comments and commit
messages like "nothing handled", "no library supports", "had to roll our own", "X doesn't work
when". Each one marks a spot where the team walked past the edge of the available state of the
art. Sometimes they walked past it because they didn't find the right tool (→ known art,
still useful to learn); sometimes because the tool genuinely doesn't exist (→ candidate).

### 2. Workaround markers and anomaly comments
`HACK`, `XXX`, `FIXME` that never got fixed because the hack *works*, "counterintuitively",
"for some reason", "don't reorder these lines", "this shouldn't be faster but it is".
An unexplained anomaly the team routed around and stabilized is often an empirical discovery
with the theory still missing. The theory is the paper.

### 3. Numbers that surprised someone
Internal benchmarks that beat the expected complexity class, latency that degrades *less* than
queueing theory predicts, memory that stays flat where it should grow. Ask for the benchmark
history: "which numbers made you re-run the benchmark because you didn't believe them?"
Surprise is the strongest single research smell.

### 4. Cross-domain imports
A technique imported from a foreign field and made to work: a compiler trick in a web app,
a database technique in a game engine, a control-theory idea in an autoscaler, a bioinformatics
structure in log processing. The candidate is rarely the imported technique itself (that's
known art in its home field) — it's the **transfer plus the integration work** that made it
viable in the new domain, and the evidence that it helps there.

### 5. Problem reframings
The team stopped solving the problem everyone solves and solved a different one that made the
original trivial. These are easy to miss because the resulting code looks *simple*. Signal:
"we realized we didn't actually need to..." in ADRs, PR descriptions, or retro notes.
Reframings are disproportionately publishable because they transfer to everyone who still
solves the hard version.

### 6. Home-grown abstractions, protocols and invariants
Internal DSLs, wire protocols, scheduling policies, consistency rules that map to nothing
standard. Also **tests that encode undocumented behavior**: an assertion for an edge case that
no documentation anywhere mentions means the team discovered that edge case empirically.
A test suite is a catalog of hard-won knowledge; read it as literature.

### 7. Documented dead ends
Branches, ADR "rejected alternatives" sections, retro notes about approaches that failed.
"We proved X doesn't work under conditions Y" is a legitimate candidate — negative results
save the whole community from re-running the same failure, and there are venues for them.

### 8. Configuration archaeology
Non-default settings with comments explaining pain: a tuned kernel parameter, a bizarre
timeout value, a retry policy with oddly specific constants. Each encodes an empirical finding
about how a system actually behaves versus how it's documented to behave.

## The developer interview

The code records *what*; only people remember *why*. Interview whoever lived through the work.
Highest-yield questions, in rough order:

1. **"What did you build yourself because nothing you found actually worked?"** — the single
   best question. It jumps straight to reimplementation scars and their reasons.
2. "What took 5× longer than the estimate, and what made it hard?" — difficulty concentration
   marks either missing state of the art or a fight with an undocumented reality.
3. "What would you not know how to google?" — if the developer can't name the concept, either
   the vocabulary gap is theirs (→ phase 2 will find the name) or the concept has no name yet
   (→ strong candidate).
4. "Which result made you re-run the measurement because you didn't believe it?"
5. "What do you explain to every new teammate because it's written nowhere?" — undocumented
   institutional knowledge is a candidate pool.
6. "What did you try that failed, and do you know *why* it failed?" — dead ends with
   understood causes are negative-result candidates.
7. "If you could ask a researcher one question about this system, what would it be?" — the
   open questions the team carries are research topics by definition.

Keep it to 20 minutes per person. You're collecting pointers, not conclusions.

## Scanning large repos and monorepos

A full audit of a large codebase can't read everything. Prioritize by signal density:

- **Grep the markers first**: the comment vocabulary from sections 1–2 above, plus "faster",
  "instead of", "workaround", "apparently", "somehow". Rank files by marker density.
- **Sort PRs by discussion length.** Long review threads mark contested, non-obvious
  decisions. Read the top 10.
- **Read every ADR**, especially rejected-alternatives sections.
- **Diff against convention**: places where the codebase deviates from the framework's or
  ecosystem's idiomatic solution usually have a reason; the reason is sometimes a candidate.
- **Benchmark and load-test directories** — read the results and their history, not just the
  harness.
- In AI-assisted codebases, weight *human-authored* deviations higher: the spots where a human
  overrode or rewrote generated code mark exactly the places where available knowledge (which
  the model represents) wasn't good enough.

## Writing the candidate inventory

One entry per candidate:

```
### [Short name]
- What: 2–3 sentences, plain language, no claims yet
- Where: paths / PR / ADR
- Problem it addresses: one sentence
- Why it might be novel: the signal that flagged it (from the list above)
- Deep dive: yes / later / no
```

Rules of thumb:
- **Cap sprint scans at ~5 candidates.** Triage beats completeness; the log accumulates.
- Describe without evaluating. "Might be novel because we couldn't name it" is a fine reason;
  "is definitely novel" is a phase-3 sentence.
- If two candidates share a root cause, merge them — the root cause is the real candidate.
- Check the radar log first: a candidate already evaluated is only reopened if the code or the
  state of the art changed.
