---
name: ceet-sub-agent-orchestration
description: Orchestrates complex CEET executions by delegating independent role-based tasks to sub-agents, each bound to one CEET role's pack, validating every handoff against the OrchestrationPlan and SubAgentResult contracts, and consolidating the validated outputs into one delivery. Use when a task needs several CEET roles (for example backend, frontend and SRE reviews of the same change) and ceet-autodiscover or the user chose parallel sub-agents.
---

# CEET Sub-Agent Orchestration

Use this skill when a task is complex enough to benefit from specialized parallel execution.

## Purpose

Act as the coordinator that plans, delegates, validates, and merges work produced by multiple specialized sub-agents.

## Handoff contracts

The orchestrator passes work via two JSON contracts documented in
[`references/contracts.md`](references/contracts.md):

- `OrchestrationPlan` — what the orchestrator hands off.
- `SubAgentResult` — what each sub-agent returns.

Both are validated deterministically by
[`scripts/validate_handoff.py`](scripts/validate_handoff.py). Run it
before dispatch (plan validation) and after every sub-agent returns
(result validation). Paths are relative to this skill's directory:

```bash
python3 scripts/validate_handoff.py --plan plan.json
python3 scripts/validate_handoff.py --result result.json
```

It needs `ceet-core` 2 installed beside this skill. A binding's pack path is relative to the
project root: `--project`, else `$CLAUDE_PROJECT_DIR`, else the git top level, else the current
directory.

A non-zero exit means the payload violates the contract; the
orchestrator must stop instead of merging partial output.

## Mandatory workflow

1. **Assess orchestration fit**
   - Confirm the task contains multiple specialized roles or workstreams.
   - Prefer independent sub-tasks to avoid conflicts.

2. **Plan role-based decomposition**
   - Define explicit sub-agents by role.
   - Assign each one a clear, bounded scope, input, and expected output.
   - Ensure no sub-agent depends on another sub-agent's in-flight edits.

3. **Bind CEET per sub-agent**
   - Bind each task to its role's pack in the project (`ceet-autodiscover` lists them, with the path
     that goes in `binding.pack`) and to the **one** artifact that matches the sub-task: an agent,
     skill, command or rule file of that pack (`binding.artifact`).
   - The sub-agent loads the pack's `core.md` plus that artifact, and nothing else of the pack, as
     the [pack contract](../ceet-core/references/pack-contract.md) says under "Loading". The validator
     checks the binding against the pack on disk.
   - If a role has no pack, bind the sub-agent to an example pack when one exists (no per-role manual
     confirmation), set `binding.example: true`, and name it in the execution trace as an example,
     not the user's profile.

4. **Conflict prevention strategy**
   - Default: split work into independent tasks operating on non-overlapping files.
   - If full independence is not possible:
     - Isolate each sub-agent in temporary folders/workspaces.
     - Let orchestrator reconcile and combine results after execution.

5. **Execute sub-agents**
   - Dispatch all defined role tasks.
   - Track outputs and execution status per role.

6. **Validate and consolidate (orchestrator responsibility)**
   - Review outputs for consistency, quality, and alignment with user goal.
   - Resolve overlaps or contradictions.
   - Merge into a single coherent final result.

7. **Return final integrated delivery**
   - Provide consolidated output plus a short execution trace (roles, tasks, merge decisions).

## Guardrails

- Never delegate without explicit role boundaries.
- Never allow uncontrolled overlapping edits between sub-agents.
- Never skip orchestrator validation before final output.
- Always prefer deterministic merge criteria over ad-hoc combination.
