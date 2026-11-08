"""Unit tests for the rule-based inference functions in jira_pipeline_cli."""

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

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_text(fixture: str) -> str:
    issue = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    return cli.build_ticket_text(issue)


class AmbiguityLevel(unittest.TestCase):
    def test_ambiguity_level_returns_dict_shape(self):
        result = cli.infer_ambiguity_level(load_text("issue_tight.json"))
        self.assertEqual(set(result), {"level", "constraintDensity", "ambiguityMarkers", "signals"})
        self.assertIn(result["level"], {"LOW", "MEDIUM", "HIGH"})
        self.assertIsInstance(result["constraintDensity"], float)
        self.assertIsInstance(result["ambiguityMarkers"], float)
        self.assertIn("constraintKeywords", result["signals"])
        self.assertIn("ambiguityMarkers", result["signals"])

    def test_ambiguity_level_low_for_tight_ticket(self):
        self.assertEqual(cli.infer_ambiguity_level(load_text("issue_tight.json"))["level"], "LOW")

    def test_ambiguity_level_medium_for_mixed_ticket(self):
        self.assertEqual(cli.infer_ambiguity_level(load_text("issue_medium.json"))["level"], "MEDIUM")

    def test_ambiguity_level_high_for_near_empty_ticket(self):
        self.assertEqual(cli.infer_ambiguity_level(load_text("issue_empty.json"))["level"], "HIGH")

    def test_ambiguity_level_high_for_marker_dominated_ticket(self):
        """A long ticket dominated by markers (TBD, maybe, ...) and lacking
        constraint keywords should still rank HIGH despite its length."""
        result = cli.infer_ambiguity_level(load_text("issue_ambiguous.json"))
        self.assertEqual(result["level"], "HIGH")
        self.assertGreater(result["ambiguityMarkers"], 0)
        self.assertIn("tbd", result["signals"]["ambiguityMarkers"])

    def test_density_normalized_per_100_words(self):
        """Growing the text without adding keywords must lower the density."""
        short = "limit retry expire"
        long = short + " " + " ".join(["filler"] * 100)
        short_density = cli.infer_ambiguity_level(short)["constraintDensity"]
        long_density = cli.infer_ambiguity_level(long)["constraintDensity"]
        self.assertGreater(short_density, long_density)


class WordBoundaries(unittest.TestCase):
    def test_keyword_does_not_fire_inside_another_word(self):
        result = cli.infer_ambiguity_level("this pattern is commonly used")
        self.assertEqual(result["signals"]["constraintKeywords"], [])
        self.assertEqual(result["constraintDensity"], 0.0)

    def test_or_marker_is_the_word_or(self):
        self.assertEqual(cli.count_term("the order was ignored by the operator", "or"), 0)
        self.assertEqual(cli.count_term("show success or error, or retry", "or"), 2)
        # At the start of the text and before punctuation too.
        self.assertEqual(cli.count_term("or maybe not. this or.", "or"), 2)

    def test_phrases_match_across_spaces_hyphens_and_newlines(self):
        self.assertTrue(cli.has_term("we   should\ndecide", "we should"))
        self.assertTrue(cli.has_term("avoid a double-click", "double click"))
        self.assertTrue(cli.has_term("scope: all\tusers", "all users"))
        self.assertFalse(cli.has_term("we shoulder it", "we should"))

    def test_punctuation_markers_count_every_occurrence(self):
        self.assertEqual(cli.count_term("why? and how??", "?"), 3)
        self.assertEqual(cli.infer_ambiguity_level("is this final?")["signals"]["ambiguityMarkerCounts"], {"?": 1})

    def test_regular_inflections_match(self):
        for word in ["expire", "expires", "expired", "expiring"]:
            with self.subTest(word=word):
                self.assertTrue(cli.has_term(f"the window {word} soon", "expire"))
        for word in ["retry", "retries", "retried", "retrying"]:
            with self.subTest(word=word):
                self.assertTrue(cli.has_term(f"we {word} twice", "retry"))
        for word in ["cancel", "cancels", "cancelled", "canceled", "cancelling"]:
            with self.subTest(word=word):
                self.assertTrue(cli.has_term(f"users {word} it", "cancel"))
        self.assertTrue(cli.has_term("support reporting", "report"))

    def test_former_substring_false_positives_are_gone(self):
        cases = [
            ("the reviewers decide", "view"),
            ("translate the page", "sla"),
            ("more information", "format"),
            ("the request was cancelled", "can"),
            ("maybe later", "may"),
            ("progressive rollout", "progress"),
            ("the whole team", "who"),
        ]
        for text, term in cases:
            with self.subTest(term=term):
                self.assertFalse(cli.has_term(text, term))

    def test_heuristics_use_word_boundaries(self):
        self.assertNotIn("view operation status", cli.infer_user_actions("two reviewers approve"))
        self.assertNotIn("Perceived Performance", cli.detect_category_signals("a progressive rollout"))
        self.assertNotIn(
            "optional business behavior requested",
            cli.infer_explicit_requirements("maybe the request is cancelled"),
        )

    def test_derived_forms_listed_as_terms_still_match(self):
        text = "decisions must be traceable"
        self.assertIn("auditability flow", cli.infer_possible_flows(text))
        self.assertIn("Auditability & Traceability", cli.detect_category_signals(text))
        self.assertNotIn("auditability", cli.infer_missing_decisions(text, []))


