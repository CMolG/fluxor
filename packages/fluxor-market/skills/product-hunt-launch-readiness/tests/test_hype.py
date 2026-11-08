"""The three hype detectors (launch kit, repository audit, URL audit) agree on superlatives.

Run from the repository root:
    python3 -m unittest discover -s skills/product-hunt-launch-readiness/tests
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import audit_repo  # noqa: E402
import audit_url  # noqa: E402
import check_launch_kit  # noqa: E402

HYPED = [
    "The smartest AI copilot for recruiters ever made",
    "The best invoicing app ever",
    "The most useful tool you will ever install",
    "The world's first AI recruiter",
    "The world’s fastest markdown editor",
    "The #1 ATS for startups",
    "Number one CRM for agencies",
    "Our most powerful release yet",
    "The greatest note app",
]

PLAIN = [
    "Invoices that chase themselves",
    "Most teams track hires in spreadsheets; we replace them",
    "Screen candidates in half the time",
    "Forever free for small teams",
    "Track every candidate from one inbox",
    "Whenever a candidate replies, you know",
    "Fixes issue #12 in the scheduler",
    "Brand color #1e293b on every chart",
    "Rank 1st in your own dashboard, not ours",
]

DETECTORS = {
    "check_launch_kit": lambda t: bool(check_launch_kit.HYPE.search(t)),
    "audit_repo": lambda t: any(rx.search(t) for rx in audit_repo.HYPE),
    "audit_url": lambda t: any(rx.search(t) for rx in audit_url.HYPE),
}


class Hype(unittest.TestCase):
    def test_superlatives_are_flagged_everywhere(self):
        for name, is_hype in DETECTORS.items():
            for text in HYPED:
                with self.subTest(detector=name, text=text):
                    self.assertTrue(is_hype(text))

    def test_ordinary_words_are_not_flagged(self):
        for name, is_hype in DETECTORS.items():
            for text in PLAIN:
                with self.subTest(detector=name, text=text):
                    self.assertFalse(is_hype(text))

    def test_tagline_warning_from_the_cli(self):
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        result = subprocess.run([sys.executable, str(SCRIPTS / "check_launch_kit.py"), "--tagline",
                                 "The smartest AI copilot for recruiters ever made"],
                                capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hype wording", result.stdout)


if __name__ == "__main__":
    unittest.main()
