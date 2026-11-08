"""Tests for scripts/validate_handoff.py, against a synthetic pack of pack contract v2.

Run: python3 -m unittest discover -s meta-skills/ceet-sub-agent-orchestration/tests -t meta-skills/ceet-sub-agent-orchestration/tests
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_handoff  # noqa: E402

BACKEND_PACK = ".harness/packs/backend-engineer-alex"
SRE_PACK = ".harness/packs/devops-sre-sam"


def plan(tasks: list[dict] | None = None) -> dict:
    return {
        "schemaVersion": "2.0.0",
        "planId": "plan-1",
        "goal": "Audit checkout flow",
        "tasks": tasks if tasks is not None else [
            {
                "id": "T1",
                "role": "ceet-backend-engineer",
                "scope": "Audit migration plan",
                "expectedArtifacts": ["report"],
                "dependsOn": [],
                "binding": {"pack": BACKEND_PACK, "artifact": "agents/code-reviewer.md", "example": False},
            },
            {
                "id": "T2",
                "role": "ceet-devops-sre",
                "scope": "Add alerts",
                "expectedArtifacts": ["diff"],
                "dependsOn": ["T1"],
                "binding": {"pack": SRE_PACK, "artifact": "rules/alerting.md"},
            },
        ],
    }


def task(**binding) -> dict:
    """One backend task bound as `binding` says, over the valid binding."""
    return {
        "id": "T1",
        "role": "ceet-backend-engineer",
        "scope": "x",
        "expectedArtifacts": ["report"],
        "dependsOn": [],
        "binding": {"pack": BACKEND_PACK, "artifact": "agents/code-reviewer.md", **binding},
    }


VALID_RESULT = {
    "schemaVersion": "1.0.0",
    "planId": "plan-1",
    "taskId": "T1",
    "role": "ceet-backend-engineer",
    "status": "completed",
    "artifacts": [{"path": "report.md", "kind": "report"}],
    "summary": "ok",
}


class PackFixture(unittest.TestCase):
    """A project holding two rendered v2 packs: the files a pack contract v2 render writes."""

    def setUp(self):
        self.project = Path(tempfile.mkdtemp())
        self.write_pack(BACKEND_PACK, "ceet-backend-engineer", ["agents/code-reviewer.md", "skills/migrations.md"])
        self.write_pack(SRE_PACK, "ceet-devops-sre", ["rules/alerting.md"])

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def write_pack(self, path: str, role: str, artifacts: list[str], profile_role: bool = True) -> Path:
        pack = self.project / path
        files = {
            "pack.json": json.dumps({"schemaVersion": "1.0.0", "packId": pack.name, "metaSkill": f"{role}@2.0.0"}),
            "core.md": "# Alex\n\nI split migrations into expand and contract.\n",
            "cognitive-profile.md": "# The full clone, for people\n",
            "private/answers.json": "{}",
        }
        if profile_role:
            files["cognitive-profile.json"] = json.dumps({"schemaVersion": "2.0.0", "role": role})
        files.update({artifact: f"# {artifact}\n" for artifact in artifacts})
        for name, text in files.items():
            (pack / name).parent.mkdir(parents=True, exist_ok=True)
            (pack / name).write_text(text, encoding="utf-8")
        return pack

    def errors(self, payload: dict) -> list[str]:
        return validate_handoff.validate_plan(payload, self.project)

    def assertError(self, payload: dict, fragment: str):
        errors = self.errors(payload)
        self.assertTrue(any(fragment in e for e in errors), errors)


class Plan(PackFixture):
    def test_valid_plan_has_no_errors(self):
        self.assertEqual(self.errors(plan()), [])

    def test_plan_rejects_wrong_schema_version(self):
        self.assertError(dict(plan(), schemaVersion="1.0.0"), "schemaVersion")

    def test_plan_rejects_duplicate_task_ids(self):
        self.assertError(plan([task(), task()]), "duplicate id")

    def test_plan_rejects_forward_dependencies(self):
        first, second = plan()["tasks"]
        first["dependsOn"], second["dependsOn"] = ["T2"], []
        self.assertError(plan([first, second]), "not declared before")

    def test_plan_rejects_empty_task_list(self):
        self.assertError(plan([]), "non-empty list")


class Binding(PackFixture):
    def test_every_task_needs_a_binding(self):
        unbound = task()
        del unbound["binding"]
        self.assertError(plan([unbound]), "binding: must be an object")

    def test_pack_must_exist(self):
        self.assertError(plan([task(pack=".harness/packs/nobody")]), "is not a folder")

    def test_pack_must_be_rendered(self):
        (self.project / BACKEND_PACK / "core.md").unlink()
        self.assertError(plan(), "has no core.md")

    def test_pack_must_be_for_the_tasks_role(self):
        self.assertError(plan([task(pack=SRE_PACK, artifact="rules/alerting.md")]), "is a ceet-devops-sre pack")

    def test_role_falls_back_to_the_manifest(self):
        kim = ".harness/packs/backend-engineer-kim"
        self.write_pack(kim, "ceet-backend-engineer", ["agents/code-reviewer.md"], profile_role=False)
        self.assertEqual(self.errors(plan([task(pack=kim)])), [])
        self.assertError(plan([dict(task(pack=kim), role="ceet-devops-sre")]), "is a ceet-backend-engineer pack")

    def test_artifact_must_exist(self):
        self.assertError(plan([task(artifact="agents/architect.md")]), "does not exist")

    def test_only_a_per_task_artifact_is_loaded(self):
        # Pack contract v2: besides core.md, a sub-agent loads one agent, skill, command or rule file;
        # the full clone for people and private/ are never loaded for work.
        for artifact in ("cognitive-profile.md", "core.md", "private/answers.json", "pack.json", "agents"):
            with self.subTest(artifact=artifact):
                self.assertError(plan([task(artifact=artifact)]), "must be a file under one of")

    def test_artifact_cannot_leave_the_pack(self):
        for artifact in ("agents/../private/answers.json", "/etc/passwd", "../backend-engineer-alex/core.md"):
            with self.subTest(artifact=artifact):
                self.assertError(plan([task(artifact=artifact)]), "must be a file under one of")

    def test_example_must_be_a_boolean(self):
        self.assertError(plan([task(example="yes")]), "binding.example: must be a boolean")

    def test_an_example_pack_outside_the_packs_folder_binds(self):
        # ceet-autodiscover reports example packs where a sibling skill ships them.
        example = "skills/ceet-impersonator/examples/backend-engineer-sample"
        self.write_pack(example, "ceet-backend-engineer", ["agents/code-reviewer.md"])
        self.assertEqual(self.errors(plan([task(pack=example, example=True)])), [])

    def test_an_absolute_pack_path_binds(self):
        self.assertEqual(self.errors(plan([task(pack=str(self.project / BACKEND_PACK))])), [])


class Result(unittest.TestCase):
    def test_valid_result_has_no_errors(self):
        self.assertEqual(validate_handoff.validate_result(VALID_RESULT), [])

    def test_result_completed_requires_artifacts(self):
        errors = validate_handoff.validate_result(dict(VALID_RESULT, artifacts=[]))
        self.assertTrue(any("non-empty when status=completed" in e for e in errors), errors)

    def test_result_failed_requires_error(self):
        errors = validate_handoff.validate_result({**VALID_RESULT, "status": "failed", "artifacts": []})
        self.assertTrue(any("error" in e for e in errors), errors)

    def test_result_rejects_unknown_artifact_kind(self):
        errors = validate_handoff.validate_result(dict(VALID_RESULT, artifacts=[{"path": "x.md", "kind": "wat"}]))
        self.assertTrue(any("file|diff|report|decision" in e for e in errors), errors)

    def test_result_rejects_unknown_status(self):
        errors = validate_handoff.validate_result(dict(VALID_RESULT, status="in-progress"))
        self.assertTrue(any("completed|failed|skipped" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
