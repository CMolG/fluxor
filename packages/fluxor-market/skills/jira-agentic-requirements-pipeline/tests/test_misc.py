"""Coverage for the smaller helpers and the CLI plumbing."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jira_pipeline_cli as cli  # noqa: E402

JIRA_ENV = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")


class JiraConfig(unittest.TestCase):
    def test_get_jira_config_raises_when_env_missing(self):
        with mock.patch.dict(os.environ):
            for name in JIRA_ENV:
                os.environ.pop(name, None)
            with self.assertRaises(SystemExit) as ctx:
                cli.get_jira_config()
        self.assertIn("JIRA_BASE_URL", str(ctx.exception))
        self.assertIn("JIRA_EMAIL", str(ctx.exception))
        self.assertIn("JIRA_API_TOKEN", str(ctx.exception))

    def test_get_jira_config_strips_trailing_slash(self):
        with mock.patch.dict(os.environ, {
            "JIRA_BASE_URL": "https://example.atlassian.net/",
            "JIRA_EMAIL": "u@example.com",
            "JIRA_API_TOKEN": "secret",
        }):
            config = cli.get_jira_config()
        self.assertEqual(config.base_url, "https://example.atlassian.net")


class ExtractText(unittest.TestCase):
    def test_extract_text_from_jira_node_handles_nested_adf(self):
        node = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "world"}]},
            ],
        }
        self.assertEqual(cli.extract_text_from_jira_node(node), "hello world")

    def test_extract_text_from_jira_node_handles_string_input(self):
        self.assertEqual(cli.extract_text_from_jira_node("plain string"), "plain string")

    def test_extract_text_from_jira_node_handles_none(self):
        self.assertEqual(cli.extract_text_from_jira_node(None), "")


class CollectInput(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, payload: dict) -> Path:
        path = self.tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_collect_input_non_interactive_passes_when_complete(self):
        questions_path = self.write("q.json", {
            "issueKey": "DEMO-1",
            "questions": [{"id": "Q1", "category": "Business Objective", "priority": "P0", "required": True}],
        })
        state_path = self.write("state.json", {"issueKey": "DEMO-1", "answers": {"Q1": {"answer": "ok"}}})

        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli.collect_input(
                Namespace(input=str(questions_path), state_file=str(state_path), non_interactive=True)
            )
        self.assertEqual(rc, 0)

    def test_collect_input_non_interactive_fails_when_incomplete(self):
        questions_path = self.write("q.json", {
            "issueKey": "DEMO-1",
            "questions": [
                {"id": "Q1", "category": "Business Objective", "priority": "P0", "required": True},
                {"id": "Q2", "category": "Functional Scope", "priority": "P0", "required": True},
            ],
        })
        state_path = self.write("state.json", {"issueKey": "DEMO-1", "answers": {"Q1": {"answer": "ok"}}})

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli.collect_input(
                Namespace(input=str(questions_path), state_file=str(state_path), non_interactive=True)
            )
        self.assertEqual(rc, 2)
        self.assertIn("Q2", out.getvalue())


class ContractHelpers(unittest.TestCase):
    def test_unresolved_items_detect_tbd_markers(self):
        items = [
            {"questionId": "Q1", "category": "Business Rules", "answer": "TBD: still pending"},
            {"questionId": "Q2", "category": "Functional Scope", "answer": "All paid users"},
        ]
        unresolved = cli.infer_unresolved_contract_items(items)
        self.assertTrue(any("Q1" in entry for entry in unresolved))
        self.assertFalse(any("Q2" in entry for entry in unresolved))

    def test_build_parser_lists_all_subcommands(self):
        parser = cli.build_parser()
        # parse_args raises SystemExit without a command, so probe the choices instead.
        sub = next(a for a in parser._actions if a.dest == "cmd")
        self.assertEqual(set(sub.choices), {
            "fetch-issue",
            "discovery",
            "generate-questions",
            "collect-input",
            "resolve-contract",
            "base-branch-plan",
            "merge-llm-suggestions",
            "request-human",
        })


if __name__ == "__main__":
    unittest.main()
