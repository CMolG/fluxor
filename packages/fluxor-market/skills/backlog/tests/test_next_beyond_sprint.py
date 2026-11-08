"""Step 4 of the protocol ("When `nextCard` finds nothing") and the Officium mapping say the same thing
about reaching past a sprint that is all blocked: the option's name, what it answers, and that the card
goes into the sprint before it is worked."""

from __future__ import annotations

import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PROTOCOL = (SKILL / "SKILL.md").read_text()
ADAPTER = (SKILL / "references" / "adapter-officium.md").read_text()
LOOP_PROMPT = (SKILL.parent / "autoloop" / "prompt.md").read_text()


class NextBeyondSprint(unittest.TestCase):
    def test_the_protocol_names_the_option_and_what_it_answers(self):
        for fragment in (
            "`nextCard(beyondSprint)`",
            "blocks a blocked sprint card",
            "never a person's",
            "else the best\n   card in no sprint",
            "`setSprint` it into the active one",
            "Without the flag, `nextCard` never leaves the sprint",
        ):
            self.assertIn(fragment, PROTOCOL)

    def test_the_officium_mapping_passes_the_flag(self):
        row = next(line for line in ADAPTER.splitlines() if line.startswith("| `nextCard` |"))
        self.assertIn("`cards.next`", row)
        self.assertIn("`beyondSprint: true`", row)
        self.assertIn("?beyondSprint=true", row)

    def test_the_loop_asks_past_the_sprint_before_idling(self):
        before_idle = LOOP_PROMPT.split("Nothing left to claim")[0]
        self.assertIn("beyond-the-sprint", before_idle)
        self.assertIn("move it into the sprint before you work it", before_idle.replace("\n   ", " "))


if __name__ == "__main__":
    unittest.main()
