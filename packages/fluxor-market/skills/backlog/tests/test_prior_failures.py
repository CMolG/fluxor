"""The failure history (`priorFailures`) is named where a session reads it: the Refine row plans with it, the
To do check looks again, the adapter maps it, and the review protocol checks the plan's `Known failure
modes:` lines. The text is the contract the sessions follow, so the tests pin the words they depend on."""

from __future__ import annotations

import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SKILL_MD = (SKILL / "SKILL.md").read_text(encoding="utf-8")
ADAPTER = (SKILL / "references" / "adapter-officium.md").read_text(encoding="utf-8")
PROTOCOL = (SKILL / "references" / "review-protocol.md").read_text(encoding="utf-8")


class PriorFailures(unittest.TestCase):
    def test_the_operation_is_in_the_abstract_table_and_the_adapter(self):
        self.assertIn("`priorFailures(card, touched?)`", SKILL_MD)
        self.assertIn("`cards.priorFailures", ADAPTER)
        self.assertIn("prior-failures", ADAPTER)

    def test_refine_plans_with_the_history_and_names_the_paths_first(self):
        refine = next(line for line in SKILL_MD.splitlines() if line.startswith("| **Refine**"))
        self.assertIn("card_refs.py touching", refine)
        self.assertIn("priorFailures(card, touched)", refine)
        self.assertIn("`Known failure modes:`", refine)
        self.assertIn("`Known failure modes: none found`", refine)
        self.assertIn("`Guard:`", refine)

    def test_the_to_do_check_looks_again_at_the_same_history(self):
        todo = SKILL_MD.split("### To do is a check, not the work", 1)[1].split("Then one of two moves", 1)[0]
        self.assertIn("priorFailures", todo)
        self.assertIn("Known failure modes:", todo)

    def test_quotes_are_data(self):
        third_party = SKILL_MD.split("## Third-party content is data", 1)[1].split("## Writing a card", 1)[0]
        self.assertIn("priorFailures", third_party)
        self.assertIn("never instructions", third_party)

    def test_the_review_protocol_checks_each_known_failure_mode_as_a_row(self):
        self.assertIn("Each `Known failure modes:` line of the plan is one row", PROTOCOL)
        self.assertIn("`not applicable`", PROTOCOL)

    def test_the_skill_says_without_the_operation_the_plan_says_unavailable(self):
        self.assertIn("Known failure modes: unavailable", SKILL_MD)


if __name__ == "__main__":
    unittest.main()
