"""gate.py: structural metrics decide exactly, timing metrics decide only on material evidence.

The timing samples are generated from fixed seeds, so every case is the same on every run.
Run from packages/fluxor-market:
    python3 -m unittest discover -s skills/ui-fluidity-verification/tests -t skills/ui-fluidity-verification/tests
"""

from __future__ import annotations

import io
import json
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import gate  # noqa: E402


def samples(seed: int, n: int, center: float, spread: float) -> list[float]:
    rng = random.Random(seed)
    return [round(rng.gauss(center, spread), 3) for _ in range(n)]


def one(metric: dict, **extra) -> dict:
    return gate.evaluate({"metrics": [metric], **extra})


class Structural(unittest.TestCase):
    def test_any_increase_beyond_tolerance_fails(self):
        r = one({"name": "cls", "class": "structural", "baseline": 0, "candidate": 0.031})
        self.assertEqual(r["verdict"], gate.FAIL)

    def test_within_tolerance_passes(self):
        r = one({"name": "loaf-count", "class": "structural", "baseline": 2, "candidate": 3, "tolerance": 1})
        self.assertEqual(r["verdict"], gate.PASS)

    def test_improvement_passes_and_asks_for_a_ratchet(self):
        r = one({"name": "forced-layouts", "class": "structural", "baseline": 4, "candidate": 1})
        self.assertEqual(r["verdict"], gate.PASS)
        self.assertIn("ratchet", r["metrics"][0]["detail"])

    def test_budget_alone_decides(self):
        self.assertEqual(one({"name": "b", "class": "structural", "candidate": 0, "budget": 0})["verdict"], gate.PASS)
        self.assertEqual(one({"name": "b", "class": "structural", "candidate": 1, "budget": 0})["verdict"], gate.FAIL)

    def test_higher_is_better_flips_the_direction(self):
        r = one({"name": "targets-ok", "class": "structural", "baseline": 10, "candidate": 9, "higherIsBetter": True})
        self.assertEqual(r["verdict"], gate.FAIL)

    def test_findings_fail_only_on_new_ids_counted_as_a_multiset(self):
        base = ["overlap:nav", "clipped-text:h1"]
        self.assertEqual(one({"name": "f", "class": "structural", "baseline": base,
                              "candidate": ["clipped-text:h1", "overlap:nav"]})["verdict"], gate.PASS)
        r = one({"name": "f", "class": "structural", "baseline": base,
                 "candidate": base + ["overlap:nav"]})
        self.assertEqual(r["verdict"], gate.FAIL)
        self.assertEqual(r["metrics"][0]["new"], ["overlap:nav"])

    def test_fixed_findings_are_reported(self):
        r = one({"name": "f", "class": "structural", "baseline": ["a", "b"], "candidate": ["a"]})
        self.assertEqual(r["verdict"], gate.PASS)
        self.assertEqual(r["metrics"][0]["fixed"], ["b"])


