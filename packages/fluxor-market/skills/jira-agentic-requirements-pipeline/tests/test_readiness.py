"""The readiness hand-off to a backlog: a card snapshot from any tracker in, a wall draft out."""

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

FIXTURES = Path(__file__).resolve().parent / "fixtures"
WALL_KEYS = {"title", "why", "steps", "doneWhen", "unblocks", "category"}


def _quiet(func, args: Namespace) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return func(args)


class CardMissingAcceptance(unittest.TestCase):
    """A card with no acceptance criteria yields a wall with the questions, and no plan."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _questions(self, card: dict) -> Path:
        snapshot = self.dir / "card.json"
        snapshot.write_text(json.dumps(card), encoding="utf-8")
        analysis = self.dir / "analysis.json"
        questions = self.dir / "questions.json"
        _quiet(cli.discovery, Namespace(input=str(snapshot), output=str(analysis)))
        _quiet(cli.generate_questions, Namespace(
            input=str(analysis), output=str(questions),
            baseline_budget=cli.DEFAULT_BASELINE_BUDGET, signal_budget=cli.DEFAULT_SIGNAL_BUDGET,
        ))
        return questions

    def _card(self) -> dict:
        return json.loads((FIXTURES / "card_no_acceptance.json").read_text(encoding="utf-8"))

    def test_the_draft_is_a_request_human_wall_carrying_the_acceptance_question(self):
        questions = self._questions(self._card())
        wall = self.dir / "wall.json"
        self.assertEqual(_quiet(cli.request_human, Namespace(
            questions=str(questions), answers=None, output=str(wall))), 0)

        draft = json.loads(wall.read_text(encoding="utf-8"))
        self.assertFalse(draft["ready"])
        self.assertTrue(WALL_KEYS.issubset(draft), WALL_KEYS - set(draft))
        self.assertEqual(draft["unblocks"], ["PROJ-42"])
        self.assertEqual(draft["category"], "spike")
        ac = next(t for t in cli.question_templates() if t["template_id"] == "AC-1")
        self.assertIn(ac["question"], draft["steps"])
        asked = json.loads(questions.read_text(encoding="utf-8"))["questions"]
        for q in asked:
            self.assertIn(f"**{q['id']} ", draft["steps"])
            self.assertIn(q["id"], draft["doneWhen"])

    def test_no_contract_and_so_no_plan_while_the_questions_are_open(self):
        questions = self._questions(self._card())
        state = self.dir / "state.json"
        state.write_text(json.dumps({"issueKey": "PROJ-42", "answers": {}}), encoding="utf-8")
        contract = self.dir / "contract.json"
        code = _quiet(cli.resolve_contract, Namespace(
            questions=str(questions), answers=str(state), output=str(contract)))
        self.assertEqual(code, 2)
        self.assertFalse(contract.exists())

    def test_criteria_kept_as_a_list_answer_the_acceptance_decision(self):
        card = self._card()
        card["acceptanceCriteria"] = ["A member resumes early from the account page"]
        questions = json.loads(self._questions(card).read_text(encoding="utf-8"))["questions"]
        self.assertNotIn("Acceptance Criteria", {q["category"] for q in questions})
        analysis = json.loads((self.dir / "analysis.json").read_text(encoding="utf-8"))
        self.assertNotIn("acceptance_criteria", analysis["missingBusinessDecisions"])
        self.assertIn("a member resumes early", cli.build_ticket_text(card))

    def test_every_required_answer_in_means_ready_and_no_wall(self):
        questions = self._questions(self._card())
        asked = json.loads(questions.read_text(encoding="utf-8"))["questions"]
        state = self.dir / "state.json"
        state.write_text(json.dumps({
            "issueKey": "PROJ-42",
            "answers": {q["id"]: {"answer": "Decided"} for q in asked},
        }), encoding="utf-8")
        wall = self.dir / "wall.json"
        _quiet(cli.request_human, Namespace(questions=str(questions), answers=str(state), output=str(wall)))
        draft = json.loads(wall.read_text(encoding="utf-8"))
        self.assertTrue(draft["ready"])
        self.assertFalse(WALL_KEYS & set(draft))


class PlanScopeComesFromTheContract(unittest.TestCase):
    def test_answers_become_scope_and_out_of_scope_becomes_exclusions(self):
        scope = cli.contract_scope({
            "businessObjective": "Fewer cancellations",
            "businessRules": ["Up to three months", "One pause a year"],
            "outOfScope": ["Annual plans"],
            "reporting": [],
            "functionalScope": None,
        })
        self.assertEqual(scope, [
            "businessObjective: Fewer cancellations",
            "businessRules: Up to three months",
            "businessRules: One pause a year",
        ])


class ProjectRoot(unittest.TestCase):
    def test_claude_project_dir_wins_and_omitted_outputs_land_there(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmp}):
            self.assertEqual(cli.project_root(), Path(tmp))
            args = cli.build_parser().parse_args(["request-human", "--questions", "q.json"])
            self.assertEqual(Path(args.output), Path(tmp) / "request_human.json")
            args = cli.build_parser().parse_args(["collect-input", "--input", "q.json"])
            self.assertEqual(Path(args.state_file), Path(tmp) / cli.DEFAULT_STATE_FILE)

    def test_outside_git_and_without_the_variable_it_is_the_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            os.environ["GIT_CEILING_DIRECTORIES"] = str(Path(tmp).parent)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertEqual(cli.project_root().resolve(), Path(tmp).resolve())
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
