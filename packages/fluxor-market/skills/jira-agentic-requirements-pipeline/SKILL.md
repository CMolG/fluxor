---
name: jira-agentic-requirements-pipeline
description: Run a two-phase agentic requirements pipeline connected to Jira (Requirement Discovery and Base Branch Generation). Use when a team wants to analyze Jira tickets, detect business ambiguity, generate structured non-technical business questions, collect business answers from CLI with resumable session state, resolve a functional contract, and prepare a constrained base-branch plan with traceability and guardrails.
---

# Jira Agentic Requirements Pipeline

Execute this workflow to convert ambiguous Jira tickets into actionable engineering inputs without inventing product decisions.

## Quick start

`CLI` is relative to this skill's directory. An artifact path left out lands at the project root
(`$CLAUDE_PROJECT_DIR`, else the git top level, else the current directory), never in this skill's
folder; a path given is used as given.

```bash
export JIRA_BASE_URL="https://example.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="<your-jira-api-token>"

CLI=scripts/jira_pipeline_cli.py

python3 "$CLI" fetch-issue DEMO-1 --output issue.json
python3 "$CLI" discovery --input issue.json --output analysis.json
python3 "$CLI" generate-questions --input analysis.json --output questions.json
python3 "$CLI" collect-input --input questions.json --state-file .jira_requirement_state.json
python3 "$CLI" resolve-contract --questions questions.json --answers .jira_requirement_state.json --output contract.json
python3 "$CLI" base-branch-plan --analysis analysis.json --contract contract.json --output plan.json
```

Output files at each step:

| Step | Produces | Used by next step |
|---|---|---|
| `fetch-issue` | `issue.json` (TicketSnapshot) | `discovery` |
| `discovery` | `analysis.json` (TicketAnalysis) | `generate-questions`, `base-branch-plan` |
| `generate-questions` | `questions.json` (BusinessQuestionSet) | `collect-input`, `resolve-contract` |
| `collect-input` | `.jira_requirement_state.json` (resumable) | `resolve-contract` |
| `resolve-contract` | `contract.json` (FunctionalContract) | `base-branch-plan` |
| `base-branch-plan` | `plan.json` (BaseBranchPlan) | engineer review |
| `request-human` | `request_human.json` (RequestHumanDraft) | a backlog's `requestHuman` wall |

## Mandatory flow (run in order)

1. Fetch Jira issue with `scripts/jira_pipeline_cli.py fetch-issue`.
2. Run requirement discovery with `scripts/jira_pipeline_cli.py discovery`.
3. Generate business questions with `scripts/jira_pipeline_cli.py generate-questions`.
4. Collect business answers in terminal with `scripts/jira_pipeline_cli.py collect-input`.
5. Resolve functional contract with `scripts/jira_pipeline_cli.py resolve-contract`.
6. Build base-branch plan with `scripts/jira_pipeline_cli.py base-branch-plan`.

If required answers are missing, stop in phase 1 and do not plan implementation:
`request-human` turns the open questions into a wall card for the person who decides.

## With a backlog, on any tracker

The question catalog, the priorities and the contract are not Jira's. The `backlog` skill hands
off to this pipeline at its "Is the card ready?" step, on whatever tracker it works:

1. Write the card as a `TicketSnapshot` (`issue.json`); `references/contracts.md` maps every
   field from a tracker card. `fetch-issue` is only for Jira.
2. `discovery`, then `generate-questions`, as above.
3. `request-human --questions questions.json`: a `requestHuman` draft (title, why, steps,
   doneWhen, unblocks, category) whose steps are the open questions. The backlog raises it as a
   wall that blocks the card. `"ready": true` means there is nothing to ask.
4. Once the person answers on the card, write the answers into the state file, run
   `resolve-contract`, and post the contract on the card as one comment
   (`references/contracts.md`, "On the card"). The backlog's action plan cites that comment.

With a backlog, `collect-input` (the terminal) and `base-branch-plan` are not used: the person
answers on the card, and the action plan replaces the base-branch plan.

## Decision rules

- Ask only functional/product/operations questions.
- Infer architecture and implementation details from repository patterns.
- Keep required questions small and prioritized (typically 5-10 per ticket).
- The selector reserves a baseline budget (default 4) for universally
  required P0 templates (objective / scope / rules / lifecycle) and a
  signal budget (default 6) for templates whose declared signals match
  the ticket's missing decisions. Tune via `--baseline-budget` and
  `--signal-budget`.
