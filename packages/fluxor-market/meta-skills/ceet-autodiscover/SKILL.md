---
name: ceet-autodiscover
description: Use this skill when a task should be carried out as a specific person's CEET cognitive clone, i.e. "do this the way my cloned engineer/SRE/devops lead would", or when asked to check whether a project has a CEET pack for a role. It decides which ceet-<role> applies, verifies whether that role's pack is filled, and asks the user whether to initialize it, use an example pack, or proceed without CEET. Then it hands off to the role's pack, to sub-agent orchestration for multi-role work, or to the Jira requirements pipeline. Use it only to route and gate work that consumes a clone. Don't use it when the user directly asks to run a role's interview or to evaluate or measure a pack (fidelity, held-out decisions). Those go straight to the specific ceet-<role> or ceet-core skill. Don't use it for generic conventions, code review, or PRDs that don't mention CEET or a cloned persona.
---

# CEET autodiscover

Use this skill at the start of any execution that depends on a CEET context: work that should follow
a specific person's judgment as captured in a CEET pack.

Paths are relative to this skill's directory. The detector finds the `ceet-<role>` meta-skills
installed next to this skill (a role is a `ceet-*` folder with `interview/form.json`, routed by that
form's `routing.keywords`, so a new role needs no change here) and the packs in the project
(`.harness/packs/` by default; see the [pack contract](../ceet-core/references/pack-contract.md)). It
requires ceet-core 2 installed beside it. `evals/routing.json` measures how often a request reaches
the right role; its test prints the accuracy.

## Mandatory behavior

1. **Detect the target CEET (deterministic first, then judgment)**
   - Run `python3 scripts/detect.py --request "<user request>"`. It prints a JSON report:
     `detectedCEETs`, `initializedCEETs`, a `scoring` entry per role (matched keywords, the
     project's filled `packs`, `incompletePacks`, `examples`) and a `recommendation`
     (`primary`, `reason`, `needsInitialization`, `packs`, `examples`). Pure standard library, no
     model needed. `--project`, `--skills-dir` and `--packs-dir` override the defaults.
   - Use `recommendation.primary` as the starting point.
   - Override the script only if the user request names a CEET role or pack explicitly and the
     keyword matcher missed it — never silently disagree.
   - If `recommendation.primary` is `null`, stop and ask for clarification.

2. **Check CEET initialization**
   - A role is initialized when the project has a **rendered pack** for it (`recommendation.packs`):
     a `core.md` and none of the role's slots left. The role's own templates never count, and a
     pack listed under `incompletePacks` is a draft to finish, not a clone to use: `missing` names
     a file it still lacks (a pack with no `core.md` was never rendered: run ceet-core's
     `render_pack.py`), `unfilledSlots` the slots still open.
   - Never assume initialization state; take it from the report.

3. **If the CEET is not initialized**
   - Ask explicitly: **"Do you want to initialize this CEET now?"**
   - If the answer is **yes**: run the role's meta-skill (`../<role>/SKILL.md`): its interview
     produces the pack. Continue with that pack once it exists.
   - If the answer is **no**:
     - If `recommendation.examples` is not empty, ask: **"You do not have your own CEET
       initialized. Do you want to use an example CEET before continuing without CEET?"** Say what
       the example is: a sample or simulated pack of someone else (a simulated pack carries a
       Simulation Notice), not the user.
     - If the answer is **yes**: continue under that example pack's context.
     - If the answer is **no**, or there is no example: stop the CEET flow and tell the agent to
       look for another skill, because this one is not the right fit.

4. **If the CEET is initialized**
   - Load the pack as the pack contract says: `core.md` always, the one agent, skill, command or
     rule file that matches the task, and the three to five closest decisions of `examples/`
     (`bin/examples.py select`). Never `cognitive-profile.md` (it is for people) or `private/`.
   - Keep traceability from user request → CEET → pack → selected artifacts.

5. **Complex task orchestration option**
   - If planning reveals a complex task with distinct specialized roles, ask explicitly: **"Do you
     want us to launch different subagent roles to execute this in parallel and then consolidate
     it?"**
   - If the answer is **yes**, hand off to the `ceet-sub-agent-orchestration` skill.
   - If the answer is **no**, continue with single-agent CEET execution.

## Sub-agent orchestration compatibility

Autodiscover is compatible with the `ceet-sub-agent-orchestration` skill.

- Use orchestration only when work can be decomposed into independent role-based tasks or
  partitioned safely.
- If a required role has no pack, orchestration may bind that sub-agent to an example pack without
  asking per role, and must say so in its execution trace.
- The orchestrator validates all sub-agent outputs before final delivery.

## Jira compatibility

Autodiscover is compatible with the `jira-agentic-requirements-pipeline` skill.

- If the discovered context is Jira-driven, run autodiscovery first, then hand off to the Jira
  pipeline flow.
- If the Jira flow references a CEET that is not initialized, apply the same initialization question
  and branching rules.
- Preserve sequence integrity: autodiscover gating always runs before Jira requirement discovery
  actions.

## Guardrails

- Never skip CEET detection and initialization checks.
- Never assume initialization state.
- Never continue with a non-initialized CEET unless the user confirms initialization or explicitly
  chooses an example CEET.
- Never present an example or simulated pack as the user's own profile.
- If the user rejects both initialization and example CEET usage, explicitly report the mismatch
  and route to another skill.
- Never run sub-agent orchestration without clear task decomposition criteria.
