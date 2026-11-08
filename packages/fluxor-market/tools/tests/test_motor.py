"""The routing engine's rule for board roles (card://JAVA-327): wording never picks one."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "market"))
import motor  # noqa: E402


class BoardRoles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = motor.load_catalog, motor.load_lexicon
        self.roles = [
            self.role("backend-engineer", "Designs server logic.", ["server"]),
            # Matches the prompt far better than backend-engineer does.
            self.role("backend-developer", "Implements backend api endpoints for a card.",
                      ["board", "phase-action", "backend", "api", "endpoint"]),
        ]
        motor.load_catalog = lambda: {"roles": self.roles, "mods": [], "steps": []}
        motor.load_lexicon = lambda: {}

    def tearDown(self):
        motor.load_catalog, motor.load_lexicon = self.saved

    def role(self, id_: str, description: str, tags: list) -> dict:
        path = self.tmp / f"{id_}.md"
        path.write_text(f"# {id_}\n\n{description}\n", encoding="utf-8")
        return {"id": id_, "description": description, "tags": tags, "domains": [], "incompatible": [],
                "exclusive_group": None, "runtime": None, "path": path, "order": len(getattr(self, "roles", []))}

    def picked(self, prompt: str) -> str:
        return motor.resolve(prompt, self.tmp)["role"]["id"]

    def test_wording_never_picks_a_board_role(self):
        self.assertEqual(self.picked("implement the backend api endpoint"), "backend-engineer")

    def test_an_explicit_directive_still_attaches_it(self):
        self.assertEqual(self.picked("implement the backend api endpoint @role:backend-developer"),
                         "backend-developer")

    def test_a_board_role_that_is_also_interactive_can_be_picked(self):
        self.roles[1]["tags"].append("interactive")
        self.assertEqual(self.picked("implement the backend api endpoint"), "backend-developer")

    def test_wording_never_suggests_a_flow_step(self):
        steps = [dict(self.role("run-tests", "Runs the backend api tests of the flow.",
                                ["tests", "backend", "api", "flow"]), order=0),
                 dict(self.role("review-diff", "Reviews the backend api diff.", ["review", "backend", "api"]),
                      order=1)]
        motor.load_catalog = lambda: {"roles": self.roles, "mods": [], "steps": steps}
        got = motor.resolve("implement and test the backend api endpoint", self.tmp)
        self.assertEqual([s["id"] for s in got["steps"]], ["review-diff"])


class FlowMods(unittest.TestCase):
    """A mod tagged `flow` belongs to a flow: wording never preselects it, and it never lowers the
    threshold an ordinary mod must clear (the failure `never_auto` had). @mod: still attaches it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = motor.load_catalog, motor.load_lexicon
        self.roles = [self.role("copywriter", "Writes landing page copy.", ["copy"])]
        self.mods = [
            # Matches the prompt better than the ordinary mod does, so it would win the shortlist.
            self.mod("hero-copy-flow", "Rewrites the landing hero copy and value props.",
                     ["copy", "landing", "hero", "flow"]),
            self.mod("hero-copy-ordinary", "Keeps the landing hero copy short.", ["copy", "landing", "hero"]),
        ]
        motor.load_catalog = lambda: {"roles": self.roles, "mods": self.mods, "steps": []}
        motor.load_lexicon = lambda: {}

    def tearDown(self):
        motor.load_catalog, motor.load_lexicon = self.saved

    def role(self, id_: str, description: str, tags: list) -> dict:
        path = self.tmp / f"{id_}.md"
        path.write_text(f"# {id_}\n\n{description}\n", encoding="utf-8")
        return {"id": id_, "description": description, "tags": tags, "domains": [], "incompatible": [],
                "exclusive_group": None, "runtime": None, "path": path, "order": 0}

    def mod(self, id_: str, description: str, tags: list) -> dict:
        path = self.tmp / f"{id_}.md"
        path.write_text(f"# {id_}\n\n{description}\n", encoding="utf-8")
        return {"id": id_, "description": description, "tags": tags, "domains": [], "incompatible": [],
                "exclusive_group": None, "runtime": None, "path": path, "order": 0}

    def mods_of(self, prompt: str) -> list:
        return [m["id"] for m in motor.resolve(prompt, self.tmp)["mods"]]

    def test_wording_never_preselects_a_flow_mod(self):
        self.assertEqual(self.mods_of("rewrite the landing hero copy"), ["hero-copy-ordinary"])

    def test_an_explicit_directive_still_attaches_it(self):
        self.assertEqual(self.mods_of("rewrite the landing hero copy @mod:hero-copy-flow"),
                         ["hero-copy-flow", "hero-copy-ordinary"])


