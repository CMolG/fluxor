# Dissemination — sharing findings without leaking IP or manufacturing hype

Phase 5 turns a verdict into community impact. Order matters: IP gate → channel → package →
promote. Skipping the gate can cost a client relationship or a lawsuit; skipping the honest
packaging costs the credibility that makes future findings worth listening to.

## The IP gate (always first)

Answer in writing before any public word:

1. **Who owns the work?** Client contract, employment agreement, or your own time and
   equipment? Contractor and freelance agreements routinely assign IP to the client —
   including "inventions" — even when the technique feels like yours.
2. **Is anything under NDA?** The technique may be shareable while the context (client name,
   domain, data, scale, incident) is not.
3. **Can the technique be abstracted from the artifact?** The operating rule: **publish the
   technique, never the client's code.** Clean-room reimplement the mechanism, demonstrate on
   synthetic or public data, strip every identifying detail (domain terms, metric baselines
   that fingerprint the client, architecture diagrams that mirror theirs).
4. **Written clearance** whenever the work was done for a client or employer — a short email
   ("I'd like to publish the general technique, abstracted as attached, no reference to you")
   with an explicit yes. Many clients say yes; the ask itself builds trust.
5. **Patent decision before publication.** Publishing creates prior art that permanently
   destroys patentability — yours and everyone else's. That is sometimes exactly the goal
   (**defensive publication**: publish precisely so nobody can patent it and the technique
   stays free), but it must be a decision, not an accident. If a patent might matter, that
   conversation happens before the preprint, not after.
6. **License the release.** If code ships, pick the license deliberately (MIT/Apache-2.0 for
   adoption, AGPL for reciprocity) and check it against dependencies' licenses.

## Choosing the channel

Match channel to verdict and evidence — publishing above your evidence level is the main way
engineering teams burn credibility:

| Verdict | Channels, in order of fit | Notes |
|---|---|---|
| Known art | Internal doc adopting standard terminology; optionally an educational blog post ("we rediscovered X — here's the literature") | Rediscovery posts perform honestly and well; the community respects "TIL" framing far more than false novelty. |
| Incremental | Engineering blog post; upstream OSS contribution (the improvement belongs in the library you improved); internal doc | Workshop paper only with E2+. Upstreaming is often the highest-impact move: everyone downstream inherits it. |
| Novel combination | Experience report (industry tracks: ICSE SEIP, VLDB industrial, USENIX ATC, SREcon); applied/conference paper; conference talk; OSS release with a paper-grade README | Experience reports are underrated: venues actively want rigorous accounts from production. |
| Novel contribution | arXiv preprint immediately (timestamps priority and invites feedback), then the owning community's venue; OSS release | Check the target venue's preprint/double-blind policy before posting — most CS venues allow prior arXiv posting, a few restrict it. Some arXiv categories require endorsement for first-time submitters; budget a few days. |
| Promising-unproven | Nothing public | Write the MPU into the radar log; publish after the experiment, not before. |

Cross-cutting options at any level ≥ incremental: a talk at a meetup or conference (talks
tolerate earlier-stage work than papers), and a well-packaged OSS release (for many practical
techniques, a maintained repo with benchmarks *is* the publication of record).

## The research note template

The universal packaging unit. It works as an arXiv preprint skeleton, a blog post, a
paper-grade README, or a talk outline — same bones, different dress:

```
# [Technique name — the standard vocabulary if it exists, a plain descriptive name if not]

**Claim (one falsifiable sentence).** X improves Y by Z under conditions W.

## Problem
Who has it, why it matters, why the obvious approaches fall short. Two paragraphs.

## Nearest prior art — and the delta
The 2–4 closest works, linked, each in one honest line. Then the delta: what this does that
the nearest neighbor cannot. This section IS the contribution statement; write it first.

## How it works
Mechanism, minimal example, key design decisions and why.

## Evidence
Setup, baselines (and how they were tuned), results, ablations. Report where it loses.

## Limitations
Where it breaks, what wasn't tested, which contexts it probably doesn't transfer to.
Written by you before a reviewer writes it for you.

## Reproduce it
Code, data or generator, seeds, exact steps. If readers can't re-run it, scale every claim
down one notch.
```

If a content-writing or engagement-judging skill is installed, hand it the finished note when
adapting it into platform content — this skill owns the substance and the honesty; that one owns
the hook and the engagement. Without one, adapt the note yourself, keeping every claim at the
level the evidence supports.

## Promoting without hype

The goal of promotion is to reach the people who have the problem, with claims they can
verify. Rules that keep the radar's credibility compounding:

- **Lead with the delta, not the drama.** "Unlike [nearest neighbor], this handles X" beats
  "revolutionary new approach" with every audience that matters.
- **Cite generously and link the nearest neighbors prominently.** Citations are credibility,
  not concessions — a writeup that maps its own neighborhood signals it was searched, and the
  neighbors' authors are the likeliest expert amplifiers you have.
- **Claims match evidence level, everywhere.** The tweet obeys the same E-gate as the paper.
  If the evidence is E2 on one workload class, the headline doesn't say "always".
- **Invite falsification.** "We'd love counterexamples" plus a runnable repo turns critics
  into free reviewers and converts every survived attack into stronger evidence.
- **Post where the owning community lives** — the venue, subreddit, Discord or mailing list of
  the nearest neighbor's field — before generic channels. Ten readers with the problem beat
  ten thousand without it.
- **Report the kill honestly if it comes.** If someone surfaces prior art phase 2 missed,
  update the piece, credit them, and log the vocabulary in the radar log. Handled openly,
  being corrected in public *raises* long-term credibility; handled defensively, it ends it.

## After publication

- Log the outcome in `RESEARCH_RADAR.md`: channel, link, reception, corrections, new prior
  art surfaced by readers.
- Feed reviewer/community feedback back through phase 3 — a verdict can move in both
  directions after contact with the world.
- If the finding seeded a research line, open its own entry: the open questions from the
  interview protocol are the natural next candidates.
