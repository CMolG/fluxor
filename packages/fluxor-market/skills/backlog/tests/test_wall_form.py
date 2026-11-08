"""The wall-with-a-form protocol (SKILL.md "A wall answered by a form") and its Officium mapping say the
same things, and say the whole of them: the authoring rules a form must pass, where it is linted, how
it is attached, and where its answers are read."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PROTOCOL = (SKILL / "SKILL.md").read_text()
ADAPTER = (SKILL / "references" / "adapter-officium.md").read_text()


def section(text: str, heading: str) -> str:
    match = re.search(rf"^### {re.escape(heading)}\n(.*?)(?=^#{{2,3}} )", text, re.S | re.M)
    assert match, f"no '{heading}' section"
    return match.group(1)


class WallForm(unittest.TestCase):
    def test_the_protocol_carries_every_authoring_rule(self):
        rules = section(PROTOCOL, "A wall answered by a form")
        for fragment in (
            "one question per step",
            "one decision per question",
            "the kind follows the answer",
            "yes/no with the command in `help`",
            "never ask for a secret",
            "at most ten questions",
            "opening statement",
            "Lint the draft",
            "`getCard` returns the answers as structured data",
        ):
            self.assertIn(fragment, rules)

    def test_the_wall_no_longer_asks_for_a_free_text_answer(self):
        rules = section(PROTOCOL, "A wall answered by a form")
        self.assertIn("no longer asks the person to write a free-text answer", rules)

    def test_requesthuman_takes_a_form_in_the_operation_table_and_the_mapping(self):
        self.assertIn("requestHuman(why, steps, doneWhen, unblocks, category, form?)", PROTOCOL)
        self.assertRegex(ADAPTER, r"\| `requestHuman\(\.\.\.\)` \| `cards\.requestHuman` \|[^\n]*`form`")

    def test_the_officium_mapping_names_each_operation_the_protocol_relies_on(self):
        for operation in ("cards.attachForm", "forms.lint", "form.answers", "form.history", "form_invalid"):
            self.assertIn(operation, ADAPTER)

    def test_a_completed_form_is_found_by_the_human_edit_step(self):
        self.assertIn("A wall whose person completed its form turns up here too", PROTOCOL)
        self.assertIn("an answered form raises it too", ADAPTER)

    def test_a_wall_without_a_form_is_refused_unless_it_says_why(self):
        rules = section(PROTOCOL, "A wall answered by a form")
        self.assertIn("a wall without one is refused", rules)
        self.assertIn("`No form: <reason>`", rules)


class DecisionPolicy(unittest.TestCase):
    """A project that hands business decisions to agents names its rule once, and step 5 reads it."""

    def test_step_five_defers_to_the_projects_decision_policy(self):
        step = re.search(r"^5\. \*\*Is the card ready\?\*\*(.*?)^6\. ", PROTOCOL, re.S | re.M)
        self.assertTrue(step)
        self.assertIn("`decisionPolicy`", step.group(1))
        self.assertIn("Decided by:", step.group(1))

    def test_the_key_is_in_the_config_table_and_the_schema(self):
        self.assertRegex(PROTOCOL, re.compile(r"^\| `decisionPolicy` \| none \|", re.M))
        schema = json.loads((SKILL / "config.schema.json").read_text())
        self.assertEqual(schema["properties"]["decisionPolicy"]["type"], "string")


if __name__ == "__main__":
    unittest.main()
