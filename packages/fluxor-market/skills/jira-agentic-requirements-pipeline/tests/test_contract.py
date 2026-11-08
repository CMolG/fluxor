"""Tests for the functional contract fields, optional answers and the catalog reference sync."""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import jira_pipeline_cli as cli  # noqa: E402

CATALOG_MD = SKILL / "references" / "question-catalog.md"
CONTRACTS_MD = SKILL / "references" / "contracts.md"


def _question(qid: str, category: str, priority: str = "P0", required: bool = True) -> dict:
    return {"id": qid, "category": category, "priority": priority, "required": required,
            "question": f"About {category}?", "whyItMatters": "Because."}


class ContractFields(unittest.TestCase):
    def test_every_catalog_category_has_a_contract_field(self):
        categories = set(cli.CATEGORY_KEYWORDS) | {t["category"] for t in cli.question_templates()}
        self.assertEqual(categories - set(cli.CONTRACT_FIELDS), set())

    def test_contract_field_names_are_unique(self):
        fields = list(cli.CONTRACT_FIELDS.values())
        self.assertEqual(len(fields), len(set(fields)))
        self.assertLessEqual(cli.SINGULAR_CONTRACT_FIELDS, set(fields))

    def test_contracts_reference_lists_every_field(self):
        text = CONTRACTS_MD.read_text(encoding="utf-8")
        rows = dict(re.findall(r"^\| ([^|`]+?) \| `(\w+)`", text, flags=re.MULTILINE))
        self.assertEqual(rows, cli.CONTRACT_FIELDS)


