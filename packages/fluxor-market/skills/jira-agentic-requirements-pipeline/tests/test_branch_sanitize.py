"""Property tests for sanitize_branch_part.

Each property runs over a few hundred strings from a seeded generator (ASCII letters, digits,
punctuation and whitespace, control characters, accented and non-Latin letters, emoji, and code
points from anywhere in Unicode) plus hand-picked edge cases, so the run is deterministic and
needs only the standard library.

Run from the repository root:
    python3 -m unittest discover -s skills/jira-agentic-requirements-pipeline/tests \
        -t skills/jira-agentic-requirements-pipeline/tests
"""

from __future__ import annotations

import random
import re
import string
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jira_pipeline_cli as cli  # noqa: E402

SEED = 20260929
SAMPLES_FROM_ALPHABET = 400
SAMPLES_FROM_ANY_CODE_POINT = 150

# Pieces the generator draws from; multi-code-point emoji stay whole.
ALPHABET = (
    list(string.ascii_letters + string.digits + string.punctuation)
    + [" ", "\t", "\n", "\r", "\x0b", "\x0c", " ", " ", "　"]
    + [chr(c) for c in range(0, 32)] + ["\x7f", "​", "﻿", "́", "̇"]
    + list("áéíóúñüçÅØßÆœÀÉÎÕÜĳŁąŸ")  # lang:es: generator input
    + list("ЖжДдλΩπσς中文日本語한국어עבריתالعربية")
    + ["İ", "K", "ǅ", "ﬁ", "Σ", "ẞ"]
    + ["😀", "🚀", "🔥", "👍🏽", "👨‍👩‍👧", "🇪🇸"]
)

EDGE_CASES = [
    "", "-", "---", " - ", "-a-", "a--b", "a - b", "--x--", "   ", "\t\n", "\x00", "\x7f",
    "​", "﻿", "á", "/", "//", "..", "../..", "._-", "-.-", "feature/ABC-1",
    "APP-4827", " APP-4827 ", "APP 4827", "app_4827.v2", "İstanbul", "Straße", "ǅ", "Ω",
    "K", "ﬁ", "😀", "👍🏽", "中文", "-😀-", "😀-😀", "  trailing  ", "\n-leading",
    "ñandú", "-ñ-", "¿qué?",  # lang:es: generator input
]


def generated_strings() -> list[str]:
    rng = random.Random(SEED)
    values = list(EDGE_CASES)
    for _ in range(SAMPLES_FROM_ALPHABET):
        values.append("".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 40))))
    for _ in range(SAMPLES_FROM_ANY_CODE_POINT):
        length = rng.randint(1, 12)
        chars: list[str] = []
        while len(chars) < length:
            code_point = rng.randint(0, 0x10FFFF)
            if 0xD800 <= code_point <= 0xDFFF:  # lone surrogates are not text
                continue
            chars.append(chr(code_point))
        values.append("".join(chars))
    return values


VALUES = generated_strings()


class SanitizeBranchPart(unittest.TestCase):
    def test_sanitize_idempotent(self):
        for value in VALUES:
            with self.subTest(value=value):
                once = cli.sanitize_branch_part(value)
                twice = cli.sanitize_branch_part(once)
                self.assertEqual(once, twice)

    def test_sanitize_no_double_dashes(self):
        for value in VALUES:
            with self.subTest(value=value):
                self.assertNotIn("--", cli.sanitize_branch_part(value))

    def test_sanitize_no_leading_or_trailing_dash(self):
        for value in VALUES:
            with self.subTest(value=value):
                result = cli.sanitize_branch_part(value)
                self.assertFalse(result.startswith("-"))
                self.assertFalse(result.endswith("-"))

    def test_sanitize_only_branch_safe_characters(self):
        # Branch parts may contain a-z, 0-9, dot, underscore, slash, dash.
        for value in VALUES:
            with self.subTest(value=value):
                result = cli.sanitize_branch_part(value)
                self.assertIsNotNone(re.fullmatch(r"[a-z0-9._/\-]+", result), result)

    def test_sanitize_empty_string_returns_default(self):
        self.assertEqual(cli.sanitize_branch_part(""), "unknown-issue")

    def test_sanitize_keeps_issue_key_intact(self):
        self.assertEqual(cli.sanitize_branch_part("APP-4827"), "app-4827")


if __name__ == "__main__":
    unittest.main()
