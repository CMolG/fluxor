"""Tests for evals/scripts/scoring.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "scripts"))
import scoring  # noqa: E402


class Scoring(unittest.TestCase):
    def test_word_count_excludes_punctuation(self):
        self.assertEqual(scoring.word_count("Hello, world! Foo's bar."), 4)

    def test_section_count_counts_markdown_headings(self):
        text = "# A\n\n## B\n\nbody\n\n### C\n"
        self.assertEqual(scoring.section_count(text), 3)

    def test_required_phrase_hits_is_case_insensitive(self):
        text = "We use a Feature Flag with dual-write."
        result = scoring.required_phrase_hits(text, ["feature flag", "dual-write", "missing"])
        self.assertEqual(result, {"feature flag": True, "dual-write": True, "missing": False})

    def test_phrases_match_whole_words_and_a_space_matches_a_hyphen(self):
        self.assertFalse(scoring.has_phrase("The deploy is blocked.", "lock"))
        self.assertTrue(scoring.has_phrase("Take a table lock.", "lock"))
        self.assertTrue(scoring.has_phrase("Ship it behind a feature-flag.", "feature flag"))
        self.assertTrue(scoring.has_phrase("Keep a dual write for a week.", "dual-write"))

    def test_defect_hits_count_any_detect_phrase(self):
        defects = [
            {"id": "index", "detect": ["concurrently", "table lock"]},
            {"id": "collisions", "detect": ["duplicate"]},
        ]
        self.assertEqual(scoring.defect_hits("Build it CONCURRENTLY.", defects),
                         {"index": True, "collisions": False})

    def test_forbidden_bang_ignores_markdown_images(self):
        self.assertEqual(scoring.forbidden_hits("![diagram](d.png) Plain text.", ["!"]), [])
        self.assertEqual(scoring.forbidden_hits("Ship it now!", ["!", "revolutionary"]), ["!"])
        self.assertEqual(scoring.forbidden_hits("A revolutionary tool.", ["revolutionary"]), ["revolutionary"])

    def test_voice_alignment_high_for_overlapping_vocabulary(self):
        corpus = "expand contract dual-write feature flag rollback blast radius"
        output = "Use expand and contract with a feature flag and a rollback toggle."
        other = "Looks fine, ship it. Senior engineer here."
        aligned = scoring.voice_alignment(output, corpus)
        misaligned = scoring.voice_alignment(other, corpus)
        self.assertGreater(aligned, misaligned)
        self.assertGreater(aligned, 0.05)

    def test_score_output_full_pipeline(self):
        text = (
            "# Summary\n"
            "Reject as written. We need expand and contract with a feature flag.\n"
            "## Risk\n"
            "Lock contention on the unique index. Backfill must batch.\n"
            "## Rollback\n"
            "The plan has none. Add a toggle.\n"
        )
        criteria = {
            "minWords": 5,
            "maxWords": 1000,
            "requiredSections": ["summary", "risk", "rollback"],
            "requiredPhrases": ["expand", "contract", "feature flag", "rollback", "missing-term"],
            "seededDefects": [
                {"id": "index", "detect": ["lock contention"]},
                {"id": "collisions", "detect": ["duplicate"]},
            ],
            "forbiddenPhrases": ["revolutionary"],
        }
        result = scoring.score_output(text, criteria, corpus="expand contract feature flag rollback")
        self.assertEqual(result["sectionCoverage"], 1.0)
        self.assertEqual(result["phraseCoverage"], 0.8)  # 4 of 5 phrases present
        self.assertEqual(result["defectRecall"], 0.5)
        self.assertEqual(result["defectHits"], {"index": True, "collisions": False})
        self.assertEqual(result["forbiddenHits"], [])
        self.assertIs(result["lengthWithinBounds"], True)
        self.assertGreater(result["voiceAlignment"], 0.0)
        # No composite: the metrics are separate diagnostics, never folded into one score.
        self.assertNotIn("compositeScore", result)

    def test_score_output_without_criteria_lists(self):
        result = scoring.score_output("Just words.", {}, corpus=None)
        self.assertEqual(result["phraseCoverage"], 1.0)
        self.assertEqual(result["sectionCoverage"], 1.0)
        self.assertIsNone(result["defectRecall"])
        self.assertIsNone(result["voiceAlignment"])

    def test_score_output_flags_length_violation(self):
        criteria = {"minWords": 1000, "maxWords": 2000, "requiredPhrases": [], "requiredSections": []}
        result = scoring.score_output("only ten words here for this test of the scorer", criteria, corpus=None)
        self.assertIs(result["lengthWithinBounds"], False)


if __name__ == "__main__":
    unittest.main()