class ResolveContract(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def resolve(self, questions: list[dict], optional: list[dict], answers: dict[str, str]) -> dict:
        question_set = {"issueKey": "DEMO-1", "questions": questions, "optionalFutureDecisions": optional}
        state = {"issueKey": "DEMO-1", "answers": {qid: {"answer": text} for qid, text in answers.items()}}
        (self.tmp / "q.json").write_text(json.dumps(question_set), encoding="utf-8")
        (self.tmp / "s.json").write_text(json.dumps(state), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli.resolve_contract(Namespace(questions=str(self.tmp / "q.json"),
                                                answers=str(self.tmp / "s.json"),
                                                output=str(self.tmp / "c.json")))
        self.assertEqual(rc, 0)
        return json.loads((self.tmp / "c.json").read_text(encoding="utf-8"))

    def test_contract_carries_every_field(self):
        contract = self.resolve([_question("Q1", "Business Objective")], [], {"Q1": "Grow"})
        self.assertEqual(list(contract["functionalContract"]), list(cli.CONTRACT_FIELDS.values()))
        self.assertEqual(contract["functionalContract"]["businessObjective"], "Grow")
        self.assertIsNone(contract["functionalContract"]["functionalScope"])
        self.assertEqual(contract["functionalContract"]["edgeCases"], [])

    def test_formerly_unmapped_categories_resolve_to_fields(self):
        categories = [
            "Actors & Permissions", "Edge Cases", "Pricing, Billing & Monetization",
            "Activation & Functional Configuration", "Auditability & Traceability",
            "Functional Error Handling", "Business External Dependencies",
            "Internationalization & Localization", "Accessibility & Usability", "Perceived Performance",
            "Functional Security", "Data Quality", "Priority, Severity & Criticality",
            "Reversibility & Rollback", "Migration & Existing Data", "Rapid Decision",
        ]
        questions = [_question(f"Q{i}", c) for i, c in enumerate(categories, start=1)]
        answers = {q["id"]: f"Answer for {q['category']}" for q in questions}
        contract = self.resolve(questions, [], answers)
        self.assertEqual(contract["unmappedAnswers"], [])
        for category in categories:
            with self.subTest(category=category):
                field = cli.CONTRACT_FIELDS[category]
                self.assertEqual(contract["functionalContract"][field], [f"Answer for {category}"])

    def test_unknown_category_stays_unmapped(self):
        contract = self.resolve([_question("Q1", "Partner Onboarding")], [], {"Q1": "Manual review"})
        self.assertEqual(contract["unmappedAnswers"],
                         [{"questionId": "Q1", "category": "Partner Onboarding", "answer": "Manual review"}])

    def test_answered_optional_questions_are_resolved(self):
        required = [_question("Q1", "Business Objective")]
        optional = [_question("O1", "Edge Cases", "P2", False), _question("O2", "Data Quality", "P2", False)]
        contract = self.resolve(required, optional, {"Q1": "Grow", "O1": "Ignore duplicates"})
        self.assertEqual(contract["functionalContract"]["edgeCases"], ["Ignore duplicates"])
        self.assertEqual(contract["functionalContract"]["dataQuality"], [])

    def test_optional_questions_are_never_required(self):
        required = [_question("Q1", "Business Objective")]
        optional = [_question("O1", "Edge Cases", "P2", False)]
        contract = self.resolve(required, optional, {"Q1": "Grow"})
        self.assertEqual(contract["functionalContract"]["edgeCases"], [])


class CollectOptional(unittest.TestCase):
    def test_include_optional_asks_optional_questions_after_required(self):
        question_set = {
            "issueKey": "DEMO-1",
            "questions": [_question("Q1", "Business Objective")],
            "optionalFutureDecisions": [_question("O1", "Edge Cases", "P2", False),
                                        _question("O2", "Out of Scope", "P3", False)],
        }
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = Path(tmp) / "q.json"
            questions_path.write_text(json.dumps(question_set), encoding="utf-8")
            state_path = Path(tmp) / "state.json"
            replies = iter(["Grow", "Ignore duplicates", ""])  # the empty reply skips O2
            with mock.patch.object(builtins, "input", lambda _prompt: next(replies)), \
                    contextlib.redirect_stdout(io.StringIO()):
                rc = cli.collect_input(Namespace(input=str(questions_path), state_file=str(state_path),
                                                 non_interactive=False, include_optional=True))
            state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual({k: v["answer"] for k, v in state["answers"].items()},
                         {"Q1": "Grow", "O1": "Ignore duplicates"})

    def test_without_the_flag_only_required_questions_are_asked(self):
        question_set = {
            "issueKey": "DEMO-1",
            "questions": [_question("Q1", "Business Objective")],
            "optionalFutureDecisions": [_question("O1", "Edge Cases", "P2", False)],
        }
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = Path(tmp) / "q.json"
            questions_path.write_text(json.dumps(question_set), encoding="utf-8")
            state_path = Path(tmp) / "state.json"
            prompts = []

            def fake_input(prompt):
                prompts.append(prompt)
                return "Grow"

            with mock.patch.object(builtins, "input", fake_input), contextlib.redirect_stdout(io.StringIO()):
                cli.collect_input(Namespace(input=str(questions_path), state_file=str(state_path),
                                            non_interactive=False))
        self.assertEqual(len(prompts), 1)


class CatalogReferenceSync(unittest.TestCase):
    def test_template_table_matches_the_script(self):
        text = CATALOG_MD.read_text(encoding="utf-8")
        rows = re.findall(r"^\| ([A-Z]{2}-\d+) \| (P\d) \| ([^|]+?) \| ([^|]+?) \|$", text, flags=re.MULTILINE)
        documented = {row[0]: (row[1], row[2], row[3]) for row in rows}
        shipped = {t["template_id"]: (t["priority"], t["category"], t["question"]) for t in cli.question_templates()}
        self.assertEqual(len(rows), len(documented), "duplicate template id in the table")
        self.assertEqual(documented, shipped)

    def test_every_template_category_is_a_catalog_heading(self):
        text = CATALOG_MD.read_text(encoding="utf-8")
        headings = set(re.findall(r"^## \d+\) (.+)$", text, flags=re.MULTILINE))
        self.assertEqual(set(cli.CATEGORY_KEYWORDS) - headings, set())


if __name__ == "__main__":
    unittest.main()
