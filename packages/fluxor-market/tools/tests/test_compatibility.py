"""Tests for tools/compatibility.py, on synthetic manifests and on the real catalog."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import compatibility  # noqa: E402
import marketplace  # noqa: E402


def mod(mid, **extra):
    return {"id": mid, "kind": "mod", "precedence": extra.pop("precedence", "correctness"),
            "enforcement": "prompt", **extra}


class Compute(unittest.TestCase):
    def setUp(self):
        self.manifests = [
            mod("dry-run", incompatibleWith=["tests"], precedence="scope"),
            mod("tests"),
            mod("ds-a", exclusiveGroup="design-system", precedence="style"),
            mod("ds-b", exclusiveGroup="design-system", precedence="style"),
            mod("ds-c", exclusiveGroup="design-system", precedence="style", incompatibleWith=["ds-a"]),
            mod("secure", precedence="security"),
            {"id": "skill-x", "kind": "skill", "requires": {"atoms": ["engine@1"]}},
        ]
        self.matrix = compatibility.compute(self.manifests)

    def test_declarations_are_symmetric(self):
        self.assertEqual(self.matrix["mods"]["tests"]["incompatibleWith"], ["dry-run"])
        self.assertEqual(self.matrix["mods"]["dry-run"]["incompatibleWith"], ["tests"])

    def test_exclusive_groups_expand_to_pairs(self):
        pairs = {(p["a"], p["b"]): p["reasons"] for p in self.matrix["pairs"]}
        self.assertIn(("ds-a", "ds-b"), pairs)
        self.assertIn(("ds-b", "ds-c"), pairs)
        self.assertEqual(pairs[("ds-a", "ds-c")], ["declared by ds-c", "exclusive group design-system"])
        self.assertEqual(self.matrix["groups"], {"design-system": ["ds-a", "ds-b", "ds-c"]})

    def test_conflicts_and_order(self):
        found = compatibility.conflicts(["ds-a", "ds-b", "secure"], self.matrix)
        self.assertEqual([(p["a"], p["b"]) for p in found], [("ds-a", "ds-b")])
        ordered = compatibility.order_by_precedence(["ds-a", "dry-run", "tests", "secure"], self.matrix)
        self.assertEqual(ordered, ["secure", "tests", "dry-run", "ds-a"])

    def test_dependencies_and_one_sided(self):
        self.assertEqual(self.matrix["dependencies"], {"skill-x": ["engine@1"]})
        self.assertEqual(compatibility.one_sided(self.manifests), [("dry-run", "tests"), ("ds-c", "ds-a")])

    def test_matches_its_schema(self):
        store = marketplace.SchemaStore(REPO / "schemas")
        self.assertEqual(store.validate(self.matrix, "compatibility.schema.json"), [])


class RealCatalog(unittest.TestCase):
    def test_real_catalog_matrix_is_valid(self):
        atoms, errors = marketplace.load_catalog()
        self.assertEqual(errors, [])
        matrix = compatibility.compute([a.manifest for a in atoms])
        store = marketplace.SchemaStore(REPO / "schemas")
        self.assertEqual(store.validate(json.loads(json.dumps(matrix)), "compatibility.schema.json"), [])
        design = matrix["groups"].get("design-system", [])
        self.assertGreaterEqual(len(design), 2, "the design-system group should hold several mods")
        for a in design:
            for b in design:
                if a != b:
                    self.assertIn(b, matrix["mods"][a]["incompatibleWith"])


if __name__ == "__main__":
    unittest.main()
