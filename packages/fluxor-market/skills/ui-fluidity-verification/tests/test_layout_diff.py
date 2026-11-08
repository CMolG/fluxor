"""layout_diff.py: a cascade of moved boxes reduces to the change that caused it.

Run from packages/fluxor-market:
    python3 -m unittest discover -s skills/ui-fluidity-verification/tests -t skills/ui-fluidity-verification/tests
"""

from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import layout_diff  # noqa: E402

VIEWPORT = {"width": 390, "height": 800, "dpr": 3}


def page() -> dict:
    """header with a title; main with a card (heading + text) and a footer below."""
    nodes = [
        ("header", None, [0, 0, 390, 60]),
        ("header > h1", "header", [16, 16, 200, 28]),
        ("main", None, [0, 60, 390, 400]),
        ("main > card", "main", [16, 76, 358, 200]),
        ("main > card > h2", "main > card", [32, 92, 326, 24]),
        ("main > card > p", "main > card", [32, 124, 326, 120]),
        ("main > list", "main", [16, 292, 358, 150]),
        ("main > list > item", "main > list", [16, 292, 358, 50]),
        ("footer", None, [0, 460, 390, 80]),
        ("footer > a", "footer", [16, 476, 100, 24]),
    ]
    return {"viewport": dict(VIEWPORT), "nodes": [{"key": k, "parent": p, "rect": r} for k, p, r in nodes]}


def edit(snapshot: dict, key: str, dx=0, dy=0, dw=0, dh=0) -> None:
    for n in snapshot["nodes"]:
        if n["key"] == key:
            x, y, w, h = n["rect"]
            n["rect"] = [x + dx, y + dy, w + dw, h + dh]


def origins(result: dict) -> list[list[str]]:
    return [[o["key"] for o in c["origins"]] for c in result["clusters"]]


class Diff(unittest.TestCase):
    def test_identical_snapshots_have_no_cluster(self):
        r = layout_diff.diff(page(), page())
        self.assertEqual(r["clusters"], [])

    def test_sub_tolerance_noise_is_no_change(self):
        cand = page()
        edit(cand, "main > card > p", dh=0.3)
        self.assertEqual(layout_diff.diff(page(), cand)["clusters"], [])

    def test_a_growing_paragraph_is_one_cluster_with_one_origin(self):
        cand = page()
        edit(cand, "main > card > p", dh=24)        # the cause
        edit(cand, "main > card", dh=24)            # its container grows
        edit(cand, "main", dh=24)
        edit(cand, "main > list", dy=24)            # displaced sibling
        edit(cand, "main > list > item", dy=24)     # carried with it
        edit(cand, "footer", dy=24)
        edit(cand, "footer > a", dy=24)             # carried with the footer
        r = layout_diff.diff(page(), cand)
        self.assertEqual(len(r["clusters"]), 1)
        self.assertEqual(origins(r), [["main > card > p"]])
        self.assertEqual(r["carried"], 2)

    def test_an_added_box_is_the_origin(self):
        cand = page()
        cand["nodes"].insert(1, {"key": "header > banner", "parent": "header", "rect": [0, 0, 390, 40]})
        edit(cand, "header", dh=40)
        edit(cand, "header > h1", dy=40)
        r = layout_diff.diff(page(), cand)
        self.assertEqual(len(r["clusters"]), 1)
        self.assertIn("header > banner", origins(r)[0])

    def test_a_removed_box_is_reported(self):
        cand = page()
        cand["nodes"] = [n for n in cand["nodes"] if n["key"] != "footer > a"]
        r = layout_diff.diff(page(), cand)
        self.assertEqual(origins(r), [["footer > a"]])
        self.assertEqual(r["clusters"][0]["origins"][0]["change"], "removed")

    def test_a_container_that_narrows_is_an_origin_of_its_rewrap(self):
        cand = page()
        edit(cand, "main > card", dw=-100)
        edit(cand, "main > card > h2", dw=-100)
        edit(cand, "main > card > p", dw=-100, dh=40)
        r = layout_diff.diff(page(), cand)
        self.assertEqual(len(r["clusters"]), 1)
        self.assertIn("main > card", origins(r)[0])

    def test_a_box_that_moves_alone_is_its_own_origin(self):
        cand = page()
        edit(cand, "header > h1", dx=12)
        r = layout_diff.diff(page(), cand)
        self.assertEqual(origins(r), [["header > h1"]])

    def test_two_independent_changes_are_two_clusters(self):
        cand = page()
        edit(cand, "header > h1", dx=12)
        edit(cand, "footer > a", dw=30)
        r = layout_diff.diff(page(), cand)
        self.assertEqual(origins(r), [["header > h1"], ["footer > a"]])

    def test_different_viewports_are_not_comparable(self):
        cand = page()
        cand["viewport"]["dpr"] = 2
        with self.assertRaises(layout_diff.BadInput):
            layout_diff.diff(page(), cand)


class Cli(unittest.TestCase):
    def run_cli(self, base: dict, cand: dict) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            b, c = Path(tmp) / "b.json", Path(tmp) / "c.json"
            b.write_text(json.dumps(base), encoding="utf-8")
            c.write_text(json.dumps(cand), encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return layout_diff.main([str(b), str(c)])

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(page(), page()), 0)
        cand = page()
        edit(cand, "header > h1", dx=12)
        self.assertEqual(self.run_cli(page(), cand), 1)
        bad = copy.deepcopy(page())
        bad["nodes"][0]["rect"] = [1, 2]
        self.assertEqual(self.run_cli(page(), bad), 2)


if __name__ == "__main__":
    unittest.main()