class OccurrenceCounts(unittest.TestCase):
    def test_constraint_density_counts_every_occurrence(self):
        once = cli.infer_ambiguity_level("only admins a b c d e f g h")
        thrice = cli.infer_ambiguity_level("only admins only editors only owners a b c d")
        self.assertEqual(once["constraintDensity"], 10.0)
        self.assertEqual(thrice["constraintDensity"], 30.0)
        self.assertEqual(thrice["signals"]["constraintKeywordCounts"], {"only": 3})
        self.assertEqual(thrice["signals"]["constraintKeywords"], ["only"])

    def test_marker_density_counts_every_occurrence(self):
        result = cli.infer_ambiguity_level("tbd tbd maybe x x x x x x x")
        self.assertEqual(result["ambiguityMarkers"], 30.0)
        self.assertEqual(result["signals"]["ambiguityMarkerCounts"], {"tbd": 2, "maybe": 1})

    def test_inflected_occurrences_are_counted(self):
        result = cli.infer_ambiguity_level("it expires, then expired items expire")
        self.assertEqual(result["signals"]["constraintKeywordCounts"], {"expire": 3})


class MissingDecisionsAndSelection(unittest.TestCase):
    def test_missing_decisions_for_empty_ticket(self):
        text = load_text("issue_empty.json")
        missing = cli.infer_missing_decisions(text, cli.detect_category_signals(text))
        # A near-empty title should miss most decisions.
        self.assertGreaterEqual(len(missing), 10)

    def test_select_required_templates_respects_baseline_budget(self):
        selected = cli.select_required_templates(missing_decisions=set(), baseline_budget=4, signal_budget=6)
        baseline_ids = {t["template_id"] for t in selected if t["template_id"] in cli.BASELINE_TEMPLATE_IDS}
        self.assertEqual(baseline_ids, {"BO-1", "FS-1", "BR-1", "SL-1"})

    def test_select_required_templates_signal_overflow_into_baseline_p1(self):
        """When no signals match, signal slots overflow into remaining P0/P1 templates."""
        selected = cli.select_required_templates(missing_decisions=set(), baseline_budget=4, signal_budget=6)
        self.assertEqual(len(selected), 10)  # 4 baseline + 6 overflow
        overflow_ids = {t["template_id"] for t in selected if t["template_id"] not in cli.BASELINE_TEMPLATE_IDS}
        self.assertTrue(overflow_ids)  # must be filled

    def test_select_required_templates_signal_priority_match(self):
        """Templates whose signals match more missing decisions rank higher."""
        selected = cli.select_required_templates(
            missing_decisions={"compliance", "communications"}, baseline_budget=4, signal_budget=2
        )
        ids = {t["template_id"] for t in selected if t["template_id"] not in cli.BASELINE_TEMPLATE_IDS}
        # CM-1 maps to communications, LC-1 maps to compliance: both must be picked.
        self.assertLessEqual({"CM-1", "LC-1"}, ids)


class P2Templates(unittest.TestCase):
    def test_catalog_has_p2_templates(self):
        counts = {}
        for template in cli.question_templates():
            counts[template["priority"]] = counts.get(template["priority"], 0) + 1
        self.assertGreater(counts.get("P2", 0), 0)
        self.assertEqual(counts.get("P0"), 6)
        self.assertEqual(counts.get("P1"), 7)
        self.assertEqual(counts.get("P3"), 1)

    def test_p2_templates_are_optional_and_have_a_default(self):
        for template in cli.p2_templates():
            with self.subTest(template=template["template_id"]):
                self.assertEqual(template["priority"], "P2")
                self.assertFalse(template["required"])
                self.assertFalse(template["blocksImplementation"])
                self.assertTrue(template["defaultIfUnanswered"])
                self.assertIn(template["category"], cli.CATEGORY_KEYWORDS)

    def test_template_ids_are_unique(self):
        ids = [t["template_id"] for t in cli.question_templates()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_p2_and_p3_never_enter_the_required_set(self):
        every_decision = {s for t in cli.question_templates() for s in t["signals"]}
        selected = cli.select_required_templates(every_decision, baseline_budget=4, signal_budget=50)
        self.assertTrue(selected)
        self.assertEqual({t["priority"] for t in selected} - {"P0", "P1"}, set())

    def test_p2_is_offered_when_the_ticket_touches_its_category(self):
        chosen = cli.select_optional_templates(["Edge Cases", "Data Quality", "Business Rules"])
        self.assertEqual([t["template_id"] for t in chosen], ["DQ-1", "EC-1", "PZ-1"])

    def test_only_p3_without_matching_categories(self):
        chosen = cli.select_optional_templates([])
        self.assertEqual([t["template_id"] for t in chosen], ["PZ-1"])

    def test_generated_optional_questions_have_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            analysis = Path(tmp) / "analysis.json"
            analysis.write_text(json.dumps({
                "issueKey": "DEMO-1",
                "missingBusinessDecisions": [],
                "detectedCategories": ["Migration & Existing Data", "Perceived Performance"],
            }), encoding="utf-8")
            output = Path(tmp) / "questions.json"
            with contextlib.redirect_stdout(io.StringIO()):
                cli.generate_questions(Namespace(input=str(analysis), output=str(output),
                                                 baseline_budget=4, signal_budget=6))
            questions = json.loads(output.read_text(encoding="utf-8"))
        optional = questions["optionalFutureDecisions"]
        self.assertEqual([(q["id"], q["template_id"]) for q in optional],
                         [("O1", "MG-1"), ("O2", "PP-1"), ("O3", "PZ-1")])
        self.assertTrue(all("signals" not in q for q in optional))


if __name__ == "__main__":
    unittest.main()
