"""Golden tests for scripts/analyze_traffic.py on real-shaped analytics exports.

The fixtures hold the same site twice: as an English GA4 export ("1,234,567", "38.4", ",") and as
a decimal-comma spreadsheet export ("1.234.567", "38,4", ";", BOM). Both must produce the golden
output, where the high-traffic pages keep their real view counts.

Run from the repository root:
    python3 -m unittest discover -s skills/traffic-to-funnel/tests
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "analyze_traffic.py"
FIXTURES = HERE / "fixtures"
EXPECTED = HERE / "expected"

sys.path.insert(0, str(SCRIPT.parent))
from analyze_traffic import parse_number  # noqa: E402


def run(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=60)


def analyze(locale):
    with tempfile.TemporaryDirectory() as tmp:
        out_json, out_md = Path(tmp) / "out.json", Path(tmp) / "out.md"
        result = run("--pages", str(FIXTURES / f"pages_{locale}.csv"), "--search", str(FIXTURES / f"search_{locale}.csv"),
                     "--json", str(out_json), "--md", str(out_md))
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(out_json.read_text(encoding="utf-8")), out_md.read_text(encoding="utf-8")


class ParseNumber(unittest.TestCase):
    def test_export_formats(self):
        cases = {
            "12,500": 12500, "1,234,567": 1234567, "1,234.56": 1234.56,
            "12.500": 12500, "1.234.567": 1234567, "1.234,56": 1234.56,
            "12,5": 12.5, "12.5": 12.5, "0,125": 0.125, "0.125": 0.125, "1234.567": 1234.567,
            "45%": 45, "4,5%": 4.5, "12 500": 12500, "12\u00a0500": 12500, "-1,234": -1234, "860": 860,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_number(text), expected)

    def test_file_locale_settles_a_single_group(self):
        self.assertEqual(parse_number("12.500", "."), 12.5)
        self.assertEqual(parse_number("12,500", ","), 12.5)
        self.assertEqual(parse_number("12.500", ","), 12500)
        self.assertEqual(parse_number("12,500", "."), 12500)

    def test_not_a_number(self):
        self.assertIsNone(parse_number("n/a"))
        self.assertIsNone(parse_number("1,2,3.4.5"))


class GoldenOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads((EXPECTED / "en.json").read_text(encoding="utf-8"))
        cls.golden_md = (EXPECTED / "en.md").read_text(encoding="utf-8")

    def test_english_export_matches_golden(self):
        res, md = analyze("en")
        self.assertEqual(res, self.golden)
        self.assertEqual(md, self.golden_md)

    def test_decimal_comma_export_matches_golden(self):
        res, md = analyze("eu")
        self.assertEqual(res, self.golden)
        self.assertEqual(md, self.golden_md)

    def test_high_traffic_pages_keep_their_views(self):
        for locale in ("en", "eu"):
            with self.subTest(locale=locale):
                pages = analyze(locale)[0]["pages"]["ranking"]
                by_views = sorted(pages, key=lambda p: p["views"] or 0, reverse=True)
                self.assertEqual([(p["url"], p["views"]) for p in by_views[:4]],
                                 [("/", 1234567), ("/pricing", 312450), ("/blog/hiring-guide", 98700),
                                  ("/features", 12500)])
                for p in by_views[:4]:
                    self.assertNotIn("insufficient_sample", p["signals"], p["url"])
                self.assertEqual([p["url"] for p in pages if "insufficient_sample" in p["signals"]], ["/old-landing"])
                ranked = [p["url"] for p in pages]
                self.assertEqual(ranked[:3], ["/blog/hiring-guide", "/pricing", "/"])

    def test_search_numbers(self):
        queries = {q["query"]: q for q in analyze("eu")[0]["search"]["queries"]}
        self.assertEqual(queries["recruiting software"]["impressions"], 310000)
        self.assertEqual(queries["hiring guide"]["clicks"], 9870)
        self.assertEqual(queries["ats for startups"]["ctr"], 0.023)
        self.assertEqual(queries["ats for startups"]["position"], 6.4)

    def test_markdown_on_a_legacy_windows_code_page(self):
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        result = run("--pages", str(FIXTURES / "pages_en.csv"), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("exit rate ≥ P75", result.stdout)


if __name__ == "__main__":
    unittest.main()
