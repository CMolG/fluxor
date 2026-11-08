"""tools/fluxor_sync.py with `"storage": "local"` (card://JAVA-2010, ADR 0038): a pulled harness is
this machine's state. It stays out of git, a hook approved here is wired in this machine's settings
only, the committed bridges are the same on every machine, and a fresh clone of an enrolled machine
pulls at its first session. Reuses test_fluxor_sync's fake of the snapshot contract.
Run: python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import test_fluxor_sync as base
from test_fluxor_sync import CODE, PROJECT, fluxor_sync

GIT = shutil.which("git")


@unittest.skipUnless(GIT, "needs git, which a local harness keeps itself out of")
class LocalStorage(base.Sync):
    GUARD = "#!/bin/sh\necho guard\n"

    def setUp(self):
        super().setUp()
        self.git("init", "-q")

    def git(self, *args, cwd=None) -> str:
        return subprocess.run([GIT, *args], cwd=cwd or self.root, check=True, capture_output=True,
                              text=True).stdout

    def init_local(self, *extra):
        code, out = self.run_sync("init", "--enroll", CODE, "--project", PROJECT, "--server", self.url,
                                  "--storage", "local", *extra)
        self.assertEqual(code, 0, out)
        return out

    def with_guard(self):
        self.fluxor.hook("guard", "preTool", sh=self.GUARD, tools="shell")
        self.fluxor.wiring(always=("english", "guard"))

    def untracked(self) -> list[str]:
        status = self.git("status", "--porcelain", "--untracked-files=all")
        return sorted(line[3:] for line in status.splitlines())

    def test_nothing_of_the_pulled_harness_but_its_config_and_the_bridges_reaches_git(self):
        self.init_local()

        self.assertEqual(self.untracked(), [".claude/settings.json", ".codex/hooks.json", ".harness/fluxor.json",
                                            "AGENTS.md", "CLAUDE.md"])
        self.assertEqual(json.loads(self.read(".harness/fluxor.json"))["storage"], "local")
        exclude = (self.root / ".git" / "info" / "exclude").read_text()
        self.assertIn("/.harness/*\n!/.harness/fluxor.json\n", exclude)

    def test_a_clone_git_distrusts_still_keeps_the_harness_out_of_git(self):
        # Windows' git refuses every clone it reaches through WSL's share, unless the call trusts it.
        fake = self.tmp / "fake-git"
        fake.mkdir()
        (fake / "git").write_text(f'#!/bin/sh\ncase " $* " in *" safe.directory=* "*) exec "{GIT}" "$@" ;; esac\n'
                                  "echo 'fatal: detected dubious ownership in repository' >&2\nexit 128\n")
        (fake / "git").chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"}):
            self.init_local()

        self.assertIn("/.harness/*\n", (self.root / ".git" / "info" / "exclude").read_text())

    def test_a_pull_from_windows_into_a_wsl_tree_has_wsl_set_the_scripts_executable(self):
        self.assertEqual(fluxor_sync.wsl_share(r"\\wsl.localhost\Ubuntu\home\dev\p"), ("Ubuntu", "/home/dev/p"))
        self.assertEqual(fluxor_sync.wsl_share("\\\\wsl$\\Debian"), ("Debian", "/"))
        self.assertIsNone(fluxor_sync.wsl_share(r"C:\Users\dev\p"))
        (self.root / "run.sh").write_text("#!/bin/sh\n")
        lock = {"files": {"run.sh": {"executable": True}, "notes.md": {"executable": False},
                          "gone.sh": {"executable": True}}}
        with mock.patch.object(fluxor_sync, "wsl_share", return_value=("Ubuntu", "/home/dev/p")), \
                mock.patch.object(fluxor_sync.os, "name", "nt"), \
                mock.patch.object(fluxor_sync.subprocess, "run") as run:
            fluxor_sync.wsl_modes(self.root, lock)

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0],
                         ["wsl.exe", "-d", "Ubuntu", "--cd", "/home/dev/p", "--", "chmod", "755", "--", "run.sh"])

    def test_the_committed_block_is_the_same_on_every_machine_and_the_list_is_this_machines(self):
        self.init_local()

        block = fluxor_sync.managed_block(self.read("AGENTS.md"))
        self.assertEqual(block, fluxor_sync.STABLE_BLOCK)
        self.assertIn("@rules/english.md\n", self.read(".harness/agents.md"))
        self.assertNotIn("@.harness/", self.read(".harness/agents.md"))
        self.assertEqual(fluxor_sync.always_directives(self.root), [".harness/rules/english.md"])

    def test_a_hook_approved_here_is_wired_in_this_machines_settings_only(self):
        self.with_guard()
        self.init_local()
        committed = self.read(".claude/settings.json")

        code, out = self.run_sync("approve", "--consented", "guard")

        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(".claude/settings.json"), committed)
        local = json.loads(self.read(".claude/settings.local.json"))
        self.assertIn(".harness/hooks/guard.sh", json.dumps(local["hooks"]["PreToolUse"]))
        self.assertEqual(json.loads(self.read(".harness/harness.lock.json"))["hookWiring"]["claude"]["file"],
                         ".claude/settings.local.json")
        self.assertNotIn("@rules/guard.md", self.read(".harness/agents.md"))
        self.assertEqual(fluxor_sync.managed_block(self.read("AGENTS.md")), fluxor_sync.STABLE_BLOCK)
        self.assertNotIn(".claude/settings.local.json", self.untracked())

    def test_a_wiring_the_committed_settings_held_moves_to_this_machines_when_the_project_turns_local(self):
        self.with_guard()
        self.init()
        self.run_sync("approve", "--consented", "guard")
        self.assertIn("guard.sh", self.read(".claude/settings.json"))
        config = json.loads(self.read(".harness/fluxor.json"))
        (self.root / ".harness/fluxor.json").write_text(json.dumps({**config, "storage": "local"}))

        code, out = self.run_sync("pull")

        self.assertEqual(code, 0, out)
        self.assertNotIn("guard.sh", self.read(".claude/settings.json"))
        self.assertIn("guard.sh", self.read(".claude/settings.local.json"))
        self.assertIn("moved this machine's hook wiring out of .claude/settings.json", out)

    def test_a_fresh_clone_of_an_enrolled_machine_pulls_with_the_machines_writer_and_prints_the_rules(self):
        self.init_local()
        machine_writer = self.tmp / "config" / "bin" / "fluxor-sync.py"
        self.assertTrue(machine_writer.is_file())
        clone = self.tmp / "clone"
        (clone / ".harness").mkdir(parents=True)
        shutil.copy(self.root / ".harness/fluxor.json", clone / ".harness/fluxor.json")
        self.git("init", "-q", cwd=clone)

        run = subprocess.run(["python3", str(machine_writer), "--root", str(clone), "pull"], capture_output=True,
                             text=True, env={**os.environ})

        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual((clone / ".harness/rules/english.md").read_text(), "Write everything in American English.\n")
        self.assertIn("Write everything in American English.", run.stdout)
        self.assertEqual((clone / "AGENTS.md").read_text().count("@.harness/agents.md"), 1)

    def test_a_pull_after_the_first_does_not_print_the_rules_again(self):
        self.init_local()

        code, out = self.run_sync("pull")

        self.assertEqual(code, 0, out)
        self.assertNotIn("Write everything in American English.", out)

    def test_a_committed_harness_keeps_todays_behavior(self):
        self.with_guard()
        self.init_local()
        config = json.loads(self.read(".harness/fluxor.json"))
        (self.root / ".harness/fluxor.json").write_text(json.dumps({**config, "storage": "repository"}))
        (self.root / ".git" / "info" / "exclude").write_text("")

        self.run_sync("pull", "--force")
        self.run_sync("approve", "--consented", "guard")

        self.assertIn("guard.sh", self.read(".claude/settings.json"))
        self.assertIn("@.harness/rules/english.md", self.read("AGENTS.md"))
        self.assertNotIn("fluxor-sync:begin", (self.root / ".git" / "info" / "exclude").read_text())


def load_tests(loader, tests, pattern):
    """Only this class's own cases: the inherited ones run from test_fluxor_sync, in their mode."""
    return unittest.TestSuite(LocalStorage(name) for name in loader.getTestCaseNames(LocalStorage)
                              if name in LocalStorage.__dict__)


if __name__ == "__main__":
    unittest.main()
