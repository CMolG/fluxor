"""market/hooks/officium-temporary-refs: an agent's move to review is refused while the card still
has `[temporary]` references in the code.

Runs the hook's scripts on crafted payloads inside a throwaway git project that carries a backlog
config, the backlog skill's card_refs.py and a session transcript (card://JAVA-838). The `.ps1`
twin runs the same cases where `pwsh` is on PATH, and is skipped otherwise.
Run: python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "market" / "hooks" / "officium-temporary-refs"
CARD_REFS = REPO / "skills" / "backlog" / "scripts" / "card_refs.py"
CARD_ID = "22222222-3333-4444-8555-666666666666"
OTHER_ID = "11111111-2222-3333-4444-555555555555"
KEY = "JAVA-7"


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class Project:
    """A git project with the backlog config, card_refs.py and a transcript."""

    def __init__(self, root: Path, config: dict | None = None) -> None:
        self.root = root
        (root / ".harness" / "config").mkdir(parents=True)
        if config is not False:
            config = config or {"provider": "officium", "mcpServer": "officium", "keyPrefix": "JAVA"}
            (root / ".harness" / "config" / "backlog.json").write_text(json.dumps(config), encoding="utf-8")
        scripts = root / ".harness" / "skills" / "backlog" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy(CARD_REFS, scripts / "card_refs.py")
        (root / "src").mkdir()
        git(root, "init", "-q")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "test")
        self.transcript = root / "transcript.jsonl"
        self.transcript.write_text("", encoding="utf-8")

    def source(self, text: str) -> None:
        (self.root / "src" / "a.py").write_text(text, encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "change")

    def remember(self, *lines: str) -> None:
        with self.transcript.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")


def card_answer(card_id: str, key: str, escaped: bool) -> str:
    """A transcript line carrying an Officium card, as Claude Code writes it: the MCP answer is a
    JSON string inside the line (its quotes escaped), and mcpMeta repeats it as an object."""
    card = {"id": card_id, "projectId": "11111111-2222-4333-8444-555555555555", "key": key, "status": "doing"}
    if escaped:
        return json.dumps({"type": "user", "content": json.dumps(card, separators=(",", ":"))}, separators=(",", ":"))
    return json.dumps({"type": "user", "mcpMeta": {"structuredContent": card}}, separators=(",", ":"))


def work_answer(card_id: str, key: str) -> str:
    work = {"items": [{"cardId": card_id, "cardKey": key, "actor": {"kind": "agent"}}]}
    return json.dumps({"type": "user", "content": json.dumps(work, separators=(",", ":"))}, separators=(",", ":"))


def move(status: str = "review", card_id: str = CARD_ID, operation: str = "cards.move",
         tool: str = "mcp__officium__query", **extra) -> dict:
    params = {"projectId": "11111111-2222-4333-8444-555555555555", "cardId": card_id, "status": status,
              "position": 0, "expectedVersion": 3, **extra}
    return {"tool_name": tool, "tool_input": {"operation": operation, "params": params}}


class Runner:
    command: list[str] = []

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = Project(self.tmp / "project")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_hook(self, payload: dict, project: Project | None = None, env_root: bool = True,
                 cwd: Path | None = None) -> subprocess.CompletedProcess:
        project = project or self.project
        payload = {"session_id": "s1", "hook_event_name": "PreToolUse", "cwd": str(cwd or project.root),
                   "transcript_path": str(project.transcript), "tool_use_id": "t1", **payload}
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PROJECT_DIR", "HARNESS_DIR")}
        if env_root:
            env["CLAUDE_PROJECT_DIR"] = str(project.root)
        return subprocess.run(self.command, input=json.dumps(payload), capture_output=True, text=True,
                              cwd=cwd or project.root, env=env, timeout=60)

    def assert_blocked(self, result: subprocess.CompletedProcess, key: str = KEY) -> None:
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn(key, result.stderr)
        self.assertIn("src/a.py:1:", result.stderr)
        self.assertIn(f"card://{key} [temporary]: drop the shim", result.stderr)
        self.assertIn("follow-up card", result.stderr)

    def assert_passes(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stderr.strip(), "")
        self.assertEqual(result.stdout.strip(), "")

    # --- the block, and what lifts it

    def test_a_move_to_review_with_a_temporary_reference_is_blocked(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\nx = 1\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_blocked(self.run_hook(move()))

    def test_it_passes_once_the_reference_is_gone(self):
        self.project.source("x = 1\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move()))

    def test_it_passes_once_the_reference_is_re_pointed_to_a_follow_up(self):
        self.project.source("# card://JAVA-8 [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move()))

    def test_a_rationale_reference_does_not_block(self):
        self.project.source(f"# card://{KEY}: why this exists\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move()))

    # --- only an Officium move to review

    def test_other_operations_statuses_and_tools_pass(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move(status="doing")))
        self.assert_passes(self.run_hook(move(operation="cards.update")))
        self.assert_passes(self.run_hook(move(tool="mcp__other__query")))
        self.assert_passes(self.run_hook({"tool_name": "Bash", "tool_input": {"command": "cards.move review"}}))

    def test_the_server_name_comes_from_the_config(self):
        project = Project(self.tmp / "custom", {"mcpServer": "tracker", "keyPrefix": "JAVA"})
        project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_blocked(self.run_hook(move(tool="mcp__tracker__query"), project))
        self.assert_passes(self.run_hook(move(), project))

    # --- the key

    def test_the_key_comes_from_a_card_answer_written_as_an_object(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=False))
        self.assert_blocked(self.run_hook(move()))

    def test_the_key_comes_from_a_work_entry(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(work_answer(OTHER_ID, "JAVA-9"), work_answer(CARD_ID, KEY))
        self.assert_blocked(self.run_hook(move()))

    def test_the_key_can_come_in_the_params(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.assert_blocked(self.run_hook(move(card_id=OTHER_ID, cardKey=KEY)))

    def test_another_cards_answer_does_not_lend_its_key(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(OTHER_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move()))

    # --- it fails open

    def test_no_config_passes(self):
        project = Project(self.tmp / "bare", config=False)
        project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move(), project))

    def test_no_card_refs_script_passes(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        shutil.rmtree(self.project.root / ".harness" / "skills")
        self.assert_passes(self.run_hook(move()))

    def test_no_project_passes(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_passes(self.run_hook(move(), env_root=False, cwd=outside))

    def test_the_project_root_comes_from_git_without_the_variable(self):
        self.project.source(f"# card://{KEY} [temporary]: drop the shim once the API ships\n")
        self.project.remember(card_answer(CARD_ID, KEY, escaped=True))
        self.assert_blocked(self.run_hook(move(), env_root=False, cwd=self.project.root / "src"))


@unittest.skipUnless(shutil.which("bash"), "bash is not on PATH")
class Bash(Runner, unittest.TestCase):
    command = ["bash", str(HOOK.with_suffix(".sh"))]


@unittest.skipUnless(shutil.which("pwsh"), "pwsh is not on PATH: the .ps1 twin is not exercised here")
class PowerShell(Runner, unittest.TestCase):
    command = ["pwsh", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(HOOK.with_suffix(".ps1"))]


class Manifest(unittest.TestCase):
    def test_it_runs_before_every_tool_sends_nothing_and_ships_in_the_officium_preset(self):
        manifest = json.loads(HOOK.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["event"], manifest["tools"], manifest["sends"]), ("preTool", ["any"], None))
        for suffix in (".sh", ".ps1", ".md"):
            self.assertTrue(HOOK.with_suffix(suffix).is_file(), suffix)
        preset = json.loads((REPO / "market" / "presets" / "officium.json").read_text(encoding="utf-8"))
        self.assertIn("officium-temporary-refs", [item["key"] for item in preset["items"]])


if __name__ == "__main__":
    unittest.main()
