"""breakpoints.py: thresholds from every query syntax, and the matrix they imply.

Run from packages/fluxor-market:
    python3 -m unittest discover -s skills/ui-fluidity-verification/tests -t skills/ui-fluidity-verification/tests
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import breakpoints  # noqa: E402


def values(css: str, kind: str = "media", axis: str = "width") -> list[tuple[float, str]]:
    return sorted((t["value"], t["unit"]) for t in breakpoints.thresholds(css, "t.css")
                  if t["kind"] == kind and t["axis"] == axis)


class Thresholds(unittest.TestCase):
    def test_min_and_max_width_in_px(self):
        css = "@media (min-width: 640px) { a {} } @media screen and (max-width: 1023.98px) { b {} }"
        self.assertEqual(values(css), [(640.0, "px"), (1023.98, "px")])

    def test_range_syntax_both_sides_and_reversed(self):
        css = "@media (width >= 40rem) {} @media (40rem <= width < 64rem) {} @media (768px < width) {}"
        self.assertEqual(values(css), [(40.0, "rem"), (40.0, "rem"), (64.0, "rem"), (768.0, "px")])

    def test_height_features_go_to_the_height_axis(self):
        css = "@media (max-height: 500px) and (orientation: landscape) {}"
        self.assertEqual(values(css, axis="height"), [(500.0, "px")])
        self.assertEqual(values(css), [])

    def test_container_queries_are_kept_apart(self):
        css = "@container sidebar (min-width: 400px) {} @container (inline-size > 30em) {}"
        self.assertEqual(values(css, kind="container"), [(30.0, "em"), (400.0, "px")])
        self.assertEqual(values(css), [])

    def test_non_size_features_and_comments_are_ignored(self):
        css = "/* @media (min-width: 999px) {} */ @media (min-resolution: 2dppx) {} @media (prefers-reduced-motion) {}"
        self.assertEqual(values(css), [])

    def test_tailwind_theme_variables_are_declared_thresholds(self):
        css = "@theme { --breakpoint-sm: 40rem; --container-md: 28rem; }"
        self.assertEqual(values(css), [(40.0, "rem")])
        self.assertEqual(values(css, kind="container"), [(28.0, "rem")])

    def test_source_line_is_kept(self):
        found = breakpoints.thresholds("a {}\n\n@media (min-width: 640px) {}", "app.css")
        self.assertEqual(found[0]["source"], "app.css:3")


class Matrix(unittest.TestCase):
    def test_both_sides_of_each_threshold_floor_and_ceil(self):
        found = breakpoints.thresholds("@media (min-width: 640px) {}", "t.css")
        m = breakpoints.matrix(found, 16, [1], 320, 1920, [], [])
        self.assertEqual(m["1"]["widths"], [320, 639, 640, 641, 1920])

    def test_fractional_threshold_gets_floor_and_ceil(self):
        found = breakpoints.thresholds("@media (max-width: 1023.98px) {}", "t.css")
        m = breakpoints.matrix(found, 16, [1], 320, 1920, [], [])
        self.assertEqual(m["1"]["widths"], [320, 1023, 1024, 1920])

    def test_em_thresholds_move_with_the_user_font_scale_px_do_not(self):
        found = breakpoints.thresholds("@media (width >= 40rem) {} @media (min-width: 900px) {}", "t.css")
        m = breakpoints.matrix(found, 16, [1, 1.25], 320, 1920, [], [])
        self.assertIn(640, m["1"]["widths"])
        self.assertIn(800, m["1.25"]["widths"])
        self.assertNotIn(640, m["1.25"]["widths"])
        self.assertIn(900, m["1"]["widths"])
        self.assertIn(900, m["1.25"]["widths"])

    def test_widths_below_the_floor_are_reported_not_rendered(self):
        found = breakpoints.thresholds("@media (min-width: 280px) {}", "t.css")
        m = breakpoints.matrix(found, 16, [1], 320, 1920, [], [])
        self.assertEqual(m["1"]["belowFloor"], [279, 280, 281])
        self.assertNotIn(280, m["1"]["widths"])

    def test_extra_sizes_are_included(self):
        m = breakpoints.matrix([], 16, [1], 320, 1920, [390], [360])
        self.assertEqual(m["1"]["widths"], [320, 390, 1920])
        self.assertEqual(m["1"]["heights"], [360])

    def test_container_sizes_are_listed_apart(self):
        found = breakpoints.thresholds("@container (min-width: 400px) {}", "t.css")
        self.assertEqual(breakpoints.containers(found, 16), {"inline": [399, 400, 401], "block": []})


class Cli(unittest.TestCase):
    def test_reads_directories_skips_node_modules_and_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.css").write_text("@media (min-width: 768px) {}", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "lib.css").write_text("@media (min-width: 1234px) {}", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = breakpoints.main([tmp, "--json", "--scales", "1"])
            self.assertEqual(code, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["files"], 1)
            self.assertEqual(result["matrix"]["1"]["widths"], [320, 767, 768, 769, 1920])


if __name__ == "__main__":
    unittest.main()
