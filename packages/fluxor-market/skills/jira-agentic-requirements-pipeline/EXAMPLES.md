# Worked examples

Three end-to-end runs that show how the pipeline handles tickets at
different ambiguity levels. The fixtures live in this skill's
[`tests/fixtures/`](tests/fixtures/) folder in the repository and are the
same ones used by the test suite, so the outputs are reproducible. Tests are
not installed with the skill: run these examples from a checkout of the source
repository, or point `--input` at a ticket export of your own.

> All examples run from this skill's directory and assume the CLI variable is
> set:
>
> ```bash
> CLI=scripts/jira_pipeline_cli.py
> ```

---

## Example 1 — A clean ticket → `READY_FOR_BASE_BRANCH`

Source: [`tests/fixtures/issue_tight.json`](tests/fixtures/issue_tight.json).
The ticket specifies scope, success/error/expired/cancelled states,
limits, communications, audit trail, rollout, and acceptance.

```bash
python3 "$CLI" discovery --input tests/fixtures/issue_tight.json --output analysis.json
python3 "$CLI" generate-questions --input analysis.json --output questions.json
# Answer all required questions (interactive) or synthesize answers in CI
python3 "$CLI" collect-input --input questions.json --state-file state.json --non-interactive
python3 "$CLI" resolve-contract --questions questions.json --answers state.json --output contract.json
python3 "$CLI" base-branch-plan --analysis analysis.json --contract contract.json --output plan.json
```

What you get:

- `analysis.ambiguityLevel.level` → `LOW` (constraint density `10.53`:
  ten constraint keyword occurrences in 95 words, no ambiguity markers).
- `analysis.missingBusinessDecisions` → `[]`. The ticket already
  describes every category the rule-based detector tracks.
- `plan.status` → `READY_FOR_BASE_BRANCH`, `confidence: 0.90`.
- `plan.proposedBranchName` → `ai/demo-100-base`. Note: the CLI does not
  create the branch — the engineer creates it after reviewing the plan.

---

## Example 2 — A near-empty ticket → `QUESTIONS_ONLY`

Source: [`tests/fixtures/issue_empty.json`](tests/fixtures/issue_empty.json).
The ticket has only a title (`"Approval flow"`) and a description of
`"TBD"`.

```bash
python3 "$CLI" discovery --input tests/fixtures/issue_empty.json --output analysis.json
python3 "$CLI" generate-questions --input analysis.json --output questions.json
```

The discovery output shows what is missing:

```json
{
  "schemaVersion": "1.2.0",
  "ambiguityLevel": {
    "level": "HIGH",
    "constraintDensity": 0.0,
    "ambiguityMarkers": 33.333,
    "signals": {
      "constraintKeywords": [],
      "ambiguityMarkers": ["tbd"],
      "constraintKeywordCounts": {},
      "ambiguityMarkerCounts": {"tbd": 1}
    }
  },
  "missingBusinessDecisions": [
    "acceptance_criteria", "auditability", "communications",
    "compliance", "error_behavior", "expiration", "legacy_compatibility",
    "limits", "rollout", "scope", "success_behavior", "support_behavior"
  ]
}
```

Generated questions cover:

- The 4 baseline P0 templates (BO-1, FS-1, BR-1, SL-1).
- 6 signal-driven templates ranked by how strongly each one matches the
  missing decisions (UX-1, AC-1, CP-1, CM-1, DR-1, LC-1).
- One optional question, the P3 out-of-scope template (PZ-1): the ticket
  touches no category with a P2 template.

Stop here. Do not run `base-branch-plan` until the business has answered
the required questions.

---

## Example 3 — Ambiguity markers despite long text → `QUESTIONS_ONLY`

Source: [`tests/fixtures/issue_ambiguous.json`](tests/fixtures/issue_ambiguous.json).
The text is reasonably long but every other sentence contains a marker
(`TBD`, `we should`, `maybe`, `not sure`, `pending`, `unknown`,
`alternatively`, `to be defined`).

```bash
python3 "$CLI" discovery --input tests/fixtures/issue_ambiguous.json --output analysis.json
```

The new ambiguity-level rule rejects "long therefore specific":

```json
{
  "ambiguityLevel": {
    "level": "HIGH",
    "constraintDensity": 0.0,
    "ambiguityMarkers": 17.647,
    "signals": {
      "constraintKeywords": [],
      "ambiguityMarkers": ["tbd", "we should", "or", "alternatively", "maybe", "not sure", "to be defined", "pending", "unknown"],
      "constraintKeywordCounts": {},
      "ambiguityMarkerCounts": {"tbd": 2, "we should": 2, "or": 1, "alternatively": 1, "maybe": 3, "not sure": 1, "to be defined": 1, "pending": 2, "unknown": 2}
    }
  }
}
```

Both the constraint density and the marker density are reported, and each
counts every occurrence (15 markers in 85 words here), so downstream tooling
can react to the *shape* of the ambiguity instead of treating every HIGH the
same.

---

## Customizing question budgets

Two CLI flags control how the question selector splits its slots:

```bash
python3 "$CLI" generate-questions \
  --input analysis.json \
  --output questions.json \
  --baseline-budget 3 \
  --signal-budget 7
```

The `baseline-budget` reserves slots for the universally required P0
templates (BO-1 / FS-1 / BR-1 / SL-1, picked deterministically). The
`signal-budget` is filled with templates whose `signals` array
intersects the analysis' `missingBusinessDecisions`, ranked by match
strength. If the signal pool underfills, remaining P0/P1 templates
overflow into the empty slots so the pipeline never under-asks.