class CardDrivenRoles(unittest.TestCase):
    """A prompt about a board card takes its role from the card, never from its wording
    (card://JAVA-271: ported from the harness engine, where JAVA-371 introduced it)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        role = self.tmp / "backend-engineer.md"
        role.write_text("# backend-engineer\n\nDesigns server logic.\n", encoding="utf-8")
        catalog = {"roles": [{"id": "backend-engineer", "description": "Designs server logic and java apis.",
                              "tags": ["server", "java"], "domains": [], "incompatible": [],
                              "exclusive_group": None, "runtime": None, "path": role, "order": 0}],
                   "mods": [], "steps": []}
        self.saved = (motor.load_catalog, motor.load_lexicon, motor.CARD_KEY, motor.LOOP_MARKERS,
                      motor.STATE_DIR, motor.INVARIANTS_FILE)
        motor.load_catalog = lambda: catalog
        motor.load_lexicon = lambda: {}
        motor.STATE_DIR = self.tmp / "state"
        motor.INVARIANTS_FILE = self.tmp / "none.md"
        motor.CONFIG["cards"] = {"keyPrefixes": ["PROJ"], "loopMarkers": [".loop/prompt.md"]}
        motor.CARD_KEY, motor.LOOP_MARKERS = motor._card_settings()

    def tearDown(self):
        (motor.load_catalog, motor.load_lexicon, motor.CARD_KEY, motor.LOOP_MARKERS,
         motor.STATE_DIR, motor.INVARIANTS_FILE) = self.saved
        motor.CONFIG.pop("cards", None)

    def hook(self, prompt: str) -> str:
        payload = json.dumps({"prompt": prompt, "session_id": str(len(prompt)), "cwd": str(self.tmp)})
        with mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                mock.patch.object(sys, "stdout", io.StringIO()) as out:
            motor.hook_mode()
            return out.getvalue()

    def test_a_card_key_mounts_the_card_role_even_for_a_short_prompt(self):
        out = self.hook("work PROJ-12")
        self.assertIn('<role source="card" card="PROJ-12">', out)
        self.assertNotIn('<role id="backend-engineer">', out)

    def test_a_loop_prompt_names_no_card_and_is_card_driven_too(self):
        self.assertIn('<role source="card" card="loop">', self.hook("Follow .loop/prompt.md and pick one card"))

    def test_an_explicit_role_still_wins(self):
        self.assertIn('<role id="backend-engineer">', self.hook("work PROJ-12 @role:backend-engineer"))

    def test_without_the_setting_a_key_is_ordinary_wording(self):
        motor.CARD_KEY, motor.LOOP_MARKERS = None, []
        self.assertNotIn('source="card"', self.hook("design the java server api for PROJ-12"))


class WorkflowAuthor(unittest.TestCase):
    """The workflow-author mod (card://JAVA-1593) is a whole persona, never wording's pick: it is
    attached with @mod:, and it never changes the ordinary mods a prompt gets, because it is in the
    lexicon's never_auto list."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = motor.load_catalog, motor.load_lexicon

    def tearDown(self):
        motor.load_catalog, motor.load_lexicon = self.saved

    def mods_of(self, prompt: str) -> list:
        return [m["id"] for m in motor.resolve(prompt, self.tmp)["mods"]]

    def test_wording_does_not_mount_it_and_a_directive_does(self):
        prompt = "write the workflow of this card: the roles and mods for each phase"
        self.assertNotIn("workflow-author", self.mods_of(prompt))
        self.assertIn("workflow-author", self.mods_of(prompt + " @mod:workflow-author"))

    def test_it_does_not_change_the_ordinary_mods_of_a_prompt(self):
        prompt = "plan the refine of this card and keep the copy short"
        with_atom = self.mods_of(prompt)
        catalog = self.saved[0]()
        catalog["mods"] = [m for m in catalog["mods"] if m["id"] != "workflow-author"]
        motor.load_catalog = lambda: catalog
        self.assertEqual(with_atom, self.mods_of(prompt))


if __name__ == "__main__":
    unittest.main()
