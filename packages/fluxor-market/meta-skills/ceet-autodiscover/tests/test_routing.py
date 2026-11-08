"""Routing accuracy of detect.py over evals/routing.json, against the roles' own form.json keywords.

Prints the accuracy and every miss, and fails when the accuracy falls under the eval's `floor`.
Run: python3 -m unittest discover -s meta-skills/ceet-autodiscover/tests -t meta-skills/ceet-autodiscover/tests
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
META_SKILLS = SKILL.parent
sys.path.insert(0, str(SKILL / "scripts"))
import detect  # noqa: E402

EVAL = json.loads((SKILL / "evals" / "routing.json").read_text(encoding="utf-8"))


class Routing(unittest.TestCase):
    def test_every_expected_role_exists(self):
        roles = {role.id for role in detect.find_roles([META_SKILLS])}
        expected = {case["expected"] for case in EVAL["cases"]} - {None}
        self.assertFalse(expected - roles, "the eval names roles that are not installed")
        self.assertFalse(roles - expected, "every role needs at least one case in the eval")

    def test_accuracy_holds_the_floor(self):
        with tempfile.TemporaryDirectory() as project:
            root = Path(project)
            misses = []
            for case in EVAL["cases"]:
                got = detect.detect(case["request"], root, [META_SKILLS], root / "packs")["recommendation"]["primary"]
                if got != case["expected"]:
                    misses.append(f"  {case['request']!r}: expected {case['expected']}, got {got}")
        total = len(EVAL["cases"])
        accuracy = (total - len(misses)) / total
        print(f"\nceet-autodiscover routing accuracy: {total - len(misses)}/{total} = {accuracy:.1%} "
              f"(floor {EVAL['floor']:.1%})", file=sys.stderr)
        for miss in misses:
            print(miss, file=sys.stderr)
        self.assertGreaterEqual(accuracy, EVAL["floor"])


if __name__ == "__main__":
    unittest.main()
