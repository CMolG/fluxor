# rule-of-seven-vanguard: Fixed-Count Market Strategy

This flow turns a product's mind map and its rivals' weaknesses into one market strategy: the gaps a rival leaves open, the capabilities that close them, the copy that sells each capability, a page that paces that copy, and an audit that sends weak items back. Every step is held to the count the `rule-of-seven` mod sets.

## Notes it reads

| Note type | Meaning | Read by |
| --- | --- | --- |
| `CoreVision` | The root product thesis and the target audience. | Every step, as read-context. |
| `CompetitorWeakness` | Observed complaints or limits in rival tools. | `rival-gap-analysis` as primary input; `red-team-audit` as read-context. |
| `RawFeatureIdea` | Unfiltered product ideas from the user's brain dump. | `product-moat-architecture` as primary input. |
| `BuyerObjection` | Reasons a prospect hesitates to buy or switch. | `landing-micro-sales` and `red-team-audit` as primary input. |

A `primary-input` note drives a step's work. A `read-context` note only informs it. When a bound note type has no notes, the step researches it from public sources and says so in its output.

## Steps and artifacts

1. **`rival-gap-analysis`** (competitive-intelligence-strategist). Writes a `RivalGapsMatrix`: one row per gap, with the rival, its cause, its sources, the user pain, and the defensibility on each axis.
2. **`product-moat-architecture`** (asymmetric-product-architect). Writes a `ProductCapabilitiesSpec`: one entry per capability, with its user outcome, the rival gap it answers, and whether the product already has it, with evidence.
3. **`landing-micro-sales`** (conversion-copywriter). Writes a `MicroSalesCopyDeck`: one micro-sale per capability, each with its hook, mechanism, asymmetric proof and micro-close.
4. **`landing-ux-blueprint`** (conversion-ux-architect). Writes a `LandingUXBlueprint`: one section per copy touchpoint, with its layout pattern, its primary element and the states of its interactive blocks.
5. **`red-team-audit`** (red-team-auditor). Writes an `AuditValidationReport`. When an item fails, the flow loops back to step 2, at most twice, so the failing capabilities are rewritten.

## The artifacts

Each artifact is a JSON document. Field names are fixed so the next step can read the previous one.

- **`RivalGapsMatrix`**: `{ "rival": string, "gaps": [{ "id": string, "cause": string, "sources": [{ "url": string, "shows": string }], "pain": "low" | "medium" | "high", "defensibility": { "hardTech": ..., "workflowLockIn": ..., "speed": ..., "cost": ..., "ux": ... }, "productCovers": boolean, "evidence": string }] }`

  Example row: `{ "id": "gap-1", "cause": "pricing locked to annual seats", "sources": [{ "url": "https://example.com/pricing", "shows": "annual-only plans" }], "pain": "high", "productCovers": false }`

- **`ProductCapabilitiesSpec`**: `{ "capabilities": [{ "id": string, "outcome": string, "answersGap": string, "productHas": boolean, "evidence": string }] }`

  Example: `{ "id": "cap-1", "outcome": "a team switches tools in one afternoon", "answersGap": "gap-1", "productHas": false, "evidence": "none in the repository" }`

- **`MicroSalesCopyDeck`**: `{ "blocks": [{ "capabilityId": string, "hook": string, "mechanism": string, "proof": string, "microClose": string }] }`

  Example: `{ "capabilityId": "cap-1", "hook": "Still paying for seats you never fill?", "mechanism": "Pay for the hours you use.", "proof": "The rival bills by the seat; we bill by the hour.", "microClose": "Start on your next invoice." }`

- **`LandingUXBlueprint`**: `{ "sections": [{ "touchpoint": string, "pattern": string, "primaryElement": string, "states": { "loading": string, "empty": string, "error": string, "success": string } }] }`

  Example: `{ "touchpoint": "cap-1", "pattern": "before-and-after slider", "primaryElement": "the slider", "states": { "loading": "skeleton", "empty": "sample data", "error": "retry", "success": "result" } }`

- **`AuditValidationReport`**: `{ "items": [{ "id": string, "verdict": "pass" | "fail", "failedTest": "evidence" | "duplicate" | "clarity" | null, "rewrite": string | null }] }`

  Example: `{ "id": "cap-2", "verdict": "fail", "failedTest": "duplicate", "rewrite": "merge into cap-1; both promise the same hour-based billing" }`

## The audit's three tests

1. **Evidence:** the claim has a cited source, or the product's own evidence.
2. **Duplicate:** the item solves a problem no other item solves.
3. **Clarity:** a non-technical reader understands the item in a few seconds.

A failing item carries a rewrite direction. The loop returns the item to step 2, at most twice; an item still failing after the second pass is reported as failed, not hidden.

## Limits

The flow sets no model, effort or temperature. Each role's own `betterOn` and the project's role matrix choose those. The count lives in the `rule-of-seven` mod's config, never in the prompts.