- Keywords and ambiguity markers match as whole words, with regular inflections
  ("only" never fires on "commonly"; "expire" matches "expired"), and the
  densities count every occurrence.
- Optional questions (`optionalFutureDecisions`, ids `O1`, `O2`, ...) are the P2
  templates whose category the ticket touches, then the P3 ones. They never
  block; ask them with `collect-input --include-optional` when the business has
  time, and `resolve-contract` records any that were answered.
- If inference confidence is low (`< 0.65`), generate questions only and request human review.
- Never auto-merge.

## Jira integration

Set environment variables:

- `JIRA_BASE_URL` (example: `https://company.atlassian.net`, no trailing slash needed)
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`

The CLI uses Jira REST API v3 and pages through the `/comment` endpoint
until every comment is fetched. Cap with `--max-comments` (default
`1000`); a stderr warning fires if the cap clipped the result.

## Three modes: rules, llm-augmented, hybrid

The pipeline keeps a deterministic rule-based core (free, offline,
reproducible) and lets the host model that invokes this skill augment
it. The skill never calls a model itself — the model executing the
skill is the one in your editor (Claude in Cursor, Claude Projects,
ChatGPT, Gemini, etc.). Three modes:

### 1. `rules` (default, no model required)

Run the six commands above. The rule-based inferencers in
`scripts/jira_pipeline_cli.py` produce every artifact deterministically
from keyword and density signals.

### 2. `llm-augmented`

After `discovery` the host model reads `analysis.json` and emits a
refinement patch as JSON. Allowed keys are exactly:

```
businessGoal, functionalEntities, userActions, possibleAffectedFlows,
explicitRequirements, missingBusinessDecisions, detectedCategories,
ambiguityLevel
```

Anything else is rejected. Save the patch (e.g. `suggestions.json`)
and merge it:

```bash
python3 "$CLI" merge-llm-suggestions \
  --analysis analysis.json \
  --suggestions suggestions.json
```

The merger:
- unions list-shaped fields with the rule-based output (so additions
  compound, deterministic core is never overwritten);
- replaces scalar fields;
- keeps the rule-based value of every accepted key under
  `_llmAugmentation.ruleBasedSnapshot.<field>` for provenance;
- lists the applied keys in `_llmAugmentation.acceptedKeys` and every key it
  did not apply (identity fields such as `issueKey` and `schemaVersion`
  included) in `_llmAugmentation.rejectedKeys`.

The output stays usable by `generate-questions` and `base-branch-plan`
without changes — both continue to consume `analysis.json`.

### 3. `hybrid`

Hybrid is just the orchestration: run `discovery` first, hand
`analysis.json` to the host model with the prompt in
[`templates/llm-augmentation-prompt.md`](templates/llm-augmentation-prompt.md),
merge the patch, then continue with the rest of the pipeline. The
deterministic baseline is always present; the model only refines.

## CLI mode without losing session state

For business input in terminal:

- Run `collect-input` with `--state-file`.
- State is persisted after each answer.
- If terminal closes or receives `Ctrl+C`, rerun and continue from the next pending question.
- Use `--non-interactive` to validate required completeness in CI or automation.
- Add `--include-optional` to also ask the optional questions after the required ones; an
  empty answer skips one.

## Artifact contracts

Every artifact emitted by the CLI carries a top-level `schemaVersion`
(currently `1.2.0`). See [`references/contracts.md`](references/contracts.md)
for the full shape of each artifact, the contract field of every catalog
category, and the versioning policy.

## References, examples, and troubleshooting

- Internal contracts: [`references/contracts.md`](references/contracts.md)
- Full business question catalog, prioritization and the shipped templates:
  [`references/question-catalog.md`](references/question-catalog.md)
- Worked examples (three end-to-end runs): [`EXAMPLES.md`](EXAMPLES.md)
- Common problems and fixes: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- Jira/report templates: `templates/`

## Guardrails

- Phase 1 is read-only for code changes.
- Phase 2 can prepare a base branch plan/report but must not merge.
- Keep mandatory traceability: ticket -> questions -> answers -> functional contract -> implementation plan.
