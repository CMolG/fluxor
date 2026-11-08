"""Tests for ceet-impersonator/scripts/validate_pack.py, on synthetic packs (ceet-core/tests/support.py).

Run: python3 -m unittest discover -s meta-skills/ceet-impersonator/tests -t meta-skills/ceet-impersonator/tests
"""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
CORE = SKILL.parent / "ceet-core"
sys.path.insert(0, str(CORE / "tests"))
import support  # noqa: E402
from support import cc  # noqa: E402

# Loaded by path: ceet-core's scripts folder, also on sys.path, has a validate_pack.py of its own.
_spec = importlib.util.spec_from_file_location("impersonator_validate_pack", SKILL / "scripts" / "validate_pack.py")
validate_pack = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_pack)

BACKEND = SKILL.parent / "ceet-backend-engineer"


class ValidatePack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        self.packs = self.tmp / ".harness" / "packs"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rendered(self, **kwargs) -> Path:
        pack = support.simulated_pack(BACKEND, self.packs, **kwargs)
        out = support.run("render_pack.py", "--project", str(self.tmp), "render", str(pack), "--write")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        return pack

    def errors(self, pack: Path) -> str:
        return " | ".join(validate_pack.validate(pack)[0])

    def test_a_complete_simulation_validates(self):
        self.assertEqual(validate_pack.validate(self.rendered())[0], [])

    def test_every_directive_needs_a_row(self):
        pack = support.simulated_pack(BACKEND, self.packs, drop_row=True)
        self.assertIn("each needs a sourced row or an explicit unknown", self.errors(pack))

    def test_a_populated_row_needs_a_source(self):
        pack = support.simulated_pack(BACKEND, self.packs, unsourced=True)
        self.assertIn("no source (a URL, a commit, or `doc: <document>`", self.errors(pack))

    def test_an_unknown_row_cannot_back_a_populated_directive(self):
        pack = support.simulated_pack(BACKEND, self.packs)
        rows = validate_pack.load_core().evidence_rows((pack / "evidence-map.md").read_text(encoding="utf-8"))
        ref, row = next((r, v) for r, v in rows.items() if v["confidence"] == "unknown")
        profile = support.load(pack / "cognitive-profile.json")
        support.set_path(profile, row["directive"], f"I work this way. [{ref}]")
        cc.write_json(pack / "cognitive-profile.json", profile)
        self.assertIn("whose confidence is unknown", self.errors(pack))

    def rows(self, pack: Path) -> dict[str, dict]:
        return validate_pack.load_core().evidence_rows((pack / "evidence-map.md").read_text(encoding="utf-8"))

    def cite(self, pack: Path, directive: str, refs: str) -> None:
        profile = support.load(pack / "cognitive-profile.json")
        support.set_path(profile, directive, f"I work this way. [{refs}]")
        cc.write_json(pack / "cognitive-profile.json", profile)

    def test_a_directive_cannot_borrow_another_directives_row(self):
        pack = support.simulated_pack(BACKEND, self.packs)
        rows = self.rows(pack)
        unknown = next(v for v in rows.values() if v["confidence"] == "unknown")
        borrowed = next(r for r, v in rows.items() if v["confidence"] != "unknown")
        self.cite(pack, unknown["directive"], borrowed)
        self.assertIn(f"cites {borrowed}, a row evidence-map.md gives to", self.errors(pack))

    def test_teachback_alone_cannot_back_a_simulated_directive(self):
        pack = support.simulated_pack(BACKEND, self.packs)
        sourced = next(v for v in self.rows(pack).values() if v["confidence"] != "unknown")
        self.cite(pack, sourced["directive"], "teachback")
        self.assertIn("cites none of its own sourced rows", self.errors(pack))

    def with_source(self, source: str) -> Path:
        pack = support.simulated_pack(BACKEND, self.packs)
        evidence = pack / "evidence-map.md"
        first = next(v for v in self.rows(pack).values() if v["confidence"] != "unknown")["source"]
        evidence.write_text(evidence.read_text(encoding="utf-8").replace(f"| {first} |", f"| {source} |", 1),
                            encoding="utf-8")
        return pack

    def test_a_hex_word_in_prose_is_not_a_commit(self):
        for prose in ("a defaced forum post", "an effaced slide deck"):
            with self.subTest(prose=prose):
                self.assertIn("no source", self.errors(self.with_source(prose)))
                shutil.rmtree(self.packs)

    def test_a_commit_is_the_bare_hash_or_prefixed(self):
        for commit in ("4f2e8a9b1c", "commit: 4f2e8a9", "commit: deadbeefcafe"):
            with self.subTest(commit=commit):
                self.assertNotIn("no source", self.errors(self.with_source(commit)))
                shutil.rmtree(self.packs)

    def test_the_evidence_map_carries_the_simulation_notice_too(self):
        pack = self.rendered()
        evidence = pack / "evidence-map.md"
        evidence.write_text(evidence.read_text(encoding="utf-8").replace(cc.SIMULATION_NOTICE, ""), encoding="utf-8")
        self.assertIn("evidence-map.md: missing the Simulation Notice", self.errors(pack))

    def test_a_private_individual_is_simulated_only_with_their_consent(self):
        pack = support.simulated_pack(BACKEND, self.packs)
        profile = support.load(pack / "cognitive-profile.json")
        profile["consent"]["basis"] = "operator-authorization"
        cc.write_json(pack / "cognitive-profile.json", profile)
        self.assertIn("basis", self.errors(pack))

    def test_a_pack_claiming_an_interview_is_refused(self):
        pack = self.rendered()
        profile = support.load(pack / "cognitive-profile.json")
        profile["source"] = "interview"
        cc.write_json(pack / "cognitive-profile.json", profile)
        self.assertIn("only writes simulated packs", self.errors(pack))

    def test_it_requires_ceet_core_2(self):
        fake = self.tmp / "ceet-core"
        fake.mkdir()
        (fake / "skill.json").write_text(json.dumps({"version": "1.4.0"}), encoding="utf-8")
        err = io.StringIO()
        with mock.patch.object(validate_pack, "CORE", fake), redirect_stderr(err):
            with self.assertRaises(SystemExit) as raised:
                validate_pack.load_core()
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("requires ceet-core@2, found 1.4.0", err.getvalue())
        with mock.patch.object(validate_pack, "CORE", self.tmp / "nowhere"), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                validate_pack.load_core()

    def test_the_manifest_requires_ceet_core_2(self):
        manifest = json.loads((SKILL / "skill.json").read_text(encoding="utf-8"))
        self.assertIn("ceet-core@2", manifest["requires"]["atoms"])

    def test_cli_exit_codes(self):
        good = self.rendered()
        interview = self.rendered(slug="claims-an-interview")
        profile = support.load(interview / "cognitive-profile.json")
        profile["source"] = "interview"
        cc.write_json(interview / "cognitive-profile.json", profile)
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(validate_pack.main([str(good)]), 0)
            self.assertEqual(validate_pack.main([str(interview), "--json"]), 1)
            self.assertEqual(validate_pack.main([str(self.tmp / "nowhere")]), 2)
        self.assertIn(f"pack {good.name}: ok", out.getvalue())
        self.assertIn('"valid": false', out.getvalue())


if __name__ == "__main__":
    unittest.main()
