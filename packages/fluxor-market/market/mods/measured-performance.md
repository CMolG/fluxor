# measured-performance: Measured Speed & Query Plans Modifier

When this modifier is active, a performance claim carries a measurement and every query that is new or changed carries its plan. "Faster" and "indexed" are not evidence.

## Rules

1. **Before and after, same method.** A change made for performance records a before and an after number from the same measurement, with the command, the data volume and the environment named. No number, no claim.
2. **Every new or changed query has its plan.** The plan comes from the engine's `EXPLAIN` (or its equivalent) on realistic volume and shape, and is attached to the card. An unintended full scan of a large table is a defect.
3. **An index answers a plan.** A new index is added only for a plan that needs it, and its write cost is weighed in writing.
4. **Reads are bounded and batched.** No unbounded result set and no N+1: queries carry a limit or a page, and related reads are fetched together.
5. **A number answers only where it was measured.** A laptop or small-dataset result is labelled as such: it says which option is faster there, not how fast production will be.
6. **Speed never costs behavior.** The checks that passed before the change pass unchanged after it.

## Behavioral Overrides

- If no realistic data is available, the agent says so and states what the plan was read against instead of presenting it as representative.
- If a requirement can only be met by trading correctness for speed, the agent reports the conflict instead of silently choosing either.
- Pre-existing slow queries are reported, not rewritten, unless the change already touches them.
