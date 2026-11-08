"""Tests that exercise the JiraClient seam without making real HTTP calls."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jira_pipeline_cli as cli  # noqa: E402


class FakeJiraClient:
    """Drop-in replacement for JiraClient backed by a script of canned responses."""

    def __init__(self, responses: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        self.calls.append((path, query))
        queue = self.responses.get(path)
        if not queue:
            raise AssertionError(f"unexpected call to {path}")
        return queue.pop(0)


class FetchComments(unittest.TestCase):
    def test_fetch_all_comments_paginates_until_total(self):
        page1 = {"comments": [{"id": str(i)} for i in range(100)], "total": 250, "startAt": 0, "maxResults": 100}
        page2 = {"comments": [{"id": str(i)} for i in range(100, 200)], "total": 250, "startAt": 100,
                 "maxResults": 100}
        page3 = {"comments": [{"id": str(i)} for i in range(200, 250)], "total": 250, "startAt": 200,
                 "maxResults": 100}
        client = FakeJiraClient({"/rest/api/3/issue/DEMO-1/comment": [page1, page2, page3]})

        result = cli.fetch_all_comments(client, "DEMO-1", max_comments=1000)

        self.assertEqual(len(result), 250)
        self.assertEqual(result[0]["id"], "0")
        self.assertEqual(result[-1]["id"], "249")
        self.assertEqual(len(client.calls), 3)  # one call per page

    def test_fetch_all_comments_respects_cap_and_warns(self):
        page1 = {"comments": [{"id": str(i)} for i in range(50)], "total": 200, "startAt": 0, "maxResults": 50}
        client = FakeJiraClient({"/rest/api/3/issue/DEMO-1/comment": [page1]})

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = cli.fetch_all_comments(client, "DEMO-1", max_comments=50)

        self.assertEqual(len(result), 50)
        self.assertIn("comment cap reached", err.getvalue())
        self.assertIn("200", err.getvalue())  # the total is surfaced in the warning

    def test_fetch_all_comments_stops_when_total_reached(self):
        page1 = {"comments": [{"id": "1"}, {"id": "2"}], "total": 2, "startAt": 0, "maxResults": 100}
        client = FakeJiraClient({"/rest/api/3/issue/DEMO-1/comment": [page1]})

        result = cli.fetch_all_comments(client, "DEMO-1", max_comments=1000)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(client.calls), 1)


class FetchIssue(unittest.TestCase):
    def test_fetch_issue_normalizes_payload(self):
        issue_payload = {
            "key": "DEMO-1",
            "fields": {
                "summary": "Title",
                "description": {"content": [{"type": "paragraph", "content": [{"type": "text", "text": "body"}]}]},
                "labels": ["a", "b"],
                "customfield_10011": "EPIC-1",
                "status": {"name": "Open"},
            },
        }
        comments_payload = {
            "comments": [{"author": {"displayName": "alice"}, "body": "hi", "created": "2026-01-01T00:00:00Z"}],
            "total": 1,
            "startAt": 0,
            "maxResults": 100,
        }
        client = FakeJiraClient({
            "/rest/api/3/issue/DEMO-1": [issue_payload],
            "/rest/api/3/issue/DEMO-1/comment": [comments_payload],
        })

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "issue.json"
            args = Namespace(issue_key="DEMO-1", output=str(output), max_comments=1000)
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cli.fetch_issue(args, client=client)

            self.assertEqual(rc, 0)
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(saved["issueKey"], "DEMO-1")
        self.assertEqual(saved["title"], "Title")
        self.assertEqual(saved["description"], "body")
        self.assertEqual(saved["labels"], ["a", "b"])
        self.assertEqual(saved["epic"], "EPIC-1")
        self.assertEqual(saved["status"], "Open")
        self.assertEqual(saved["comments"][0]["author"], "alice")
        self.assertEqual(saved["comments"][0]["body"], "hi")


if __name__ == "__main__":
    unittest.main()
