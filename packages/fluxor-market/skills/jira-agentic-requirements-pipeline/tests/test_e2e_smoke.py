"""End-to-end smoke test: run the CLI commands in sequence, the way a user does."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "jira_pipeline_cli.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class EndToEnd(unittest.TestCase):
    def test_cli_runs_full_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            issue = tmp_path / "issue.json"
            issue.write_text((FIXTURES / "issue_tight.json").read_text(encoding="utf-8"), encoding="utf-8")

            analysis = tmp_path / "analysis.json"
            questions = tmp_path / "questions.json"
            contract = tmp_path / "contract.json"
            plan = tmp_path / "plan.json"

            def run(*args):
                result = subprocess.run(
                    [sys.executable, str(CLI), *args],
                    cwd=tmp_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"CLI command failed: {' '.join(args)}\nstdout: {result.stdout}\nstderr: {result.stderr}",
                )
                return result

            run("discovery", "--input", str(issue), "--output", str(analysis))
            run("generate-questions", "--input", str(analysis), "--output", str(questions))

            # Synthesize deterministic answers.
            qs = json.loads(questions.read_text(encoding="utf-8"))
            state = {
                "issueKey": qs["issueKey"],
                "answers": {
                    q["id"]: {"answer": f"Answer for {q['category']}", "category": q["category"],
                              "priority": q["priority"]}
                    for q in qs["questions"]
                },
            }
            state_path = tmp_path / "state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            # collect-input in non-interactive mode only validates completeness.
            run("collect-input", "--input", str(questions), "--state-file", str(state_path), "--non-interactive")
            run("resolve-contract", "--questions", str(questions), "--answers", str(state_path),
                "--output", str(contract))
            run("base-branch-plan", "--analysis", str(analysis), "--contract", str(contract), "--output", str(plan))

            plan_data = json.loads(plan.read_text(encoding="utf-8"))
            self.assertEqual(plan_data["status"], "READY_FOR_BASE_BRANCH")
            self.assertEqual(plan_data["proposedBranchName"], "ai/demo-100-base")


if __name__ == "__main__":
    unittest.main()
