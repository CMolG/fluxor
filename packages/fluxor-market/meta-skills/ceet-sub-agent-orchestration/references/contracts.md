# Orchestration contracts

Every payload carries a top-level `schemaVersion` that follows SemVer: **patch** for clarifications,
**minor** for backward-compatible additions (a new optional field, a new enum member), **major** for
a rename, a removal, or a changed meaning. The validator accepts exactly the version it implements.

The `ceet-sub-agent-orchestration` skill enforces two contracts before
dispatching work and after each sub-agent returns. Validation is
deterministic and runs through
[`scripts/validate_handoff.py`](../scripts/validate_handoff.py).

## `OrchestrationPlan`

```json
{
  "schemaVersion": "2.0.0",
  "planId": "plan-2026-05-07-001",
  "goal": "Refactor the checkout flow with parallel role-scoped reviews",
  "tasks": [
    {
      "id": "T1",
      "role": "ceet-backend-engineer",
      "scope": "Audit the order-service migration plan",
      "expectedArtifacts": ["report"],
      "dependsOn": [],
      "binding": {"pack": ".harness/packs/backend-engineer-alex", "artifact": "agents/code-reviewer.md"}
    },
    {
      "id": "T2",
      "role": "ceet-frontend-engineer",
      "scope": "Audit the checkout component for accessibility",
      "expectedArtifacts": ["report"],
      "dependsOn": [],
      "binding": {"pack": ".harness/packs/frontend-engineer-sam", "artifact": "rules/accessibility.md"}
    },
    {
      "id": "T3",
      "role": "ceet-devops-sre",
      "scope": "Wire alerts for the new error budget",
      "expectedArtifacts": ["diff", "report"],
      "dependsOn": ["T1"],
      "binding": {
        "pack": "skills/ceet-impersonator/examples/devops-sre-sample",
        "artifact": "agents/incident-responder.md",
        "example": true
      }
    }
  ]
}
```

Constraints:

- `tasks` must be non-empty, with unique `id` values.
- Each task's `expectedArtifacts` must be non-empty.
- `dependsOn` may reference earlier tasks only — forward dependencies
  are rejected.
- Each task carries a `binding` to the pack its sub-agent works under (pack contract v2, in
  `ceet-core` 2). The sub-agent loads the pack's `core.md` plus `binding.artifact`, and nothing
  else of the pack:
  - `pack` is the pack's folder, as `ceet-autodiscover` reports it: relative to the project root,
    or absolute. It must hold a `core.md` (a rendered pack), and the role it was made for (its
    `cognitive-profile.json` `role`, else its `pack.json` `metaSkill`) must be the task's `role`.
  - `artifact` is one file of that pack under `agents/`, `skills/`, `commands/` or `rules/`, the one
    that matches the task's scope.
  - `example` (optional, default `false`) is `true` when the pack is an example or simulated pack
    of someone else, not the user's own; the execution trace names it as such.

## `SubAgentResult`

```json
{
  "schemaVersion": "1.0.0",
  "planId": "plan-2026-05-07-001",
  "taskId": "T1",
  "role": "ceet-backend-engineer",
  "status": "completed",
  "artifacts": [
    {"path": "reports/T1-backend-audit.md", "kind": "report"}
  ],
  "summary": "Migration plan is safe under the documented dual-write window."
}
```

Constraints:

- `status` is one of `completed | failed | skipped`.
- `completed` requires at least one entry under `artifacts`.
- `failed` requires a non-empty `error` field.
- Artifact `kind` is one of `file | diff | report | decision`.

The orchestrator must reject any plan or result that fails validation
and stop the run rather than merge partial output.