class Timing(unittest.TestCase):
    def metric(self, base, cand, **extra):
        return {"name": "tap-ms", "class": "timing", "baseline": base, "candidate": cand,
                "minEffect": 0.10, "minAbsolute": 4, **extra}

    def test_a_material_regression_fails(self):
        r = one(self.metric(samples(1, 30, 80, 4), samples(2, 30, 100, 4)))
        self.assertEqual(r["verdict"], gate.FAIL)

    def test_no_change_passes(self):
        r = one(self.metric(samples(3, 30, 80, 4), samples(4, 30, 80, 4)))
        self.assertEqual(r["verdict"], gate.PASS)

    def test_a_significant_but_immaterial_shift_passes(self):
        # 2% slower with tiny noise: real, detectable, and below the 10% / 4 ms threshold.
        r = one(self.metric(samples(5, 40, 80, 0.5), samples(6, 40, 81.6, 0.5)))
        self.assertEqual(r["verdict"], gate.PASS)
        self.assertLess(r["metrics"][0]["p"], 0.05)

    def test_noise_that_cannot_decide_is_inconclusive_with_a_sample_size(self):
        r = one(self.metric(samples(7, 12, 80, 30), samples(8, 12, 92, 30)))
        self.assertEqual(r["verdict"], gate.INCONCLUSIVE)
        self.assertGreater(r["metrics"][0]["suggestedSamples"], 12)

    def test_too_few_samples_is_inconclusive(self):
        r = one(self.metric([80, 81, 82], [120, 121, 122]))
        self.assertEqual(r["verdict"], gate.INCONCLUSIVE)

    def test_paired_samples_cancel_shared_drift(self):
        # A host that warms up (thermal drift) moves both sides together; the pairs still show +20.
        drift = [i * 5 for i in range(20)]
        base = [80 + d + e for d, e in zip(drift, samples(9, 20, 0, 1))]
        cand = [100 + d + e for d, e in zip(drift, samples(10, 20, 0, 1))]
        paired = one(self.metric(base, cand, paired=True))
        self.assertEqual(paired["verdict"], gate.FAIL)
        unpaired = one(self.metric(base, cand))
        self.assertEqual(unpaired["verdict"], gate.INCONCLUSIVE)

    def test_higher_is_better(self):
        r = one(self.metric(samples(11, 30, 60, 1), samples(12, 30, 45, 1), higherIsBetter=True))
        self.assertEqual(r["verdict"], gate.FAIL)

    def test_budget_over_fails_even_without_a_regression(self):
        r = one(self.metric(samples(13, 30, 250, 5), samples(14, 30, 250, 5), budget=200))
        self.assertEqual(r["verdict"], gate.FAIL)

    def test_noisy_calibration_makes_timing_abstain_but_not_structural(self):
        r = gate.evaluate({
            "calibration": {"samples": [10, 14, 9, 17, 11, 20, 8], "maxCv": 0.05},
            "metrics": [self.metric(samples(1, 30, 80, 4), samples(2, 30, 100, 4)),
                        {"name": "cls", "class": "structural", "baseline": 0, "candidate": 0.2}],
        })
        verdicts = {m["name"]: m["verdict"] for m in r["metrics"]}
        self.assertEqual(verdicts, {"tap-ms": gate.INCONCLUSIVE, "cls": gate.FAIL})
        self.assertFalse(r["calibration"]["ok"])

    def test_false_discovery_correction_spans_all_timing_metrics(self):
        # p = 0.0064: a discovery on its own, not among twenty metrics (BH needs 0.0025 there).
        weak = (samples(15, 15, 80, 6), samples(16, 15, 85, 6))
        alone = one(self.metric(*weak, minEffect=0, minAbsolute=0))
        self.assertEqual(alone["verdict"], gate.FAIL)
        crowd = gate.evaluate({"metrics": [self.metric(*weak, minEffect=0, minAbsolute=0)] + [
            {"name": f"other-{i}", "class": "timing", "baseline": samples(100 + i, 15, 50, 3),
             "candidate": samples(200 + i, 15, 50, 3), "minEffect": 0, "minAbsolute": 0} for i in range(19)]})
        crowd_verdict = next(m for m in crowd["metrics"] if m["name"] == "tap-ms")["verdict"]
        self.assertEqual(crowd_verdict, gate.INCONCLUSIVE)

    def test_the_verdict_is_reproducible(self):
        data = {"metrics": [self.metric(samples(7, 12, 80, 30), samples(8, 12, 92, 30))]}
        self.assertEqual(gate.evaluate(data), gate.evaluate(data))


class Overall(unittest.TestCase):
    def test_fail_beats_inconclusive_beats_pass(self):
        ok = {"name": "a", "class": "structural", "baseline": 0, "candidate": 0}
        unsure = {"name": "b", "class": "timing", "baseline": [1, 2], "candidate": [1, 2]}
        bad = {"name": "c", "class": "structural", "baseline": 0, "candidate": 1}
        self.assertEqual(gate.evaluate({"metrics": [ok]})["verdict"], gate.PASS)
        self.assertEqual(gate.evaluate({"metrics": [ok, unsure]})["verdict"], gate.INCONCLUSIVE)
        self.assertEqual(gate.evaluate({"metrics": [ok, unsure, bad]})["verdict"], gate.FAIL)

    def test_bad_input_is_rejected(self):
        for data in ({}, {"metrics": []}, {"metrics": [{"name": "x", "class": "vibes"}]},
                     {"metrics": [{"name": "x", "class": "structural", "candidate": 1}]},
                     {"metrics": [{"name": "x", "class": "structural", "baseline": 0, "candidate": 0},
                                  {"name": "x", "class": "structural", "baseline": 0, "candidate": 0}]}):
            with self.assertRaises(gate.BadInput):
                gate.evaluate(data)

    def test_exit_codes(self):
        cases = [({"name": "a", "class": "structural", "baseline": 0, "candidate": 0}, 0),
                 ({"name": "a", "class": "structural", "baseline": 0, "candidate": 1}, 1),
                 ({"name": "a", "class": "timing", "baseline": [1], "candidate": [1]}, 3)]
        with tempfile.TemporaryDirectory() as tmp:
            for metric, code in cases:
                path = Path(tmp) / "m.json"
                path.write_text(json.dumps({"metrics": [metric]}), encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(gate.main([str(path)]), code)
            path = Path(tmp) / "bad.json"
            path.write_text("{", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(gate.main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
