"""End-to-end tests for tools/marketplace.py against a small catalog in a throwaway git repository.

Run: python3 -m unittest discover -s tools/tests
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import english  # noqa: E402
import forms  # noqa: E402
import marketplace  # noqa: E402

ROLE = {"id": "tester", "kind": "role", "version": "1.0.0", "icon": "MdScience", "iconLibrary": "react-icons/md",
        "description": "A persona that tests things carefully.", "tags": ["testing"], "domains": ["universal"],
        "color": "112233", "palette": {"background": "112233", "text": "FFFFFF", "accents": "445566", "hover": "000000"},
        "toolTier": "comment"}
MOD = {"id": "careful", "kind": "mod", "version": "1.0.0", "icon": "MdShield", "iconLibrary": "react-icons/md",
       "description": "Every change is reviewed before it is declared done.", "tags": ["review"],
       "domains": ["universal"], "precedence": "correctness", "enforcement": "prompt"}
STEP = {"id": "run-tests", "kind": "step", "version": "1.0.0", "icon": "MdPlayArrow", "iconLibrary": "react-icons/md",
        "description": "Runs the project's test suite and reports the result.", "tags": ["testing"]}
FLOW = {"id": "check-loop", "kind": "flow", "version": "1.0.0", "icon": "MdLoop", "iconLibrary": "react-icons/md",
        "recommendedComplexity": "low", "cost": "finite", "description": "Runs the tests until they pass, three times at most.",
        "tags": ["testing"], "steps": [{"id": "run", "prompt": "Run the tests", "roleId": "tester", "modIds": ["careful"]},
                                       {"id": "again", "prompt": "Fix and rerun", "loopBackTo": {"stepId": "run", "maxIterations": 3}}]}
SKILL = {"id": "demo", "kind": "skill", "version": "1.0.0", "packaging": "traditional",
         "description": "A demonstration skill with one hook and one tool.", "tags": ["demo"],
         "hooks": [{"event": "UserPromptSubmit", "command": "hooks/prep.sh"}],
         "tools": [{"name": "demo", "command": ["python3", "demo.py"], "description": "Prints a greeting for tests."}],
         "install": {"exclude": ["evals/**"]}}
HOOK = {"id": "beat", "kind": "hook", "version": "1.0.0", "event": "postTool", "tools": ["shell"],
        "timeoutMs": 5000, "description": "Tells the board the session is still alive after each shell call.",
        "sends": {"to": "{{BOARD_API}}", "what": ["the card key", "the time of the call"]}}
META = {"id": "clone", "kind": "skill", "version": "1.0.0", "packaging": "meta",
        "description": "A meta-skill that interviews a person and renders a pack from the answers.",
        "tags": ["demo"], "form": {"questions": "interview/form.json", "profile": "templates/profile.md",
                                   "templates": "templates"}}


def question(qid: str, feeds: list[str], **extra) -> dict:
    return {"id": qid, "prompt": "How do you review a change?", "kind": "open", "required": True, "minutes": 5,
            "feeds": feeds, **extra}


def meta_form(*questions: dict, **extra) -> dict:
    return {"formVersion": "1.0.0", "role": "clone", "title": "Reviewer", "nameSlot": "name", **extra,
            "modules": [{"id": "core", "title": "Core", "optional": False, "purpose": "How the person reviews code.",
                         "sections": [{"id": "A", "title": "Review",
                                       "questions": list(questions) or [question("Q1", ["directives.review.philosophy"])]}]}]}
BOARD_ROLE = {**ROLE, "id": "builder", "description": "Implements a card's change within its category contract.",
              "tags": ["board", "phase-action"], "color": "7CC9A6", "palette": marketplace.BOARD_PHASES["action"],
              "toolTier": "write"}
BOARD_BODY = """# builder: Implements the Card

You implement one card.

## Phase Contract

- **Phase:** Action.
- **Mission:** Implement the change.
- **Must achieve:** Working code with tests.
- **Must not:** Expand scope.

## Expertise

- Building.

## Decision-Making Principles

1. **Small first.**

## Quality Standards

- Tested.

## Reference Baseline

- The Twelve-Factor App.

## Interaction Style

- **Before acting:** Reads the card.
- **Deliverable shape:** A diff.
- **Pushback:** On scope creep.
- **Voice:** Plain.

## Boundaries

