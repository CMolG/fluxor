#!/usr/bin/env python3
"""Validate orchestration handoff artifacts against the documented schemas.

This script enforces the `OrchestrationPlan` and `SubAgentResult`
contracts. The orchestrator skill calls it before dispatching work
(plan validation) and again after every sub-agent returns (result
validation), so a malformed payload fails fast and never propagates.

A plan's tasks are bound to CEET packs (pack contract v2, in ceet-core 2,
which must be installed beside this skill): each sub-agent loads the pack's
`core.md` plus the one artifact its binding names, and the plan is checked
against the packs on disk.

Usage (paths are relative to this skill's folder):
    python3 validate_handoff.py --plan plan.json
    python3 validate_handoff.py --result result.json
    python3 validate_handoff.py --plan plan.json --results r1.json r2.json

A binding's pack path is relative to the project root: `--project`, else
`$CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel`, else the current
directory.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


PLAN_SCHEMA_VERSION = "2.0.0"
RESULT_SCHEMA_VERSION = "1.0.0"
CORE = Path(__file__).resolve().parents[2] / "ceet-core"
REQUIRED_CORE_MAJOR = "2"
# Pack contract v2, "Loading": the per-task artifacts a sub-agent may load besides `core.md`.
ARTIFACT_FOLDERS = ("agents", "skills", "commands", "rules")


def load_core():
    """ceet-core's `ceet_common`, or SystemExit(2) when ceet-core 2 is not installed beside us."""
    manifest = CORE / "skill.json"
    version = json.loads(manifest.read_text(encoding="utf-8")).get("version", "") if manifest.is_file() else ""
    if version.split(".")[0] != REQUIRED_CORE_MAJOR:
        print(f"error: ceet-sub-agent-orchestration requires ceet-core@{REQUIRED_CORE_MAJOR} next to it "
              f"({CORE}), found {version or 'none'}", file=sys.stderr)
        raise SystemExit(2)
    spec = importlib.util.spec_from_file_location("ceet_common", CORE / "scripts" / "ceet_common.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cc = load_core()


def _require(path: str, condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(f"{path}: {message}")


def pack_role(pack: Path) -> str | None:
    """The role a pack was made for: its profile's `role`, else its manifest's `metaSkill` id."""
    for name, key in (("cognitive-profile.json", "role"), ("pack.json", "metaSkill")):
        try:
            value = cc.read_json(pack / name).get(key)
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(value, str) and value:
            return value.split("@")[0]
    return None


def validate_binding(base: str, task: dict[str, Any], root: Path, errors: list[str]) -> None:
    """The task's pack exists, is a rendered v2 pack for the task's role, and holds its artifact."""
    binding = task.get("binding")
    if not isinstance(binding, dict):
        errors.append(f"{base}.binding: must be an object")
        return
    _require(f"{base}.binding.example", isinstance(binding.get("example", False), bool),
             "must be a boolean", errors)
    pack_path, artifact = binding.get("pack"), binding.get("artifact")
    _require(f"{base}.binding.pack", isinstance(pack_path, str) and pack_path,
             "must be a non-empty string", errors)
    _require(f"{base}.binding.artifact", isinstance(artifact, str) and artifact,
             "must be a non-empty string", errors)
    if not (isinstance(pack_path, str) and pack_path and isinstance(artifact, str) and artifact):
        return

    pack = (root / pack_path).resolve()
    if not pack.is_dir():
        errors.append(f"{base}.binding.pack: '{pack_path}' is not a folder (relative to {root})")
        return
    if not (pack / "core.md").is_file():
        errors.append(f"{base}.binding.pack: '{pack_path}' has no core.md (render it with ceet-core's render_pack.py)")
    role = pack_role(pack)
    if role and isinstance(task.get("role"), str) and role != task["role"]:
        errors.append(f"{base}.binding.pack: '{pack_path}' is a {role} pack, the task's role is {task['role']}")

    parts = PurePosixPath(artifact).parts
    if PurePosixPath(artifact).is_absolute() or ".." in parts or len(parts) < 2 or parts[0] not in ARTIFACT_FOLDERS:
        errors.append(f"{base}.binding.artifact: '{artifact}' must be a file under one of "
                      f"{'/, '.join(ARTIFACT_FOLDERS)}/ in the pack")
    elif not (pack / artifact).is_file():
        errors.append(f"{base}.binding.artifact: '{artifact}' does not exist in '{pack_path}'")


def validate_plan(plan: dict[str, Any], root: Path) -> list[str]:
    """Return a list of human-readable schema violations (empty if valid).

    `root` is the project root that binding pack paths are relative to.
    """
    errors: list[str] = []
    _require("schemaVersion", plan.get("schemaVersion") == PLAN_SCHEMA_VERSION,
             f"must equal '{PLAN_SCHEMA_VERSION}'", errors)
    _require("planId", isinstance(plan.get("planId"), str) and plan["planId"],
             "must be a non-empty string", errors)
    _require("goal", isinstance(plan.get("goal"), str) and plan["goal"],
             "must be a non-empty string", errors)

    tasks = plan.get("tasks")
    _require("tasks", isinstance(tasks, list) and len(tasks) > 0,
             "must be a non-empty list", errors)

    if isinstance(tasks, list):
        ids: set[str] = set()
        for index, task in enumerate(tasks):
            base = f"tasks[{index}]"
            if not isinstance(task, dict):
                errors.append(f"{base}: must be an object")
                continue
            tid = task.get("id")
            _require(f"{base}.id", isinstance(tid, str) and tid, "must be a non-empty string", errors)
            if tid:
                if tid in ids:
                    errors.append(f"{base}.id: duplicate id '{tid}'")
                ids.add(tid)
            _require(f"{base}.role", isinstance(task.get("role"), str) and task["role"],
                     "must be a non-empty string", errors)
            _require(f"{base}.scope", isinstance(task.get("scope"), str) and task["scope"],
                     "must be a non-empty string", errors)
            _require(f"{base}.expectedArtifacts",
                     isinstance(task.get("expectedArtifacts"), list) and task["expectedArtifacts"],
                     "must be a non-empty list", errors)
            deps = task.get("dependsOn", [])
            _require(f"{base}.dependsOn", isinstance(deps, list),
                     "must be a list", errors)
            if isinstance(deps, list):
                for dep in deps:
                    if dep not in ids and dep != tid:
                        # Note: backward refs only; forward deps are flagged.
                        errors.append(f"{base}.dependsOn: '{dep}' not declared before this task")
            validate_binding(base, task, root, errors)

    return errors


def validate_result(result: dict[str, Any]) -> list[str]:
    """Return a list of human-readable schema violations (empty if valid)."""
    errors: list[str] = []
    _require("schemaVersion", result.get("schemaVersion") == RESULT_SCHEMA_VERSION,
             f"must equal '{RESULT_SCHEMA_VERSION}'", errors)
    _require("planId", isinstance(result.get("planId"), str) and result["planId"],
             "must be a non-empty string", errors)
    _require("taskId", isinstance(result.get("taskId"), str) and result["taskId"],
             "must be a non-empty string", errors)
    _require("role", isinstance(result.get("role"), str) and result["role"],
             "must be a non-empty string", errors)

    status = result.get("status")
    _require("status", status in {"completed", "failed", "skipped"},
             "must be one of completed|failed|skipped", errors)

    artifacts = result.get("artifacts", [])
    _require("artifacts", isinstance(artifacts, list),
             "must be a list", errors)
    if status == "completed":
        _require("artifacts", isinstance(artifacts, list) and len(artifacts) > 0,
                 "must be non-empty when status=completed", errors)

    if status == "failed":
        _require("error", isinstance(result.get("error"), str) and result["error"],
                 "must be a non-empty string when status=failed", errors)

    if isinstance(artifacts, list):
        for index, artifact in enumerate(artifacts):
            base = f"artifacts[{index}]"
            if not isinstance(artifact, dict):
                errors.append(f"{base}: must be an object")
                continue
            _require(f"{base}.path", isinstance(artifact.get("path"), str) and artifact["path"],
                     "must be a non-empty string", errors)
            _require(f"{base}.kind", artifact.get("kind") in {"file", "diff", "report", "decision"},
                     "must be one of file|diff|report|decision", errors)

    return errors


def main() -> int:
    # Plan and result ids are free text; a Windows console defaults to a legacy code page.
    cc.configure_output()
    parser = argparse.ArgumentParser(description="Validate orchestration handoff artifacts.")
    parser.add_argument("--plan", help="Path to an OrchestrationPlan JSON file.")
    parser.add_argument(
        "--result", "--results",
        dest="results",
        nargs="+",
        default=None,
        help="One or more SubAgentResult JSON files to validate.",
    )
    parser.add_argument("--project", default=None,
                        help="Project root binding pack paths are relative to (default: $CLAUDE_PROJECT_DIR, git, cwd).")
    args = parser.parse_args()

    if not args.plan and not args.results:
        parser.error("provide at least --plan or --result")

    failures = 0

    if args.plan:
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        errors = validate_plan(plan, cc.project_root(args.project))
        if errors:
            failures += 1
            print(f"plan {args.plan}: invalid", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
        else:
            print(f"plan {args.plan}: ok")

    if args.results:
        for path in args.results:
            result = json.loads(Path(path).read_text(encoding="utf-8"))
            errors = validate_result(result)
            if errors:
                failures += 1
                print(f"result {path}: invalid", file=sys.stderr)
                for err in errors:
                    print(f"  - {err}", file=sys.stderr)
            else:
                print(f"result {path}: ok")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
