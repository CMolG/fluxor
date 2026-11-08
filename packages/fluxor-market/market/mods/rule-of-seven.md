# rule-of-seven: Fixed-Count Strategy

Every market strategy this mod governs is held to one count. The count comes from the project's `rule-of-seven.json` config (`count`, default 7). It is the only place in the market that names the number, so a project changes the strategy's breadth in one file.

## Rules

1. **Exactly N rival gaps.** The gap matrix holds exactly `count` gaps. Fewer is a gap in the research; more is a list, not a strategy. Do not pad the matrix to reach the count.
2. **Exactly N capabilities.** The capability spec holds exactly `count` capabilities, each answering one gap or one buyer objection.
3. **Exactly N touchpoints.** The landing page holds exactly `count` touchpoints, one per capability, in the order the reader meets them.
4. **One driver per touchpoint, each driver used once.** Every touchpoint maps to one driver from the table below. A driver that appears twice is a sign that two touchpoints say the same thing: merge them, or find the driver the second one really answers.
5. **One conversion goal.** All touchpoints build toward the single action named in the core-vision note. A touchpoint that serves a different goal is rewritten or removed.
6. **The count is refused above the drivers.** A configured `count` above the number of drivers in the table is an error, reported before any work starts. Do not invent drivers to reach it.

## The drivers

| Driver | Meaning for the reader |
| --- | --- |
| Speed | Time to value: the outcome arrives sooner than the rival's. |
| Money saved | ROI: the reader keeps money or avoids spending it. |
| Cognitive relief | Zero setup: less thinking, fewer decisions, nothing to learn first. |
| Unfair advantage | Leverage: the reader gets an edge the rival cannot easily match. |
| Risk removed | Reliability: a failure, a lock-in or an exposure the reader no longer carries. |
| Ecosystem synergy | The capability works better with what the reader already uses. |
| Status | Future-proofing: the reader is seen as ahead, and stays ahead. |

## How to apply

- Read `count` from the project's config before writing the first gap. When the config is absent, use the default.
- State the count and the drivers used in the output, so a reader can check the matrix against the rule.
- When a step cannot fill the count with evidence, it says so and lists what is missing. It does not invent a gap to close the gap in the output.