- Review belongs to code-reviewer.
"""
CONFIG_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
                 "additionalProperties": False, "patternProperties": {"^\\$": {"description": "A comment."}},
                 "properties": {"limit": {"description": "Default: 3.", "type": "integer", "minimum": 1},
                                "names": {"type": "array", "items": {"$ref": "#/$defs/name"}}},
                 "$defs": {"name": {"type": "string", "minLength": 1}}}
CONFIG_EXAMPLE = {"$comment": "Illustrative.", "limit": 3, "names": ["a", "b"]}


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "tools/marketplace.py", *args], cwd=cwd, capture_output=True, text=True)


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class Catalog(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "tools", self.tmp / "tools", ignore=shutil.ignore_patterns("__pycache__", "tests"))
        shutil.copytree(REPO / "schemas", self.tmp / "schemas")
        (self.tmp / "marketplace.json").write_text(json.dumps({
            "schemaVersion": 1, "namespace": "test", "publisher": "tests", "source": "https://example.com/repo"}))
        for manifest in (ROLE, MOD, STEP, FLOW):
            self.write_market(manifest, f"# {manifest['id']}\n\nBody.\n")
        skill = self.tmp / "skills" / "demo"
        (skill / "hooks").mkdir(parents=True)
        (skill / "evals").mkdir()
        (skill / "SKILL.md").write_text("---\nname: demo\ndescription: >-\n  A demonstration skill\n  for tests.\n---\n\n# Demo\n")
        (skill / "demo.py").write_text("print('hello')\n")
        (skill / "hooks" / "prep.sh").write_text("#!/bin/sh\nexit 0\n")
        (skill / "evals" / "case.json").write_text("{}\n")
        (skill / "skill.json").write_text(json.dumps(SKILL, indent=2))
        git(self.tmp, "init", "-q")
        git(self.tmp, "config", "core.fileMode", "false")
        git(self.tmp, "add", "-A")
        git(self.tmp, "update-index", "--chmod=+x", "skills/demo/hooks/prep.sh")
        self.assertEqual(run(self.tmp, "inventory").returncode, 0)
        result = run(self.tmp, "lock")
        self.assertEqual(result.returncode, 0, result.stdout)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_market(self, manifest: dict, body: str | None = None) -> None:
        folder = self.tmp / "market" / marketplace.MARKET_KINDS[manifest["kind"]]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{manifest['id']}.json").write_text(json.dumps(manifest, indent=2))
        if body is not None:
            (folder / f"{manifest['id']}.md").write_text(body)

    def validate(self) -> subprocess.CompletedProcess:
        return run(self.tmp, "validate", "--no-language")

    def test_clean_catalog_is_valid(self):
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("5 atoms valid", result.stdout)

    def test_content_change_requires_a_version_bump(self):
        (self.tmp / "market/mods/careful.md").write_text("# careful\n\nA different rule.\n")
        result = self.validate()
        self.assertIn("careful: content changed but version is still 1.0.0", result.stdout)
        self.assertEqual(run(self.tmp, "lock").returncode, 1, "lock must refuse an unbumped change")
        self.write_market({**MOD, "version": "1.1.0"})
        self.assertIn("1.0.0 -> 1.1.0 is not recorded", self.validate().stdout)
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        self.assertEqual(self.validate().returncode, 0)

    def test_line_endings_do_not_change_the_hash(self):
        # A Windows checkout or editor can leave CRLF in the working tree of an LF repository.
        (self.tmp / "skills/demo/demo.py").write_bytes(b"print('hello')\r\n")
        (self.tmp / "market/mods/careful.md").write_bytes(b"# careful\r\n\r\nBody.\r\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_version_cannot_go_backwards(self):
        self.write_market({**MOD, "version": "0.9.0"})
        self.assertIn("version went backwards", self.validate().stdout)

    def test_unknown_manifest_key_is_an_error(self):
        self.write_market({**MOD, "precedense": "style"})
        self.assertIn("unknown key 'precedense'", self.validate().stdout)

    def test_orphan_prompt_is_an_error(self):
        (self.tmp / "market/mods/ghost.md").write_text("# ghost\n")
        self.assertIn("ghost.md: no manifest next to it", self.validate().stdout)

    def test_broken_references_are_errors(self):
        flow = json.loads(json.dumps(FLOW))
        flow["steps"][0]["modIds"] = ["missing"]
        flow["steps"][1]["loopBackTo"]["stepId"] = "later"
        self.write_market(flow)
        out = self.validate().stdout
        self.assertIn("unknown atom 'missing'", out)
        self.assertIn("loopBackTo 'later' is not this or an earlier step", out)

    def with_step_ref(self, ref: str) -> None:
        flow = json.loads(json.dumps(FLOW))
        flow["version"] = "1.1.0"
        flow["steps"][0]["stepRef"] = ref
        self.write_market(flow)

    def test_step_ref_must_name_an_existing_step(self):
        self.with_step_ref("missing-step")
        self.assertIn("step run: unknown atom 'missing-step'", self.validate().stdout)
        self.with_step_ref("careful")
        self.assertIn("step run: 'careful' is a mod, expected step", self.validate().stdout)
        self.with_step_ref("run-tests@2")
        self.assertIn("step run: 'run-tests@2' does not match run-tests 1.0.0", self.validate().stdout)

    def test_step_ref_is_not_in_the_projection(self):
        self.with_step_ref("run-tests@^1")
        self.assertEqual(run(self.tmp, "inventory").returncode, 0)
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        inventory = json.loads((self.tmp / "market/inventory.json").read_text())
        steps = next(f for f in inventory["flows"] if f["name"] == "check-loop")["steps"]
        self.assertEqual(steps, [{"id": "run", "prompt": "Run the tests", "roleId": "tester", "modIds": ["careful"]},
                                 {"id": "again", "prompt": "Fix and rerun",
                                  "loopBackTo": {"stepId": "run", "maxIterations": 3}}])

    def with_notes(self, note_types: list[dict] | None, bindings: list[dict] | None = None) -> None:
        flow = json.loads(json.dumps(FLOW))
        flow["version"] = "1.1.0"
        if note_types is not None:
            flow["noteTypes"] = note_types
        if bindings is not None:
            flow["steps"][0]["noteBindings"] = bindings
        self.write_market(flow)

    NOTE_TYPES = [{"id": "CoreVision", "description": "The root product thesis."},
                  {"id": "BuyerObjection", "description": "Why a prospect hesitates."}]

    def test_note_bindings_validate_and_project(self):
        self.with_notes(self.NOTE_TYPES, [{"type": "BuyerObjection", "mode": "primary-input"},
                                          {"type": "CoreVision", "mode": "read-context"}])
        self.assertEqual(run(self.tmp, "inventory").returncode, 0)
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        flow = next(f for f in json.loads((self.tmp / "market/inventory.json").read_text())["flows"]
                    if f["name"] == "check-loop")
        self.assertEqual(flow["noteTypes"], self.NOTE_TYPES)
        self.assertEqual(flow["steps"][0]["noteBindings"],
                         [{"type": "BuyerObjection", "mode": "primary-input"},
                          {"type": "CoreVision", "mode": "read-context"}])

    def test_note_binding_to_an_undeclared_type_is_an_error(self):
        self.with_notes(self.NOTE_TYPES, [{"type": "RawFeatureIdea", "mode": "primary-input"}])
        self.assertIn("noteBindings type 'RawFeatureIdea' is not one of the flow's noteTypes", self.validate().stdout)

    def test_note_binding_on_a_flow_with_no_note_types_is_an_error(self):
        self.with_notes(None, [{"type": "CoreVision", "mode": "read-context"}])
        self.assertIn("noteBindings type 'CoreVision' is not one of the flow's noteTypes", self.validate().stdout)

    def test_note_binding_mode_is_closed(self):
        self.with_notes(self.NOTE_TYPES, [{"type": "CoreVision", "mode": "maybe"}])
        result = self.validate()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("mode", result.stdout)

    def test_duplicate_note_type_and_double_binding_are_errors(self):
        self.with_notes(self.NOTE_TYPES + [{"id": "CoreVision", "description": "Again."}])
        self.assertIn("duplicate noteTypes id 'CoreVision'", self.validate().stdout)
        self.with_notes(self.NOTE_TYPES, [{"type": "CoreVision", "mode": "read-context"},
                                          {"type": "CoreVision", "mode": "primary-input"}])
        self.assertIn("step run: note type 'CoreVision' is bound twice", self.validate().stdout)

    def board_role(self, body: str = BOARD_BODY, **changes) -> None:
        self.write_market({**BOARD_ROLE, **changes}, body)

    def test_board_role_following_the_template_is_valid(self):
        self.board_role()
        self.assertEqual(run(self.tmp, "inventory").returncode, 0)
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_board_role_needs_one_known_phase(self):
        self.board_role(tags=["board"])
        self.assertIn("a board role carries exactly one of phase-refine", self.validate().stdout)
        self.board_role(tags=["board", "phase-action", "phase-review"])
        self.assertIn("a board role carries exactly one of", self.validate().stdout)
        self.board_role(tags=["board", "phase-testing"])
        self.assertIn("a board role carries exactly one of", self.validate().stdout)

    def test_role_needs_a_known_tool_tier(self):
        self.write_market({**ROLE, "toolTier": None})
        self.assertIn("toolTier", self.validate().stdout)
        self.write_market({**ROLE, "toolTier": "admin"})
        self.assertIn("toolTier", self.validate().stdout)

    def test_board_role_in_a_read_phase_is_capped_at_comment(self):
        self.board_role(toolTier="write", tags=["board", "phase-review"],
                        color=marketplace.BOARD_PHASES["review"]["background"],
                        palette=marketplace.BOARD_PHASES["review"])
        self.assertIn("a board role in phase review has toolTier 'write'; the ceiling is comment", self.validate().stdout)
        self.board_role(toolTier="comment", tags=["board", "phase-review"],
                        color=marketplace.BOARD_PHASES["review"]["background"],
                        palette=marketplace.BOARD_PHASES["review"])
        self.assertEqual(run(self.tmp, "inventory").returncode, 0)
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_phase_tag_needs_the_board_tag(self):
        self.write_market({**MOD, "version": "1.1.0", "tags": ["review", "phase-review"]})
        self.assertIn("tag 'phase-review' is only for board roles", self.validate().stdout)

    def test_board_role_wears_its_phase_palette_and_no_model_hint(self):
        self.board_role(color="112233")
        self.assertIn("a board role in phase action uses color 7CC9A6", self.validate().stdout)
        self.board_role(betterOn="anthropic/claude-opus-4.6")
        self.assertIn("a board role has no betterOn", self.validate().stdout)

    def test_board_role_prompt_follows_the_anatomy(self):
        self.board_role(BOARD_BODY.replace("## Reference Baseline", "## References"))
        self.assertIn("sections must be ['Phase Contract'", self.validate().stdout)
        self.board_role(BOARD_BODY.replace("**Must not:**", "**Avoid:**"))
        self.assertIn("## Phase Contract needs the bullets **Must not:**", self.validate().stdout)
        self.board_role(BOARD_BODY.replace("- Building.", "- Building.- **Testing:** Too."))
        self.assertIn("a list item is glued to the sentence before it", self.validate().stdout)
        self.board_role(BOARD_BODY.replace("1. **Small first.**", "1. **Small first.** Always.2. **Then fast.**"))
        self.assertIn("a list item is glued to the sentence before it", self.validate().stdout)
        self.board_role(BOARD_BODY + "word " * marketplace.BOARD_MAX_WORDS)
        self.assertIn("a board role's prompt stays under", self.validate().stdout)

    def test_runtime_enforcement_must_match(self):
        self.write_market({**MOD, "enforcement": "runtime"})
        self.assertIn("enforcement 'runtime' needs a runtime block", self.validate().stdout)

    def test_skill_front_matter_name_must_match(self):
        (self.tmp / "skills/demo/SKILL.md").write_text("---\nname: other\ndescription: x\n---\n")
        self.assertIn("front matter name 'other' must be 'demo'", self.validate().stdout)

    def test_hook_must_be_executable(self):
        git(self.tmp, "update-index", "--chmod=-x", "skills/demo/hooks/prep.sh")
        self.assertIn("is not executable in git", self.validate().stdout)

    def test_stale_inventory_is_an_error(self):
        (self.tmp / "market/inventory.json").write_text("{}\n")
        self.assertIn("inventory.json is out of date", self.validate().stdout)

    def test_removal_needs_explicit_permission(self):
        for suffix in (".json", ".md"):
            (self.tmp / "market/steps" / f"run-tests{suffix}").unlink()
        run(self.tmp, "inventory")
        self.assertIn("run-tests: in the lock but gone", self.validate().stdout)
        self.assertEqual(run(self.tmp, "lock").returncode, 1)
        self.assertEqual(run(self.tmp, "lock", "--allow-removal").returncode, 0)
        self.assertEqual(self.validate().returncode, 0)

    def test_build_is_content_addressed_and_deterministic(self):
        out1, out2 = self.tmp / "dist1", self.tmp / "dist2"
        self.assertEqual(run(self.tmp, "build", "--out", str(out1)).returncode, 0)
        self.assertEqual(run(self.tmp, "build", "--out", str(out2)).returncode, 0)
        index1 = json.loads((out1 / "index.json").read_text())
        index2 = json.loads((out2 / "index.json").read_text())
        self.assertEqual(index1["atoms"], index2["atoms"])
        demo = next(a for a in index1["atoms"] if a["id"] == "demo")
        self.assertEqual(demo["ref"], "test/demo@1.0.0")
        paths = {f["path"]: f for f in demo["files"]}
        self.assertNotIn("skills/demo/evals/case.json", paths, "install.exclude must drop evals")
        self.assertNotIn("skills/demo/skill.json", paths, "the manifest travels inline, not as a file")
        self.assertTrue(paths["skills/demo/hooks/prep.sh"]["executable"])
        for f in demo["files"]:
            blob = out1 / "blobs" / f["sha256"]
            self.assertEqual(marketplace.sha256_bytes(blob.read_bytes()), f["sha256"])
        store = marketplace.SchemaStore(REPO / "schemas")
        self.assertEqual(store.validate(index1, "index.schema.json"), [])
        matrix = json.loads((out1 / "compatibility.json").read_text())
        self.assertEqual(store.validate(matrix, "compatibility.schema.json"), [])
        self.assertIn("careful", matrix["mods"])
        for atom in index1["atoms"]:
            self.assertEqual(store.validate(atom["manifest"], f"{atom['kind']}.schema.json"), [])
        mod = next(a for a in index1["atoms"] if a["id"] == "careful")
        self.assertEqual([f["path"] for f in mod["files"]], ["market/mods/careful.md"])

    def add_skill_config(self, example: dict) -> None:
        skill = self.tmp / "skills" / "demo"
        (skill / "config.schema.json").write_text(json.dumps(CONFIG_SCHEMA, indent=2))
        (skill / "config.example.json").write_text(json.dumps(example, indent=2))
        (skill / "skill.json").write_text(json.dumps({**SKILL, "version": "1.1.0", "config": {
            "file": "demo.json", "schema": "config.schema.json", "example": "config.example.json"}}, indent=2))

    def add_mod_config(self, example: dict, manifest_example: str = "careful.config.example.json") -> None:
        folder = self.tmp / "market" / "mods"
        (folder / "careful.config.schema.json").write_text(json.dumps(CONFIG_SCHEMA, indent=2))
        (folder / "careful.config.example.json").write_text(json.dumps(example, indent=2))
        self.write_market({**MOD, "version": "1.1.0", "config": {
            "file": "careful.json", "schema": "careful.config.schema.json", "example": manifest_example}})

    def test_skill_config_example_must_validate(self):
        self.add_skill_config(CONFIG_EXAMPLE)
        self.assertEqual(run(self.tmp, "lock").returncode, 0, "a valid example must not block the lock")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.add_skill_config({**CONFIG_EXAMPLE, "limit": "ten", "typo": True})
        out = self.validate().stdout
        self.assertIn("skills/demo/config.example.json $.limit: expected integer", out)
        self.assertIn("skills/demo/config.example.json $: unknown key 'typo'", out)

    def test_config_schema_must_be_an_object_schema_within_the_subset(self):
        self.add_skill_config(CONFIG_EXAMPLE)
        schema = self.tmp / "skills/demo/config.schema.json"
        schema.write_text(json.dumps({"type": "array"}))
        self.assertIn('needs a top-level "type": "object"', self.validate().stdout)
        schema.write_text("{not json")
        self.assertIn("config.schema.json: not valid JSON", self.validate().stdout)
        schema.write_text(json.dumps({**CONFIG_SCHEMA, "properties": {"limit": {"anyOf": [{"type": "integer"}]}}}))
        self.assertIn("$.properties.limit: unsupported keyword 'anyOf'", self.validate().stdout)

    def test_mod_config_ships_next_to_the_mod(self):
        self.add_mod_config(CONFIG_EXAMPLE)
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("5 atoms valid", result.stdout, "config companions are not manifests")
        out = self.tmp / "dist"
        self.assertEqual(run(self.tmp, "build", "--out", str(out)).returncode, 0)
        index = json.loads((out / "index.json").read_text())
        mod = next(a for a in index["atoms"] if a["id"] == "careful")
        self.assertEqual([f["path"] for f in mod["files"]], [
            "market/mods/careful.config.example.json", "market/mods/careful.config.schema.json",
            "market/mods/careful.md"])

    def test_mod_config_example_must_validate(self):
        self.add_mod_config({"limit": -1})
        self.assertIn("market/mods/careful.config.example.json $.limit: below the minimum 1", self.validate().stdout)

    def test_mod_config_names_and_orphans(self):
        self.add_mod_config(CONFIG_EXAMPLE, manifest_example="example.json")
        out = self.validate().stdout
        self.assertIn("$.config.example: \"example.json\" does not match", out)
        self.assertIn("careful.config.example.json: no manifest declares it as config.example", out)

    def add_hook(self, manifest: dict | None = None, scripts: tuple[str, ...] = ("sh", "ps1"),
                 fallback: str | None = "# beat: Keep the Board Alive\n\nReport your status every ten minutes.\n") -> None:
        folder = self.tmp / "market" / "hooks"
        folder.mkdir(parents=True, exist_ok=True)
        manifest = manifest or HOOK
        (folder / f"{manifest['id']}.json").write_text(json.dumps(manifest, indent=2))
        for suffix in scripts:
            (folder / f"{manifest['id']}.{suffix}").write_text("#!/bin/sh\nexit 0\n" if suffix == "sh" else "exit 0\n")
        if fallback is not None:
            (folder / f"{manifest['id']}.md").write_text(fallback)

    def test_hook_is_an_atom_with_scripts_and_a_fallback(self):
        self.add_hook()
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("6 atoms valid", result.stdout)
        self.assertIn("beat", json.loads((self.tmp / "marketplace.lock.json").read_text())["atoms"])
        self.assertNotIn("hooks", json.loads((self.tmp / "market/inventory.json").read_text()),
                         "Fluxor's inventory has no hooks")
        out = self.tmp / "dist"
        self.assertEqual(run(self.tmp, "build", "--out", str(out)).returncode, 0)
        index = json.loads((out / "index.json").read_text())
        beat = next(a for a in index["atoms"] if a["id"] == "beat")
        self.assertEqual(beat["kind"], "hook")
        self.assertEqual(beat["ref"], "test/beat@1.0.0")
        self.assertEqual([f["path"] for f in beat["files"]],
                         ["market/hooks/beat.md", "market/hooks/beat.ps1", "market/hooks/beat.sh"])
        self.assertEqual(beat["manifest"]["sends"], HOOK["sends"])
        store = marketplace.SchemaStore(REPO / "schemas")
        self.assertEqual(store.validate(index, "index.schema.json"), [])
        self.assertEqual(store.validate(beat["manifest"], "hook.schema.json"), [])
        self.assertEqual(run(self.tmp, "list", "hook").stdout.split()[:2], ["hook", "beat"])

    def test_hook_that_sends_nothing_says_null(self):
        self.add_hook({**HOOK, "sends": None}, scripts=("ps1",))
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_hook_refusals(self):
        cases = [
            ({**HOOK, "event": "beforeLunch"}, ("sh",), True, "event 'beforeLunch' is not one of"),
            (HOOK, (), True, "needs a script, beat.sh or beat.ps1"),
            (HOOK, ("sh",), False, "missing or empty market/hooks/beat.md"),
            ({k: v for k, v in HOOK.items() if k != "sends"}, ("sh",), True, "missing required key 'sends'"),
            ({**HOOK, "sends": {"to": "example.com"}}, ("sh",), True, "missing required key 'what'"),
            ({**HOOK, "event": "stop"}, ("sh",), True, "tools only apply to preTool, postTool and postToolFailure"),
            ({**HOOK, "notifications": ["idle"]}, ("sh",), True, "notifications only apply to the notification"),
        ]
        for manifest, scripts, fallback, message in cases:
            with self.subTest(message):
                shutil.rmtree(self.tmp / "market" / "hooks", ignore_errors=True)
                self.add_hook(manifest, scripts=scripts, fallback="# beat: Fallback\n\nRead me.\n" if fallback else None)
                result = self.validate()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(message, result.stdout)

    def test_orphan_hook_script_is_an_error(self):
        (self.tmp / "market" / "hooks").mkdir(parents=True)
        (self.tmp / "market/hooks/ghost.sh").write_text("#!/bin/sh\n")
        self.assertIn("market/hooks/ghost.sh: no manifest next to it", self.validate().stdout)

    def add_preset(self, items: list, **extra) -> None:
        folder = self.tmp / "market" / "presets"
        folder.mkdir(parents=True, exist_ok=True)
        manifest = {"id": "starter", "kind": "preset", "version": "1.0.0", "title": "Starter kit",
                    "description": "Everything a new project needs to start working the board.", "items": items, **extra}
        (folder / "starter.json").write_text(json.dumps(manifest, indent=2))

    def test_preset_is_an_atom_with_no_files(self):
        # card://JAVA-161
        self.add_hook()
        # card://JAVA-835: a skill's params are its config file, so they nest like one.
        params = {"project": {"id": "{{PROJECT_ID}}"}, "minutes": 10, "prefixes": ["A"], "strict": True}
        self.add_preset([{"key": "demo", "params": params}, {"key": "beat"}])
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        out = self.tmp / "dist"
        self.assertEqual(run(self.tmp, "build", "--out", str(out)).returncode, 0)
        index = json.loads((out / "index.json").read_text())
        starter = next(a for a in index["atoms"] if a["id"] == "starter")
        self.assertEqual((starter["kind"], starter["files"]), ("preset", []))
        self.assertEqual(starter["manifest"]["items"][0]["params"], params)
        store = marketplace.SchemaStore(REPO / "schemas")
        self.assertEqual(store.validate(index, "index.schema.json"), [])
        self.assertEqual(run(self.tmp, "list", "preset").stdout.split()[:2], ["preset", "starter"])

    def test_preset_refusals(self):
        (self.tmp / "meta-skills" / "clone").mkdir(parents=True)
        (self.tmp / "meta-skills" / "clone" / "skill.json").write_text(json.dumps(META))
        self.add_hook()
        cases = [
            ([{"key": "ghost"}], "item 'ghost' is not an atom of this market"),
            ([{"key": "tester"}], "item 'tester' is a role; a preset lists skills and hooks"),
            ([{"key": "clone"}], "item 'clone' is a meta-skill"),
            ([{"key": "beat"}, {"key": "beat"}], "item 'beat' is listed twice"),
            ([{"key": "demo", "params": {"limit": None}}], "$.items[0].params.limit: expected ['string', 'number'"),
            ([{"key": "demo", "version": "1.0.0"}], "$.items[0]: unknown key 'version'"),
            ([], "$.items: needs at least 1 item(s)"),
        ]
        for items, message in cases:
            with self.subTest(message):
                self.add_preset(items)
                result = self.validate()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(message, result.stdout)
        self.add_preset([{"key": "demo"}])
        (self.tmp / "market/presets/inner.json").write_text(json.dumps(
            {"id": "inner", "kind": "preset", "version": "1.0.0", "title": "Inner kit",
             "description": "A preset that tries to list another preset.", "items": [{"key": "starter"}]}))
        self.assertIn("item 'starter' is a preset", self.validate().stdout)

    def template(self, **change) -> dict:
        base = {"id": "train", "title": "Release train", "description": "The next epic outranks the rest.",
                "placeholders": [{"key": "EPIC", "label": "The epic that ships next"}],
                "rules": [{"name": "Next", "reason": "It ships first.", "match": {"epics": ["{{EPIC}}"]},
                           "defaults": {"priority": "high", "sprint": "join"}}]}
        return {**base, **change}

    def test_precedence_template_is_accepted(self):
        # card://JAVA-1692: the market schema accepts a template and its validation passes.
        self.add_hook()
        self.add_preset([{"key": "demo"}], precedenceTemplates=[self.template()])
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_precedence_template_refusals(self):
        self.add_hook()
        rule = lambda match: [{"name": "N", "reason": "R", "match": match}]
        cases = [
            (self.template(rules=rule({"epics": ["{{OTHER}}"]})), "uses {{OTHER}} but does not declare it"),
            (self.template(rules=rule({"epics": ["plain"]})), "declares EPIC but no rule uses it"),
            (self.template(rules=rule({"categories": ["{{EPIC}}"]})), "may stand only in epics or tags"),
            (self.template(rules=rule({"epics": ["{{epic}}"]})), "has a malformed placeholder"),
            (self.template(rules=rule({"signals": ["touches-nothing"]}), placeholders=[]), "unknown value"),
            (self.template(rules=rule({"epics": ["{{EPIC}}"]}) * 21), "$.precedenceTemplates[0].rules: allows at most 20 item(s)"),
            (self.template(rules=[{"name": "N", "reason": "R", "match": {"owner": ["x"]}}]), "unknown key 'owner'"),
        ]
        for template, message in cases:
            with self.subTest(message):
                self.add_preset([{"key": "demo"}], precedenceTemplates=[template])
                result = self.validate()
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(message, result.stdout)

    def test_precedence_template_token_grammar_matches_the_shared_fixture(self):
        # The Java fill (PrecedenceTemplates.tokens) reads the same file.
        cases = json.loads((REPO / "tools/tests/precedence-template-tokens.json").read_text())["cases"]
        for case in cases:
            with self.subTest(case["value"]):
                self.assertEqual(marketplace.value_tokens(case["value"]), case["tokens"])

    def test_build_refuses_an_invalid_catalog(self):
        self.write_market({**MOD, "precedence": "vibes"})
        self.assertEqual(run(self.tmp, "build", "--out", str(self.tmp / "dist")).returncode, 1)

    def assert_locks_clean(self) -> None:
        """`lock` refuses any finding but a stale lock, so it passing means the form is clean."""
        out = run(self.tmp, "lock")
        self.assertEqual(out.returncode, 0, out.stdout)

    def add_meta_skill(self, manifest: dict | None = None, folder: str = "meta-skills",
                       template: str = "# Reviewer — {name}\n\n{directives.review.philosophy}\n",
                       form: dict | None = None,
                       profile: str = "# Profile — {name}\n\n- {directives.review.philosophy}\n") -> None:
        skill = self.tmp / folder / "clone"
        (skill / "interview").mkdir(parents=True, exist_ok=True)
        (skill / "templates" / "agents").mkdir(parents=True, exist_ok=True)
        form = form or meta_form()
        files = {
            "SKILL.md": "---\nname: clone\ndescription: Interviews a person and renders a pack.\n---\n",
            "interview/form.json": json.dumps(form, indent=2),
            "interview/questions.md": forms.render_markdown(form),
            "templates/profile.md": profile,
            "templates/agents/reviewer.md": template,
            "skill.json": json.dumps(manifest or META, indent=2),
        }
        for rel, text in files.items():
            (skill / rel).write_text(text, encoding="utf-8")

    def test_meta_skill_is_a_skill_with_a_form(self):
        self.add_meta_skill()
        self.assertEqual(run(self.tmp, "lock").returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("6 atoms valid", result.stdout)
        out = self.tmp / "dist"
        self.assertEqual(run(self.tmp, "build", "--out", str(out)).returncode, 0)
        clone = next(a for a in json.loads((out / "index.json").read_text())["atoms"] if a["id"] == "clone")
        self.assertEqual((clone["kind"], clone["manifest"]["packaging"]), ("skill", "meta"))
        self.assertIn("skills/clone/templates/agents/reviewer.md", [f["path"] for f in clone["files"]],
                      "a meta-skill installs like any skill")

    def test_meta_skill_templates_use_only_declared_slots(self):
        self.add_meta_skill(template="# Reviewer — {name}\n\n{directives.review.nitpicks}\n")
        self.assertIn("meta-skills/clone/templates/agents/reviewer.md: uses {directives.review.nitpicks}, "
                      "which templates/profile.md does not declare", self.validate().stdout)

    def test_meta_skill_form_rules(self):
        self.add_meta_skill({**META, "form": {"questions": "interview/missing.md", "profile": "templates/profile.md"}})
        out = self.validate().stdout
        self.assertIn("form.questions 'interview/missing.md' does not exist", out)
        self.assertIn("form.profile and form.templates go together", out)
        self.add_meta_skill({k: v for k, v in META.items() if k != "form"})
        self.assertIn("packaging 'meta' needs a form block", self.validate().stdout)
        self.add_meta_skill({**META, "packaging": "traditional"})
        self.assertIn("a form block needs packaging 'meta'", self.validate().stdout)
        self.add_meta_skill({**META, "form": {**META["form"], "questions": "../questions.md"}})
        self.assertIn("form.questions '../questions.md' must stay inside the skill folder", self.validate().stdout)
        self.add_meta_skill({**META, "form": {**META["form"], "questions": "interview/questions.md"}})
        self.assertIn("form.questions must be a form.json (schemas/form.schema.json)", self.validate().stdout)

    def test_meta_skill_form_must_name_its_skill_and_match_the_schema(self):
        self.add_meta_skill(form={**meta_form(), "role": "someone-else"})
        self.assertIn("meta-skills/clone/interview/form.json: role 'someone-else' must be 'clone'",
                      self.validate().stdout)
        self.add_meta_skill(form={**meta_form(), "modules": []})
        self.assertIn("meta-skills/clone/interview/form.json $.modules", self.validate().stdout)

    def test_coverage_every_slot_is_fed(self):
        profile = "# Profile — {name}\n\n- {directives.review.philosophy}\n- {directives.review.tone}\n"
        template = "# Reviewer — {name}\n\n{directives.review.philosophy}\n{directives.review.tone}\n"
        self.add_meta_skill(profile=profile, template=template)
        self.assertIn("meta-skills/clone/interview/form.json: no question feeds {directives.review.tone}",
                      self.validate().stdout)
        # A slot synthesized across the whole interview counts as fed.
        self.add_meta_skill(profile=profile, template=template, form=meta_form(
            derived={"directives.review.tone": "Read across every answer, not from one question."}))
        self.assert_locks_clean()

    def test_coverage_every_question_feeds_or_captures(self):
        self.add_meta_skill(form=meta_form(question("Q1", ["directives.review.philosophy"]), question("Q2", [])))
        self.assertIn("meta-skills/clone/interview/form.json: Q2 feeds no slot and captures nothing",
                      self.validate().stdout)
        self.add_meta_skill(form=meta_form(question("Q1", ["directives.review.philosophy"]),
                                           question("Q2", [], captures=["decisions"])))
        self.assert_locks_clean()
        self.add_meta_skill(form=meta_form(question("Q1", ["directives.review.nitpicks"])))
        self.assertIn("Q1 feeds {directives.review.nitpicks}, which the profile does not declare",
                      self.validate().stdout)

    def test_coverage_every_slot_is_rendered_or_profile_only(self):
        self.add_meta_skill(template="# Reviewer — {name}\n")
        self.assertIn("no template renders {directives.review.philosophy}: use it in an artifact or mark it "
                      "profileOnly", self.validate().stdout)
        only = {"directives.review.philosophy": "Context for people reading the profile, not for work."}
        self.add_meta_skill(template="# Reviewer — {name}\n", form=meta_form(profileOnly=only))
        self.assert_locks_clean()
        self.add_meta_skill(form=meta_form(profileOnly=only))
        self.assertIn("profileOnly names {directives.review.philosophy}, but a template renders it",
                      self.validate().stdout)

    def test_forms_renders_questions_md_and_check_catches_drift(self):
        self.add_meta_skill()
        target = self.tmp / "meta-skills/clone/interview/questions.md"
        target.write_text("# Interview\n\nEdited by hand.\n", encoding="utf-8")
        self.assertIn("meta-skills/clone/interview/questions.md is out of date: run `tools/marketplace.py forms`",
                      self.validate().stdout)
        check = run(self.tmp, "forms", "--check")
        self.assertEqual(check.returncode, 1)
        self.assertIn("meta-skills/clone/interview/questions.md is out of date", check.stdout)
        self.assertIn("Edited by hand", target.read_text(encoding="utf-8"), "--check writes nothing")
        self.assertEqual(run(self.tmp, "forms").returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), forms.render_markdown(meta_form()))
        self.assertEqual(run(self.tmp, "forms", "--check").returncode, 0)

    def test_meta_skill_lives_in_meta_skills(self):
        self.add_meta_skill(folder="skills")
        self.assertIn("skills/clone/skill.json: a meta-skill lives in meta-skills/", self.validate().stdout)

    def test_meta_skill_profile_that_is_not_utf8_is_reported(self):
        self.add_meta_skill()
        (self.tmp / "meta-skills/clone/templates/profile.md").write_bytes("# Profile — {name}\n".encode("cp1252"))
        self.assertIn("meta-skills/clone/templates/profile.md: not UTF-8", self.validate().stdout)


def contrast(a: str, b: str) -> float:
    def luminance(hex_: str) -> float:
        c = [int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class Units(unittest.TestCase):
    def test_board_phase_text_passes_wcag_aa(self):
        for phase, p in marketplace.BOARD_PHASES.items():
            for surface in ("background", "hover"):
                self.assertGreaterEqual(contrast(p["text"], p[surface]), 4.5, f"{phase} text on {surface}")

    def test_globs(self):
        match = marketplace.glob_match
        self.assertTrue(match("evals/fixtures/a.html", ["evals/**"]))
        self.assertTrue(match("scripts/__pycache__/x.pyc", ["**/__pycache__/**"]))
        self.assertTrue(match("x.pyc", ["**/*.pyc"]))
        self.assertFalse(match("scripts/evals.py", ["evals/**"]))
        self.assertFalse(match("a/b.md", ["*.md"]))

    def test_front_matter_folded(self):
        fm = marketplace.front_matter("---\nname: x\ndescription: >-\n  one\n  two\n---\nbody\n")
        self.assertEqual(fm, {"name": "x", "description": "one two"})

    def test_version_order(self):
        key = marketplace.version_key
        self.assertLess(key("1.2.3-beta"), key("1.2.3"))
        self.assertLess(key("1.9.0"), key("1.10.0"))

    def test_version_ranges(self):
        ok = marketplace.version_satisfies
        self.assertTrue(ok("1.4.2", "1"))
        self.assertFalse(ok("2.0.0", "1"))
        self.assertTrue(ok("1.2.9", "1.2"))
        self.assertFalse(ok("1.3.0", "1.2"))
        self.assertTrue(ok("1.2.3", "1.2.3"))
        self.assertFalse(ok("1.2.4", "1.2.3"))
        self.assertTrue(ok("1.9.0", "^1.2"))
        self.assertFalse(ok("1.1.0", "^1.2"))
        self.assertFalse(ok("0.3.0", "^0.2"))
        self.assertTrue(ok("1.2.7", "~1.2.3"))
        self.assertFalse(ok("1.3.0", "~1.2.3"))

    def test_schema_subset(self):
        store = marketplace.SchemaStore(REPO / "schemas")
        self.assertEqual(store.validate(MOD, "mod.schema.json"), [])
        errors = store.validate({**MOD, "tags": ["Bad Tag"], "version": "1"}, "mod.schema.json")
        self.assertTrue(any("tags[0]" in e for e in errors), errors)
        self.assertTrue(any(".version" in e for e in errors), errors)

    def test_pattern_properties(self):
        store = marketplace.SchemaStore(REPO / "schemas")
        schema = {"type": "object", "additionalProperties": False,
                  "patternProperties": {"^\\$": {"type": "string"}, "^[A-Z][0-9]$": {"type": "integer"}},
                  "properties": {"name": {"type": "string"}}}
        store.cache["t.json"] = schema
        self.assertEqual(store.validate({"$comment": "x", "A1": 3, "name": "n"}, "t.json"), [])
        errors = store.validate({"$comment": 1, "A1": "three", "typo": 0}, "t.json")
        self.assertIn("$.$comment: expected string, got int", errors)
        self.assertIn("$.A1: expected integer, got str", errors)
        self.assertIn("$: unknown key 'typo'", errors)

    def test_unsupported_keywords(self):
        find = marketplace.unsupported_keywords
        self.assertEqual(find(CONFIG_SCHEMA), [])
        found = find({"type": "object", "properties": {"a": {"type": "strin", "format": "uri"}},
                      "patternProperties": {"(": {}}, "items": {"maxLength": 2, "multipleOf": 2}})
        self.assertIn("$.properties.a: unsupported keyword 'format'", found)
        self.assertIn("$.properties.a.type: unknown type 'strin'", found)
        self.assertIn("$.items: unsupported keyword 'multipleOf'", found)
        self.assertTrue(any("invalid regular expression '('" in f for f in found), found)

    def test_repository_config_examples_validate(self):
        atoms, _ = marketplace.load_catalog()
        declared = [a for a in atoms if (a.manifest.get("config") or {}).get("example")]
        self.assertTrue(declared)
        for atom in declared:
            self.assertEqual(marketplace.config_findings(atom), [], atom.id)

    def test_runnable_engine_files_stay_executable_in_git(self):
        # card://JAVA-310: editing over the WSL UNC path drops +x, and it slipped through review twice
        if not marketplace._tracked_cache():
            self.skipTest("not a git checkout")
        git_exec = marketplace.git_executables()
        for rel in ("tools/marketplace.py", "market/motor.py"):
            self.assertIn(rel, git_exec, f"{rel} lost its executable bit: git update-index --chmod=+x {rel}")

    def test_english_detector(self):
        self.assertTrue(english.is_spanish("Esta es una prueba para los usuarios"))  # lang:es: detector input
        self.assertTrue(english.is_spanish("Configuración del proyecto"))  # lang:es: detector input
        self.assertFalse(english.is_spanish("The anterior cingulate cortex monitors conflict"))
        self.assertFalse(english.is_spanish("A café résumé"))
        self.assertFalse(english.is_spanish("dejar de fumar  # lang:es: fixture"))

    def test_only_rule_of_seven_names_the_count(self):
        # card://JAVA-1636 INV-01: the number seven lives in one mod, its config, not in the other five
        for mod in ("competitor-gap-extractor", "idea-map-synthesizer", "micro-sale-copywriting",
                    "semantic-deduplicator", "progressive-disclosure"):
            text = "".join((REPO / "market" / "mods" / f"{mod}{suffix}").read_text(encoding="utf-8")
                           for suffix in (".json", ".md"))
            self.assertNotRegex(text, r"(?i)\bseven\b|\b7\b", mod)


if __name__ == "__main__":
    unittest.main()
