"""Snapshot-style tests that pin the full pipeline output for each fixture.

To regenerate the stored snapshots after an intentional contract change, run from this skill's
directory:

    SNAPSHOT_UPDATE=1 python3 -m unittest discover -s tests -t tests -p test_pipeline_snapshots.py
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jira_pipeline_cli as cli  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
SNAPSHOTS = HERE / "snapshots"

SCENARIOS = ["tight", "medium", "empty", "ambiguous"]

VOLATILE_KEYS = {"fetchedAt", "generatedAt", "resolvedAt", "lastUpdated", "capturedAt"}


def _strip_volatile(node):
    """Recursively replace timestamp-like fields with a placeholder so snapshots are stable."""
    if isinstance(node, dict):
        return {k: ("<timestamp>" if k in VOLATILE_KEYS else _strip_volatile(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [_strip_volatile(item) for item in node]
    return node


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_full_pipeline(fixture_path: Path, tmp_path: Path) -> dict[str, dict]:
    issue_path = tmp_path / "issue.json"
    issue_path.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

    with contextlib.redirect_stdout(io.StringIO()):
        analysis_path = tmp_path / "analysis.json"
        cli.discovery(Namespace(input=str(issue_path), output=str(analysis_path)))

        questions_path = tmp_path / "questions.json"
        cli.generate_questions(
            Namespace(
                input=str(analysis_path),
                output=str(questions_path),
                baseline_budget=cli.DEFAULT_BASELINE_BUDGET,
                signal_budget=cli.DEFAULT_SIGNAL_BUDGET,
            )
        )

        # Synthesize deterministic answers so resolve-contract can produce a contract.
        questions = _read(questions_path)
        state = {
            "issueKey": questions["issueKey"],
            "answers": {
                q["id"]: {
                    "answer": f"Decision for {q['category']}",
                    "capturedAt": datetime.now(timezone.utc).isoformat(),
                    "priority": q["priority"],
                    "category": q["category"],
                }
                for q in questions["questions"]
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")

        contract_path = tmp_path / "contract.json"
        cli.resolve_contract(
            Namespace(questions=str(questions_path), answers=str(state_path), output=str(contract_path))
        )

        plan_path = tmp_path / "plan.json"
        cli.base_branch_plan(
            Namespace(analysis=str(analysis_path), contract=str(contract_path), output=str(plan_path))
        )

    return {
        "analysis": _read(analysis_path),
        "questions": _read(questions_path),
        "contract": _read(contract_path),
        "plan": _read(plan_path),
    }


class PipelineSnapshots(unittest.TestCase):
    def run_pipeline(self, scenario: str) -> dict[str, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            return _run_full_pipeline(FIXTURES / f"issue_{scenario}.json", Path(tmp))

    def test_pipeline_snapshot(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                snapshot_dir = SNAPSHOTS / scenario
                cleaned = {name: _strip_volatile(payload) for name, payload in self.run_pipeline(scenario).items()}

                if os.environ.get("SNAPSHOT_UPDATE") == "1":
                    snapshot_dir.mkdir(parents=True, exist_ok=True)
                    for name, payload in cleaned.items():
                        with open(snapshot_dir / f"{name}.json", "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                    continue

                for name, actual in cleaned.items():
                    snap_file = snapshot_dir / f"{name}.json"
                    self.assertTrue(snap_file.exists(), f"missing snapshot {snap_file}; regenerate with SNAPSHOT_UPDATE=1")
                    self.assertEqual(actual, _read(snap_file), f"snapshot mismatch for {scenario}/{name}")

    def test_pipeline_status_matches_scenario(self):
        cases = [
            ("tight", "LOW", "READY_FOR_BASE_BRANCH"),
            ("medium", "MEDIUM", "PLAN_ONLY"),
            ("empty", "HIGH", "QUESTIONS_ONLY"),
            ("ambiguous", "HIGH", "QUESTIONS_ONLY"),
        ]
        for scenario, expected_level, expected_status in cases:
            with self.subTest(scenario=scenario):
                outputs = self.run_pipeline(scenario)
                self.assertEqual(outputs["analysis"]["ambiguityLevel"]["level"], expected_level)
                self.assertEqual(outputs["plan"]["status"], expected_status)

    def test_contract_preserves_unmapped_answers(self):
        contract = self.run_pipeline("tight")["contract"]
        self.assertIn("unmappedAnswers", contract)
        self.assertIsInstance(contract["unmappedAnswers"], list)

    def test_plan_uses_proposed_branch_name(self):
        plan = self.run_pipeline("tight")["plan"]
        self.assertIn("proposedBranchName", plan)
        self.assertNotIn("branchName", plan)
        self.assertTrue(plan["proposedBranchName"].startswith("ai/"))

    def test_all_artifacts_carry_schema_version(self):
        for name, payload in self.run_pipeline("tight").items():
            with self.subTest(artifact=name):
                self.assertEqual(payload.get("schemaVersion"), cli.CONTRACT_SCHEMA_VERSION,
                                 f"{name} missing schemaVersion")


if __name__ == "__main__":
    unittest.main()
