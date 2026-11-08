# competitor-gap-extractor: Cited Rival Weaknesses

Every weakness this mod reports about a rival is backed by a public source the reader can open. A weakness from memory is not a finding.

## Rules

1. **Name one closest rival.** Pick the direct competitor the buyer would most likely compare against, and say why it is the closest. Do not average across several.
2. **Cite every claim.** Each weakness carries the URL of a public source (docs, pricing page, changelog, a public review) and one line on what that source shows.
3. **Reject memory.** A claim the step cannot source is listed as an open question, not a gap.
4. **Extract causes, not symptoms.** Each weakness names the cause in the rival's architecture, pricing model, UX or scope that produces it. A symptom with no cause is not yet a gap.
5. **Score defensibility on five axes.** Hard technology, workflow lock-in, speed, cost and UX. Each axis is scored low, medium or high, with the reason in one line.
6. **Score the user pain, then order by both.** Rate how much each weakness hurts the user: low, medium or high, with the reader's situation that makes it hurt. A severe gap the rival can fix in a release ranks below a moderate one it cannot.

## Output

A `RivalGapsMatrix`: one row per gap, with the rival, the cause, the sources, the pain, and the defensibility on each axis.
