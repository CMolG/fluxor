"""Every tool a skill manifest declares must start and print its usage.

A manifest that names a script which no longer parses its arguments is a broken promise to every
harness that exposes the tool. Node tools are skipped when Node is not installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def declared_tools():
    manifests = [*(REPO / "skills").glob("*/skill.json"), *(REPO / "meta-skills").glob("*/skill.json")]
    for manifest_path in sorted(manifests):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for tool in manifest.get("tools", []):
            yield manifest["id"], manifest_path.parent, tool


class SkillTools(unittest.TestCase):
    def test_every_declared_tool_prints_help(self):
        env = {**os.environ, "PYTHONIOENCODING": "", "PYTHONUTF8": "0"}
        for skill, folder, tool in declared_tools():
            command = list(tool["command"])
            if command[0] == "node" and not shutil.which("node"):
                continue
            if command[0] in ("python3", "python"):
                command[0] = sys.executable
            with self.subTest(skill=skill, tool=tool["name"]):
                result = subprocess.run([*command, "--help"], cwd=folder, capture_output=True, text=True,
                                        env=env, timeout=60)
                self.assertEqual(result.returncode, 0, f"{tool['name']}: {result.stderr[-400:]}")
                self.assertTrue(result.stdout.strip(), f"{tool['name']} printed no usage")


if __name__ == "__main__":
    unittest.main()
