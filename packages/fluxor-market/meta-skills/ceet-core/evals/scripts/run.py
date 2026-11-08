#!/usr/bin/env python3
"""CEET smoke test runner.

Reads task definitions from `evals/tasks/<task>/criteria.json`, scores every output under
`<results>/<run-id>/<task>/<arm>.md`, and writes `report.{md,json}` next to them.

A smoke test, not a benchmark: it checks that the output of a pack keeps the structure and
vocabulary a task expects and catches the defects planted in the task. It says nothing about
whether the output decides the way the person would; fidelity is measured per person with
`scripts/fidelity.py` (references/fidelity.md). Numbers from hand-written outputs are never
published.

Deterministic and standard library only. It never calls a model: whoever runs it pastes each
arm's reply into the results folder.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# The ceet-core folder: evals/ sits directly under it.
SKILL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import scoring  # noqa: E402


SCHEMA_VERSION = "2.0.0"
# `baseline`: the prompt alone. `generic`: a role persona. `raw`: the person's raw answers and about
# ten of their real decisions, no synthesis. `ceet`: the prompt with the rendered pack.
ARMS = ["baseline", "generic", "raw", "ceet"]


def list_tasks(tasks_dir: Path) -> list[str]:
    return sorted(p.name for p in tasks_dir.iterdir() if p.is_dir() and (p / "criteria.json").exists())


def load_task(tasks_dir: Path, name: str) -> dict[str, Any]:
    criteria = json.loads((tasks_dir / name / "criteria.json").read_text(encoding="utf-8"))
    corpus_path = tasks_dir / name / "voice-corpus.txt"
    corpus = corpus_path.read_text(encoding="utf-8") if corpus_path.exists() else None
    return {"name": name, "criteria": criteria, "corpus": corpus}


def score_run(results_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
    """Score every available arm for a task. Missing arms are skipped."""
    task_dir = results_dir / task["name"]
    arm_scores: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        output_path = task_dir / f"{arm}.md"
        if output_path.exists():
            arm_scores[arm] = scoring.score_output(output_path.read_text(encoding="utf-8"),
                                                   task["criteria"], task["corpus"])
    return arm_scores


def check(report: dict[str, Any], arm: str = "ceet") -> list[str]:
    """Regression problems of one arm: out-of-bounds length, a missing required section, a forbidden
    phrase. Planted defects are reported, not failed: detection by phrase is too crude to gate on."""
    problems = []
    for task_name, task_report in report["tasks"].items():
        scores = task_report["arms"].get(arm)
        if scores is None:
            continue
        if not scores["lengthWithinBounds"]:
            problems.append(f"{task_name}: {scores['wordCount']} words is outside the task's bounds")
        missing = [s for s, hit in scores["sectionHits"].items() if not hit]
        if missing:
            problems.append(f"{task_name}: missing section(s) {', '.join(missing)}")
        if scores["forbiddenHits"]:
            problems.append(f"{task_name}: forbidden phrase(s) {', '.join(scores['forbiddenHits'])}")
    return problems


def fmt(value) -> str:
    return "—" if value is None else (f"{value:.2f}" if isinstance(value, float) else str(value))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# Smoke test — {report['runId']}", "",
             "> Structure and vocabulary regression checks, plus planted-defect recall. Not a fidelity",
             "> measure: see references/fidelity.md.", "",
             "| Task | Arm | Words | Sections | Phrases | Defects found | Forbidden | Voice |",
             "|---|---|---:|---:|---:|---:|---|---:|"]
    for task_name, task_report in report["tasks"].items():
        for arm, s in task_report["arms"].items():
            lines.append(f"| `{task_name}` | `{arm}` | {s['wordCount']} | {fmt(s['sectionCoverage'])} | "
                         f"{fmt(s['phraseCoverage'])} | {fmt(s['defectRecall'])} | "
                         f"{', '.join(s['forbiddenHits']) or 'none'} | {fmt(s['voiceAlignment'])} |")
    return "\n".join(lines) + "\n"


def run(run_id: str, tasks_dir: Path, results_root: Path) -> dict[str, Any]:
    results_dir = results_root / run_id
    if not results_dir.exists():
        raise SystemExit(f"results directory does not exist: {results_dir}")
    report: dict[str, Any] = {"schemaVersion": SCHEMA_VERSION, "runId": run_id, "kind": "smoke-test", "tasks": {}}
    for task_name in list_tasks(tasks_dir):
        task = load_task(tasks_dir, task_name)
        arm_scores = score_run(results_dir, task)
        if arm_scores:
            report["tasks"][task_name] = {"criteria": task["criteria"], "arms": arm_scores}
    (results_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (results_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run the CEET smoke test.")
    parser.add_argument("--run-id", required=True, help="Subfolder of the results folder.")
    parser.add_argument("--tasks-dir", default=str(SKILL_ROOT / "evals" / "tasks"))
    parser.add_argument("--results-dir", required=True, help="Where the runs live (keep real runs out of the repository).")
    parser.add_argument("--check", action="store_true", help="Exit non-zero on a regression of the ceet arm.")
    args = parser.parse_args()
    report = run(args.run_id, Path(args.tasks_dir), Path(args.results_dir))
    print(f"report written to {Path(args.results_dir) / args.run_id}/report.{{json,md}}")
    if args.check:
        problems = check(report)
        for p in problems:
            print(f"regression: {p}")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
