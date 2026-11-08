"""tools/marketplace.py install: a project's harness generated from this catalog, and kept that way.

Runs the real catalog into a throwaway harness directory (card://JAVA-271).
Run: python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import marketplace  # noqa: E402

SKILL = "research-radar"
ROLE = "backend-engineer"


class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.harness = self.tmp / ".harness"
        self.harness.mkdir()
        self.select({"skills": [SKILL], "roles": [ROLE], "mods": [], "steps": [], "flows": []})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def select(self, selection: dict) -> None:
        (self.harness / "harness.json").write_text(json.dumps(selection), encoding="utf-8")

    def run_tool(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = marketplace.main(["install", "--harness", str(self.harness), *args])
        return code, out.getvalue()

    def test_an_install_writes_the_copies_and_its_check_passes(self):
        self.assertEqual(self.run_tool()[0], 0)
        skill = self.harness / "skills" / SKILL / "SKILL.md"
        self.assertEqual(skill.read_bytes(), (REPO / "skills" / SKILL / "SKILL.md").read_bytes())
        self.assertFalse((self.harness / "skills" / SKILL / "skill.json").exists())
        self.assertTrue((self.harness / "market" / "roles" / f"{ROLE}.md").is_file())
        self.assertTrue((self.harness / "market" / "motor.py").is_file())
        inventory = json.loads((self.harness / "market" / "inventory.json").read_text(encoding="utf-8"))
        self.assertEqual([c["name"] for c in inventory["roles"]], [ROLE])
        self.assertIn(f"skills/{SKILL}/SKILL.md", json.loads((self.harness / "harness.lock.json").read_text())["files"])
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_a_hand_edit_fails_the_check_and_is_not_overwritten_without_force(self):
        self.run_tool()
        skill = self.harness / "skills" / SKILL / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nedited here\n", encoding="utf-8")
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn(f"skills/{SKILL}/SKILL.md: edited by hand", out)
        self.assertEqual(self.run_tool()[0], 1)
        self.assertIn("edited here", skill.read_text(encoding="utf-8"))
        self.assertEqual(self.run_tool("--force")[0], 0)
        self.assertNotIn("edited here", skill.read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "Windows reports every file one way")
    def test_a_changed_executable_bit_is_an_edit_too(self):
        self.run_tool()
        motor = self.harness / "market" / "motor.py"
        motor.chmod(0o644)
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("executable bit differs", out)

    def test_an_unmanaged_file_fails_unless_declared_local(self):
        self.run_tool()
        (self.harness / "skills" / SKILL / "notes.md").write_text("mine\n", encoding="utf-8")
        mine = self.harness / "skills" / "handmade"
        mine.mkdir()
        (mine / "SKILL.md").write_text("---\nname: handmade\n---\n", encoding="utf-8")
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn(f"skills/{SKILL}/notes.md: unmanaged", out)
        self.assertIn("skills/handmade/SKILL.md: unmanaged", out)
        self.select({"skills": [SKILL], "roles": [ROLE], "mods": [], "steps": [], "flows": [],
                     "local": {"files": [f"skills/{SKILL}/notes.md", "skills/handmade/**"]}})
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_a_catalog_change_makes_the_install_stale_and_reinstalling_removes_what_left(self):
        self.run_tool()
        self.select({"skills": [], "roles": [ROLE], "mods": [], "steps": [], "flows": []})
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("stale", out)
        self.assertEqual(self.run_tool()[0], 0)
        self.assertFalse((self.harness / "skills" / SKILL).exists())
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_a_local_atom_replaces_the_catalog_one_with_the_same_id(self):
        mod = "dark-mode"
        self.select({"skills": [], "roles": [ROLE], "mods": [mod], "steps": [], "flows": [],
                     "local": {"files": [f"market/mods/{mod}.md"],
                               "cards": {"mods": [{"name": mod, "description": "The project's own."}]}}})
        (self.harness / "market" / "mods").mkdir(parents=True)
        (self.harness / "market" / "mods" / f"{mod}.md").write_text("# dark-mode: ours\n", encoding="utf-8")
        self.assertEqual(self.run_tool()[0], 0)
        self.assertEqual((self.harness / "market" / "mods" / f"{mod}.md").read_text(encoding="utf-8"),
                         "# dark-mode: ours\n")
        inventory = json.loads((self.harness / "market" / "inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(inventory["mods"], [{"name": mod, "description": "The project's own."}])
        self.assertNotIn(mod, json.loads((self.harness / "harness.lock.json").read_text())["atoms"])

    # card://JAVA-551: the old lock lists the file, the new install does not, and the removal pass
    # used to delete it without asking whether the project had declared it its own.
    def test_an_installed_atom_the_project_takes_over_keeps_its_file(self):
        mod = "dark-mode"
        installed = {"skills": [], "roles": [ROLE], "mods": [mod], "steps": [], "flows": []}
        taken_over = {**installed, "local": {"files": [f"market/mods/{mod}.md"],
                                             "cards": {"mods": [{"name": mod, "description": "Ours now."}]}}}
        path = self.harness / "market" / "mods" / f"{mod}.md"
        self.select(installed)
        self.run_tool()
        catalog_copy = path.read_bytes()
        self.select(taken_over)
        code, out = self.run_tool()
        self.assertEqual(code, 0, out)
        self.assertIn("0 removed", out)
        self.assertEqual(path.read_bytes(), catalog_copy)
        self.assertNotIn(f"market/mods/{mod}.md", json.loads((self.harness / "harness.lock.json").read_text())["files"])
        self.assertEqual(self.run_tool("--check")[0], 0)

        self.select(installed)
        self.run_tool()
        path.write_text("# dark-mode: edited, then taken over\n", encoding="utf-8")
        self.select(taken_over)
        self.assertEqual(self.run_tool()[0], 0)
        self.assertEqual(self.run_tool("--force")[0], 0)
        self.assertEqual(path.read_text(encoding="utf-8"), "# dark-mode: edited, then taken over\n")

    def test_a_local_card_with_no_file_behind_it_fails_the_check(self):
        mod = "dark-mode"
        self.select({"skills": [], "roles": [ROLE], "mods": [], "steps": [], "flows": [],
                     "local": {"files": [f"market/mods/{mod}.md"],
                               "cards": {"mods": [{"name": mod, "description": "Ours."}]}}})
        self.assertEqual(self.run_tool()[0], 0)
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn(f"market/mods/{mod}.md", out)
        self.assertIn("local card", out)

    # card://JAVA-551: only a TAKEN-OVER file (in the old lock, not in this install) is the project's
    # to edit; one a `local.files` glob covers while the catalog still installs it is not.
    def test_a_local_glob_does_not_let_install_overwrite_an_edit_the_catalog_still_installs(self):
        mod = "dark-mode"
        installed = {"skills": [], "roles": [ROLE], "mods": [mod], "steps": [], "flows": []}
        path = self.harness / "market" / "mods" / f"{mod}.md"
        self.select(installed)
        self.run_tool()
        path.write_text("# dark-mode: edited here\n", encoding="utf-8")
        self.select({**installed, "local": {"files": ["market/mods/*.md"]}})
        code, out = self.run_tool()
        self.assertEqual(code, 1, out)
        self.assertIn(f"market/mods/{mod}.md: edited by hand", out)
        self.assertEqual(path.read_text(encoding="utf-8"), "# dark-mode: edited here\n")

    def test_a_local_pattern_over_a_file_the_catalog_installs_fails_the_check(self):
        mod = "dark-mode"
        self.select({"skills": [], "roles": [ROLE], "mods": [mod], "steps": [], "flows": [],
                     "local": {"files": ["market/mods/*.md"]}})
        code, out = self.run_tool()
        self.assertEqual(code, 0, out)
        self.assertIn(f"warning: market/mods/{mod}.md: installed from the catalog and declared local", out)
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn(f"error: market/mods/{mod}.md: installed from the catalog and declared local", out)

    def test_a_local_card_of_a_kind_the_inventory_lacks_is_an_error(self):
        self.select({"skills": [], "roles": [ROLE], "local": {"cards": {"skills": [{"name": "ours"}]}}})
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("local.cards: unknown kind 'skills'", out)

    def test_an_unmet_requirement_fails_unless_declared_external(self):
        needs = next(a for a in marketplace.load_catalog()[0]
                     if a.kind == "role" and a.manifest.get("requires", {}).get("atoms"))
        deps = [atom.split("@")[0] for atom in needs.manifest["requires"]["atoms"]]
        self.select({"skills": [], "roles": [needs.id], "mods": [], "steps": [], "flows": []})
        code, out = self.run_tool()
        self.assertEqual(code, 1)
        for dep in deps:
            self.assertIn(f"{needs.id} requires {dep}", out)
        self.select({"skills": [], "roles": [needs.id], "mods": [], "steps": [], "flows": [],
                     "external": {dep: "the agent gets it from the user's profile" for dep in deps}})
        self.assertEqual(self.run_tool()[0], 0)

    def test_a_selected_hook_installs_its_scripts_and_fallback(self):
        # card://JAVA-674: a project wires the hooks it selects from market/hooks/ by hand.
        self.select({"skills": [], "hooks": ["officium-heartbeat"]})
        self.assertEqual(self.run_tool()[0], 0)
        folder = self.harness / "market" / "hooks"
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         ["officium-heartbeat.md", "officium-heartbeat.ps1", "officium-heartbeat.sh"])
        if os.name != "nt":
            self.assertTrue(os.access(folder / "officium-heartbeat.sh", os.X_OK))
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_a_selected_preset_installs_its_items_and_locks_itself(self):
        # card://JAVA-161: `presets` expands to the skills and hooks the preset lists.
        self.select({"skills": [SKILL], "presets": ["officium"]})
        self.assertEqual(self.run_tool()[0], 0)
        lock = json.loads((self.harness / "harness.lock.json").read_text())
        preset = json.loads((REPO / "market" / "presets" / "officium.json").read_text())
        listed = {item["key"] for item in preset["items"]}
        self.assertEqual(lock["atoms"]["officium"]["kind"], "preset")
        self.assertTrue(listed <= set(lock["atoms"]), listed - set(lock["atoms"]))
        self.assertIn(SKILL, lock["atoms"], "a preset adds to the selection, it does not replace it")
        self.assertTrue((self.harness / "skills" / "backlog" / "SKILL.md").is_file())
        self.assertTrue((self.harness / "market" / "hooks" / "backlog-session-start.sh").is_file())
        self.assertFalse(any(f["atom"] == "officium" for f in lock["files"].values()), "a preset writes no file")
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_a_preset_listed_with_its_own_items_installs_each_once(self):
        self.select({"skills": ["backlog"], "hooks": ["backlog-session-start"], "presets": ["officium"]})
        self.assertEqual(self.run_tool()[0], 0)
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_an_unknown_preset_is_an_error(self):
        for selection, message in [({"presets": ["nope"]}, "no preset called 'nope'"),
                                   ({"presets": "officium"}, "'presets' must be a list of preset ids"),
                                   ({"presets": [SKILL]}, f"no preset called '{SKILL}'")]:
            with self.subTest(message):
                self.select(selection)
                code, out = self.run_tool("--check")
                self.assertEqual(code, 1)
                self.assertIn(message, out)

    def test_a_typo_in_the_selection_is_an_error(self):
        self.select({"skils": [SKILL]})
        code, out = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("unknown key 'skils'", out)


if __name__ == "__main__":
    unittest.main()
