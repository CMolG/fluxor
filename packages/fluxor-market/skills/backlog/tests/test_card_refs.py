"""Tests for scripts/card_refs.py against a throwaway git repository."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "card_refs.py"


class CardRefs(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "src").mkdir()
        (self.root / "src" / "client.ts").write_text(
            "// card://PROJ-12 [temporary]: retry 429s until the upstream SDK backs off itself\n"
            "export const retries = 3;\n"
            "// card://PROJ-7: totals are rounded per line, as the invoicing rules require\n"
        )
        (self.root / "src" / "legacy.py").write_text("# card://OLD-3: kept for imported invoices\n")
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_client.py").write_text(
            "# card://PROJ-12: reproduces the 429 storm\n# card://proj-9 is not a key\n"
        )
        (self.root / "notes.bin").write_bytes(b"card://PROJ-99")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        config = self.root / ".harness" / "config"
        config.mkdir(parents=True)
        (config / "backlog.json").write_text(json.dumps({
            "keyPrefix": "PROJ", "legacyKeyPrefixes": ["OLD"],
            "codeReferences": {"scheme": "card", "urlTemplate": "https://board.example.com/cards/{key}"}}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_script(self, *args, env=None):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.root), **(env or {})}
        env.pop("HARNESS_DIR", None)
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)

    def test_list_finds_both_kinds_and_legacy_keys(self):
        result = self.run_script("--json", "list")
        refs = json.loads(result.stdout)["references"]
        found = {(r["file"], r["key"], r["kind"]) for r in refs}
        self.assertEqual(found, {
            ("src/client.ts", "PROJ-12", "temporary"),
            ("src/client.ts", "PROJ-7", "rationale"),
            ("src/legacy.py", "OLD-3", "rationale"),
            ("tests/test_client.py", "PROJ-12", "rationale"),
        })

    def test_list_filters_by_key_and_prints_links(self):
        result = self.run_script("list", "PROJ-12")
        self.assertIn("<https://board.example.com/cards/PROJ-12>", result.stdout)
        self.assertIn("2 reference(s)", result.stdout)

    def test_only_tracked_files_count_and_without_git_the_tree_is_walked(self):
        (self.root / "src" / "draft.ts").write_text("// card://PROJ-5 [temporary]: not tracked yet\n")
        self.assertNotIn("PROJ-5", json.loads(self.run_script("--json", "keys").stdout)["keys"])
        shutil.rmtree(self.root / ".git")
        self.assertIn("PROJ-5", json.loads(self.run_script("--json", "keys").stdout)["keys"])

    def test_git_answers_for_a_repository_whose_owner_it_cannot_verify(self):
        # card://JAVA-838: WSL's tree read from Windows, where `git ls-files` said "dubious
        # ownership" and the walk that replaced it read the whole share file by file (80 s).
        (self.root / "src" / "draft.ts").write_text("// card://PROJ-5 [temporary]: not tracked yet\n")
        result = self.run_script("--json", "keys", env={"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"})
        keys = json.loads(result.stdout)["keys"]
        self.assertEqual(keys["PROJ-12"], {"temporary": 1, "rationale": 1})
        self.assertNotIn("PROJ-5", keys, "git listed the files, so the untracked one was not walked into")

    def test_keys_counts(self):
        counts = json.loads(self.run_script("--json", "keys").stdout)["keys"]
        self.assertEqual(counts["PROJ-12"], {"temporary": 1, "rationale": 1})

    def test_check_flags_closed_temporary_and_malformed(self):
        result = self.run_script("check", "--closed", "PROJ-12,PROJ-7")
        self.assertEqual(result.returncode, 1)
        self.assertIn("src/client.ts:1: PROJ-12 is closed", result.stdout)
        self.assertNotIn("PROJ-7 is closed", result.stdout, "rationale references stay after closing")
        self.assertIn("card://proj-9 is not a key of this project", result.stdout)

    def test_check_passes_when_nothing_is_stale(self):
        (self.root / "tests" / "test_client.py").write_text("# card://PROJ-12: reproduces the 429 storm\n")
        self.assertEqual(self.run_script("check", "--closed", "PROJ-7").returncode, 0)

    def test_documenting_the_format_is_neither_a_reference_nor_malformed(self):
        (self.root / "docs.md").write_text(
            "Write `card://PROJ-5 [temporary]: why` above the workaround, or `card://KEY`.\n"
            "```\n// card://PROJ-6: an example in a fenced block\n```\n"
            "The format is card://<KEY>. Tracked in card://PROJ-8.\n"
        )
        (self.root / "src" / "api.ts").write_text("// see card://KEY for the format\n")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        keys = json.loads(self.run_script("--json", "keys").stdout)["keys"]
        self.assertNotIn("PROJ-5", keys)
        self.assertNotIn("PROJ-6", keys)
        self.assertIn("PROJ-8", keys, "a reference in prose, outside code, is a real one")
        malformed = json.loads(self.run_script("--json", "check").stdout)["malformed"]
        self.assertEqual([m["file"] for m in malformed], ["tests/test_client.py"])

    def test_without_config_any_uppercase_prefix_counts(self):
        shutil.rmtree(self.root / ".harness")
        keys = json.loads(self.run_script("--json", "keys").stdout)["keys"]
        self.assertIn("OLD-3", keys)
        self.assertIn("PROJ-7", keys)

    def test_ignored_paths_are_neither_references_nor_malformed(self):
        config = self.root / ".harness" / "config" / "backlog.json"
        data = json.loads(config.read_text())
        data["codeReferences"]["ignore"] = ["tests/**"]
        config.write_text(json.dumps(data))
        refs = json.loads(self.run_script("--json", "list").stdout)["references"]
        self.assertNotIn("tests/test_client.py", {r["file"] for r in refs})
        result = self.run_script("check", "--closed", "PROJ-1")
        self.assertNotIn("proj-9", result.stdout)

    def commit(self, message, *paths):
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(target.read_text() + "x\n" if target.exists() else "x\n")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", message],
                       cwd=self.root, check=True)

    def test_touching_names_the_cards_of_recent_commits_newest_first(self):
        self.commit("fix(client): retry (PROJ-5)", "src/a.ts")
        self.commit("feat(client): timeouts (proj-6)", "src/a.ts", "src/b.ts")
        self.commit("chore: no card", "src/b.ts")
        result = self.run_script("touching", "src/a.ts", "src/b.ts")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [
            {"path": "src/a.ts", "cards": ["PROJ-6", "PROJ-5"]},
            {"path": "src/b.ts", "cards": ["PROJ-6"]},
        ])

    def test_touching_a_path_with_no_history_answers_no_cards(self):
        self.commit("fix(client): retry (PROJ-5)", "src/a.ts")
        result = self.run_script("touching", "src/never.ts")
        self.assertEqual(json.loads(result.stdout), [{"path": "src/never.ts", "cards": []}])

    def test_touching_a_path_git_cannot_read_exits_2(self):
        self.commit("fix(client): retry (PROJ-5)", "src/a.ts")
        result = self.run_script("touching", "../outside.ts")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot read", result.stderr)

    def test_touching_refuses_a_window_below_one_day(self):
        self.commit("fix(client): retry (PROJ-5)", "src/a.ts")
        self.assertEqual(self.run_script("touching", "src/a.ts", "--days", "0").returncode, 2)


if __name__ == "__main__":
    unittest.main()
