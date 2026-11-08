"""Tests for evals/scripts/run.py.

The seed run is copied to a temporary directory first: `run()` writes `report.json` and
`report.md` next to the outputs it scores, and a test must not rewrite files in the repository.
The run is a smoke test, not a benchmark (evals/README.md): these tests pin that it scores what is
there and that `--check` catches a regression, never that one arm "beats" another.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "evals" / "scripts"))
import run as eval_run  # noqa: E402

TASKS_DIR = SKILL / "evals" / "tasks"
SEED_DIR = Path(__file__).resolve().parent / "fixtures" / "seed-run"
SEED = "seed-run"
TASKS = {"engineering-pr-review", "product-prd-draft", "copy-headlines"}


class SeedRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.results_root = Path(self._tmp.name) / "results"
        shutil.copytree(SEED_DIR, self.results_root / SEED)

    def tearDown(self):
        self._tmp.cleanup()

    def run_seed(self) -> dict:
        return eval_run.run(SEED, TASKS_DIR, self.results_root)

    def test_every_task_and_arm_present_is_scored(self):
        report = self.run_seed()
        self.assertEqual(report["kind"], "smoke-test")
        self.assertEqual(report["schemaVersion"], eval_run.SCHEMA_VERSION)
        self.assertEqual(set(report["tasks"]), TASKS)
        for task in report["tasks"].values():
            # The fixture holds three of the four arms; the missing `raw` is skipped, not failed.
            self.assertEqual(set(task["arms"]), {"baseline", "generic", "ceet"})

    def test_reports_are_written_next_to_the_outputs(self):
        self.run_seed()
        self.assertTrue((self.results_root / SEED / "report.json").exists())
        report_md = (self.results_root / SEED / "report.md").read_text(encoding="utf-8")
        self.assertIn("Not a fidelity", report_md)
        self.assertIn("`engineering-pr-review` | `ceet`", report_md)

    def test_check_passes_for_the_seed_ceet_arm(self):
        self.assertEqual(eval_run.check(self.run_seed()), [])

    def test_check_names_each_regression(self):
        # The seed's generic copy-headlines reply is 50 words (min 60) and says "next-generation".
        problems = eval_run.check(self.run_seed(), arm="generic")
        self.assertIn("copy-headlines: 50 words is outside the task's bounds", problems)
        self.assertIn("copy-headlines: forbidden phrase(s) next-generation", problems)

    def test_check_flags_a_missing_section(self):
        ceet = self.results_root / SEED / "engineering-pr-review" / "ceet.md"
        text = ceet.read_text(encoding="utf-8")
        ceet.write_text("\n".join(
            line for line in text.splitlines() if not (line.startswith("#") and "rollback" in line.lower())
        ), encoding="utf-8")
        problems = eval_run.check(self.run_seed())
        self.assertIn("engineering-pr-review: missing section(s) rollback", problems)

    def test_cli_check_exits_non_zero_on_a_regression(self):
        cli = [sys.executable, str(SKILL / "evals" / "scripts" / "run.py"),
               "--run-id", SEED, "--results-dir", str(self.results_root), "--check"]
        self.assertEqual(subprocess.run(cli, capture_output=True, text=True).returncode, 0)
        (self.results_root / SEED / "copy-headlines" / "ceet.md").write_text(
            "# Headline 1\nRevolutionary!\n# Headline 2\nx\n# Headline 3\ny\n", encoding="utf-8")
        out = subprocess.run(cli, capture_output=True, text=True)
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("regression: copy-headlines", out.stdout)


class RunEdges(unittest.TestCase):
    def test_run_skips_tasks_without_outputs(self):
        """If a results directory has no arm files, the task is skipped silently."""
        with tempfile.TemporaryDirectory() as tmp:
            results_root = Path(tmp) / "results"
            (results_root / "empty-run" / "engineering-pr-review").mkdir(parents=True)
            # No baseline.md / ceet.md / generic.md inside.
            report = eval_run.run("empty-run", TASKS_DIR, results_root)
        self.assertEqual(report["tasks"], {})

    def test_run_id_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit):
            eval_run.run("nonexistent-run-id", TASKS_DIR, Path(tmp))


if __name__ == "__main__":
    unittest.main()
