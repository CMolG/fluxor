"""Tests for ceet-autodiscover/scripts/detect.py, against the meta-skills in this repository.

Run: python3 -m unittest discover -s meta-skills/ceet-autodiscover/tests -t meta-skills/ceet-autodiscover/tests
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
META_SKILLS = SKILL.parent
sys.path.insert(0, str(SKILL / "scripts"))
import detect  # noqa: E402

BACKEND = META_SKILLS / "ceet-backend-engineer"
# A filled backend profile: the role line and no slot left.
FILLED = "> Role: **Backend Engineer**\n\nI split migrations into expand and contract.\n"
# A rendered pack's always-on core (pack contract v2): what makes a pack loadable.
CORE = "# Alex, backend engineer\n\nI split migrations into expand and contract.\n"
COMPANIONS = {"ceet-core", "ceet-autodiscover", "ceet-impersonator", "ceet-sub-agent-orchestration"}


class Detect(unittest.TestCase):
    def setUp(self):
        self.project = Path(tempfile.mkdtemp())
        self.packs = self.project / ".harness" / "packs"

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def report(self, request: str = "") -> dict:
        return detect.detect(request, self.project, [META_SKILLS], self.packs)

    def entry(self, report: dict, ceet: str) -> dict:
        return next(e for e in report["scoring"] if e["ceet"] == ceet)

    def add_pack(self, name: str, profile: str | None, data: dict | None = None, core: str | None = CORE,
                 manifest: dict | None = None, base: Path | None = None) -> Path:
        pack = (base or self.packs) / name
        pack.mkdir(parents=True)
        files = {"cognitive-profile.md": profile, "core.md": core,
                 "cognitive-profile.json": None if data is None else json.dumps(data),
                 "pack.json": None if manifest is None else json.dumps(manifest)}
        for file, text in files.items():
            if text is not None:
                (pack / file).write_text(text, encoding="utf-8")
        return pack

    def copy_role(self, skills: Path, name: str, keywords: list[str]) -> Path:
        """A copy of the backend role under another id, routed by `keywords`."""
        role = skills / name
        shutil.copytree(BACKEND, role)
        form = json.loads((role / "interview" / "form.json").read_text(encoding="utf-8"))
        form["role"], form["routing"] = name, {"keywords": keywords}
        (role / "interview" / "form.json").write_text(json.dumps(form), encoding="utf-8")
        return role

    def test_finds_the_fifteen_roles_and_no_companion(self):
        roles = {role.id for role in detect.find_roles([META_SKILLS])}
        self.assertEqual(len(roles), 15, sorted(roles))
        self.assertFalse(roles & COMPANIONS)
        self.assertIn("ceet-backend-engineer", roles)

    def test_role_titles_come_from_the_profile_template(self):
        titles = {role.id: role.title for role in detect.find_roles([META_SKILLS])}
        self.assertEqual(titles["ceet-backend-engineer"], "Backend Engineer")

    def test_recommends_backend_for_an_api_request(self):
        report = self.report("review my backend api migration")
        self.assertEqual(report["recommendation"]["primary"], "ceet-backend-engineer")
        self.assertIn("ceet-backend-engineer", report["detectedCEETs"])
        self.assertTrue(any(m.startswith("kw:") for m in report["scoring"][0]["matched"]))

    def test_recommends_copywriter_for_a_headline_request(self):
        self.assertEqual(self.report("rewrite my landing page headline")["recommendation"]["primary"], "ceet-copywriter")

    def test_no_recommendation_for_an_unrelated_request(self):
        report = self.report("the quick brown fox")
        self.assertIsNone(report["recommendation"]["primary"])
        self.assertEqual(report["detectedCEETs"], [])
        self.assertFalse(report["recommendation"]["needsInitialization"])

    def test_keywords_match_whole_words_only(self):
        roles = {role.id: role for role in detect.find_roles([META_SKILLS])}
        self.assertEqual(detect.score_request("quick fix", roles["ceet-frontend-engineer"]), (0, []))
        # `design` (1) and `design system` (2 words) both match.
        self.assertEqual(detect.score_request("a design system", roles["ceet-ui-designer"])[0], 3)

    def test_a_phrase_outweighs_a_shared_word_and_plurals_match(self):
        roles = {role.id: role for role in detect.find_roles([META_SKILLS])}
        self.assertEqual(detect.score_request("a discovery call", roles["ceet-sales"]), (2, ["kw:discovery call"]))
        self.assertEqual(detect.score_request("a discovery call", roles["ceet-product-manager"])[0], 1)
        self.assertEqual(detect.score_request("user interviews", roles["ceet-ux-researcher"])[1], ["kw:interview"])

    def test_an_id_token_that_is_a_keyword_counts_once(self):
        roles = {role.id: role for role in detect.find_roles([META_SKILLS])}
        self.assertEqual(detect.score_request("analytics", roles["ceet-data-analytics"]), (1, ["kw:analytics"]))

    def test_keywords_come_from_the_roles_form(self):
        self.assertFalse(hasattr(detect, "ROLE_KEYWORDS"))
        skills = self.project / "skills"
        self.copy_role(skills, "ceet-zookeeper", ["zebra feeding", "enclosure"])
        report = detect.detect("plan the zebra feeding rota", self.project, [skills], self.packs)
        self.assertEqual(report["recommendation"]["primary"], "ceet-zookeeper")
        self.assertEqual(report["scoring"][0]["matched"], ["kw:zebra feeding"])

    def test_a_folder_without_a_form_is_not_a_role(self):
        skills = self.project / "skills"
        role = self.copy_role(skills, "ceet-zookeeper", ["zebra"])
        (role / "interview" / "form.json").unlink()
        self.assertEqual(detect.find_roles([skills]), [])

    def test_the_shipped_template_does_not_count_as_initialized(self):
        report = self.report("review my backend api migration")
        self.assertEqual(report["initializedCEETs"], [])
        self.assertTrue(report["recommendation"]["needsInitialization"])

    def test_a_filled_pack_initializes_its_role(self):
        self.add_pack("backend-engineer-alex", FILLED)
        report = self.report("review my backend api migration")
        self.assertEqual(report["initializedCEETs"], ["ceet-backend-engineer"])
        self.assertFalse(report["recommendation"]["needsInitialization"])
        self.assertEqual(report["recommendation"]["packs"], [".harness/packs/backend-engineer-alex"])

    def test_a_pack_with_unfilled_slots_is_incomplete(self):
        template = (BACKEND / "templates" / "cognitive-profile.md").read_text(encoding="utf-8")
        self.add_pack("backend-engineer-draft", template)
        entry = self.entry(self.report(), "ceet-backend-engineer")
        self.assertFalse(entry["initialized"])
        self.assertEqual(entry["incompletePacks"][0]["path"], ".harness/packs/backend-engineer-draft")
        self.assertGreater(entry["incompletePacks"][0]["unfilledSlots"], 50)

    def test_a_pack_without_core_md_is_not_rendered(self):
        self.add_pack("backend-engineer-alex", FILLED, {"role": "ceet-backend-engineer"}, core=None)
        entry = self.entry(self.report(), "ceet-backend-engineer")
        self.assertFalse(entry["initialized"])
        self.assertEqual(entry["incompletePacks"][0]["missing"], ["core.md"])

    def test_cognitive_profile_json_alone_marks_a_pack(self):
        self.add_pack("sales-sam", None, {"role": "ceet-sales"}, core=None)
        entry = self.entry(self.report(), "ceet-sales")
        self.assertEqual(entry["incompletePacks"][0]["path"], ".harness/packs/sales-sam")

    def test_the_manifest_names_the_role_when_the_profile_json_does_not(self):
        self.add_pack("copy-cleo", None, manifest={"packId": "copy-cleo", "metaSkill": "ceet-copywriter@2.0.0"})
        self.assertEqual(self.report()["initializedCEETs"], ["ceet-copywriter"])

    def test_the_json_role_wins_over_the_markdown_line(self):
        self.add_pack("sales-sam", "# Profile\n\n> Role: **Backend Engineer**\n", {"role": "ceet-sales"})
        report = self.report()
        self.assertEqual(report["initializedCEETs"], ["ceet-sales"])

    def test_braces_that_are_not_slots_of_the_role_do_not_block(self):
        self.add_pack("backend-engineer-kim", "> Role: **Backend Engineer**\n\nKeys look like {tenant}/{id}.\n")
        self.assertTrue(self.entry(self.report(), "ceet-backend-engineer")["initialized"])

    def test_example_packs_are_reported_apart_from_the_users_own(self):
        # A rendered pack shipped in a sibling skill's examples/ folder: someone's example, not the user's.
        self.add_pack("backend-sample", FILLED, base=self.project / "skills" / "sample-skill" / "examples")
        report = detect.detect("backend", self.project, [META_SKILLS, self.project / "skills"], self.packs)
        entry = self.entry(report, "ceet-backend-engineer")
        self.assertEqual(entry["packs"], [])
        self.assertTrue(any(p.endswith("sample-skill/examples/backend-sample") for p in entry["examples"]), entry["examples"])

    def test_harness_dir_moves_the_packs_folder(self):
        with mock.patch.dict(os.environ, {"HARNESS_DIR": "custom-harness"}):
            self.assertEqual(detect.packs_directory(self.project, None), self.project / "custom-harness" / "packs")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HARNESS_DIR", None)
            self.assertEqual(detect.packs_directory(self.project, None), self.project / ".harness" / "packs")

    def test_project_root_prefers_the_explicit_then_the_environment(self):
        self.assertEqual(detect.project_root(str(self.project)), self.project.resolve())
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.project)}):
            self.assertEqual(detect.project_root(None), self.project.resolve())

    def test_no_roles_found_says_how_to_fix_it(self):
        report = detect.detect("backend", self.project, [self.project], self.packs)
        self.assertIsNone(report["recommendation"]["primary"])
        self.assertIn("--skills-dir", report["recommendation"]["reason"])

    def test_cli_prints_the_report_as_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = detect.main(["--request", "incident rollback", "--project", str(self.project),
                                "--skills-dir", str(META_SKILLS)])
        self.assertEqual(code, 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["schemaVersion"], detect.SCHEMA_VERSION)
        self.assertEqual(report["recommendation"]["primary"], "ceet-devops-sre")


if __name__ == "__main__":
    unittest.main()
