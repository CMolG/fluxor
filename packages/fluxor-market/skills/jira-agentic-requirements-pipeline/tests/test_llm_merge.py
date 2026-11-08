"""Tests for the LLM-augmented analysis merge."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jira_pipeline_cli as cli  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class MergeLlmSuggestions(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.analysis_path = self.tmp_path / "analysis.json"
        self.suggestions_path = self.tmp_path / "suggestions.json"

    def tearDown(self):
        self._tmp.cleanup()

    def merge(self, output) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.merge_llm_suggestions(Namespace(
                analysis=str(self.analysis_path),
                suggestions=str(self.suggestions_path),
                output=output,
            ))

    def test_merge_unions_list_fields(self):
        output_path = self.tmp_path / "merged.json"
        _write(self.analysis_path, {
            "schemaVersion": "1.0.0",
            "issueKey": "DEMO-1",
            "functionalEntities": ["user", "account"],
            "missingBusinessDecisions": ["scope"],
        })
        _write(self.suggestions_path, {
            "functionalEntities": ["partner", "user"],  # "user" duplicates
            "missingBusinessDecisions": ["expiration", "scope"],
        })

        self.assertEqual(self.merge(str(output_path)), 0)

        merged = _read(output_path)
        # Lists become a sorted union, without duplicates.
        self.assertEqual(merged["functionalEntities"], ["account", "partner", "user"])
        self.assertEqual(merged["missingBusinessDecisions"], ["expiration", "scope"])
        self.assertEqual(merged["_llmAugmentation"]["acceptedKeys"], [
            "functionalEntities",
            "missingBusinessDecisions",
        ])
        self.assertEqual(merged["_llmAugmentation"]["rejectedKeys"], [])
        # Provenance is captured.
        snapshot = merged["_llmAugmentation"]["ruleBasedSnapshot"]
        self.assertEqual(snapshot["functionalEntities"], ["user", "account"])

    def test_merge_replaces_scalar_fields_and_keeps_provenance(self):
        _write(self.analysis_path, {
            "schemaVersion": "1.0.0",
            "issueKey": "DEMO-1",
            "businessGoal": "Reduce risk.",
        })
        _write(self.suggestions_path, {
            "businessGoal": "Comply with GDPR retention rules and reduce risk.",
        })

        self.merge(None)  # overwrite the analysis in place

        merged = _read(self.analysis_path)
        self.assertEqual(merged["businessGoal"], "Comply with GDPR retention rules and reduce risk.")
        self.assertEqual(merged["_llmAugmentation"]["ruleBasedSnapshot"]["businessGoal"], "Reduce risk.")

    def test_merge_rejects_unknown_keys(self):
        _write(self.analysis_path, {
            "schemaVersion": "1.0.0",
            "issueKey": "DEMO-1",
            "functionalEntities": [],
        })
        _write(self.suggestions_path, {
            "functionalEntities": ["user"],
            # Disallowed: would let the model rewrite immutable identity.
            "issueKey": "DEMO-2",
            # Disallowed: an arbitrary new field.
            "secretInjection": "haha",
        })

        self.merge(str(self.analysis_path))

        merged = _read(self.analysis_path)
        # Neither key is applied, and both are reported, the immutable issueKey included.
        self.assertEqual(merged["issueKey"], "DEMO-1")
        self.assertNotIn("secretInjection", merged)
        self.assertEqual(merged["_llmAugmentation"]["rejectedKeys"], ["issueKey", "secretInjection"])
        self.assertEqual(merged["_llmAugmentation"]["acceptedKeys"], ["functionalEntities"])

    def test_merge_reports_identity_keys_as_rejected(self):
        _write(self.analysis_path, {"schemaVersion": "1.1.0", "issueKey": "DEMO-1", "title": "T"})
        _write(self.suggestions_path, {"schemaVersion": "9.9.9", "issueKey": "DEMO-2", "title": "Other"})

        self.merge(str(self.analysis_path))

        merged = _read(self.analysis_path)
        self.assertEqual(merged["schemaVersion"], "1.1.0")
        self.assertEqual(merged["issueKey"], "DEMO-1")
        self.assertEqual(merged["title"], "T")
        augmentation = merged["_llmAugmentation"]
        self.assertEqual(augmentation["rejectedKeys"], ["issueKey", "schemaVersion", "title"])
        self.assertEqual(augmentation["acceptedKeys"], [])
        self.assertEqual(augmentation["ruleBasedSnapshot"], {})

    def test_rejected_list_field_is_not_snapshotted(self):
        _write(self.analysis_path, {"schemaVersion": "1.1.0", "issueKey": "DEMO-1", "userActions": ["a"]})
        _write(self.suggestions_path, {"userActions": "not a list"})

        self.merge(str(self.analysis_path))

        augmentation = _read(self.analysis_path)["_llmAugmentation"]
        self.assertEqual(augmentation["rejectedKeys"], ["userActions"])
        self.assertNotIn("userActions", augmentation["ruleBasedSnapshot"])

    def test_docstring_names_the_provenance_key_the_code_writes(self):
        doc = cli.merge_llm_suggestions.__doc__
        self.assertIn("_llmAugmentation.ruleBasedSnapshot.<field>", doc)
        self.assertNotIn("_ruleBased.", doc)

    def test_merge_rejects_non_list_for_list_fields(self):
        _write(self.analysis_path, {
            "schemaVersion": "1.0.0",
            "issueKey": "DEMO-1",
            "functionalEntities": ["user"],
        })
        _write(self.suggestions_path, {
            "functionalEntities": "user, partner",  # wrong shape
        })

        self.merge(str(self.analysis_path))

        merged = _read(self.analysis_path)
        self.assertEqual(merged["functionalEntities"], ["user"])  # untouched
        self.assertIn("functionalEntities", merged["_llmAugmentation"]["rejectedKeys"])


if __name__ == "__main__":
    unittest.main()
