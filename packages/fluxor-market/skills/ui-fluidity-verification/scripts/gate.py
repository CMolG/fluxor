#!/usr/bin/env python3
"""gate.py: the three-valued UI quality gate of ui-fluidity-verification.

A gate that fails on noise gets disabled, and a disabled gate passes everything. So this one
never decides a stochastic signal from one number: it separates the two classes of evidence.

- structural metrics are deterministic under a pinned environment (layout-shift scores and
  sources, forced-layout counts, audit findings, non-composited animations, work counts). They
  are compared exactly, against the baseline and/or an absolute budget: any regression FAILS.
- timing metrics are samples (durations). A regression FAILS only when it is statistically
  significant after a false-discovery correction across all timing metrics, AND material: the
  confidence bound of the shift clears both a relative and an absolute threshold. When the
  evidence cannot tell, the verdict is INCONCLUSIVE, with the sample size that would decide it.
  A host whose calibration workload is too noisy makes every timing metric INCONCLUSIVE.

Usage:
    python3 scripts/gate.py <metrics.json> [--json] [--seed 1] [--resamples 2000]

Input:
{
  "alpha": 0.05,               false-discovery rate across the timing metrics (Benjamini-Hochberg)
  "confidence": 0.95,          one-sided confidence of the bootstrap bounds
  "calibration": {"samples": [12.1, 12.3, ...], "maxCv": 0.05},
  "metrics": [
    {"name": "cls", "class": "structural", "baseline": 0, "candidate": 0.031, "tolerance": 0},
    {"name": "audit", "class": "structural", "baseline": ["overlap:nav"], "candidate": ["overlap:nav", "clipped-text:h1"]},
    {"name": "tap-to-paint-ms", "class": "timing", "baseline": [..], "candidate": [..],
     "paired": true, "minEffect": 0.10, "minAbsolute": 4, "minSamples": 10, "budget": 200}
  ]
}

A metric is higher-is-worse unless it says "higherIsBetter": true. A list-valued structural
metric is a multiset of finding ids: any id the candidate has more of than the baseline fails.
"paired": true means sample i of both sides ran back to back (interleaved A/B on one host),
which cancels drift; it uses the Wilcoxon signed-rank test, otherwise Mann-Whitney U.

Exit: 0 PASS, 1 FAIL, 3 INCONCLUSIVE (nothing failed, something could not be decided), 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PASS, FAIL, INCONCLUSIVE = "PASS", "FAIL", "INCONCLUSIVE"
NORMAL = statistics.NormalDist()
MAX_SUGGESTED = 400


class BadInput(Exception):
    pass


# --- statistics ---------------------------------------------------------------------------------

def quantile(values: list[float], q: float) -> float:
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def ranks(values: list[float]) -> tuple[list[float], list[int]]:
    """Average ranks (1-based) and the sizes of the tie groups."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    ties = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        ties.append(j - i + 1)
        i = j + 1
    return out, ties


def mann_whitney_greater(b: list[float], c: list[float]) -> float:
    """One-sided p-value that `c` is stochastically greater than `b` (normal approximation with
    tie and continuity corrections)."""
    n1, n2 = len(c), len(b)
    r, ties = ranks(c + b)
    u = sum(r[:n1]) - n1 * (n1 + 1) / 2
    n = n1 + n2
    tie_term = sum(t ** 3 - t for t in ties) / (n * (n - 1))
    var = n1 * n2 / 12 * ((n + 1) - tie_term)
    if var <= 0:
        return 1.0
    z = (u - n1 * n2 / 2 - 0.5) / math.sqrt(var)
    return 1 - NORMAL.cdf(z)


def wilcoxon_greater(d: list[float]) -> float:
    """One-sided p-value that the paired differences `d` are centered above zero."""
    nz = [x for x in d if x != 0]
    n = len(nz)
    if n == 0:
        return 1.0
    r, ties = ranks([abs(x) for x in nz])
    w = sum(rk for rk, x in zip(r, nz) if x > 0)
    var = n * (n + 1) * (2 * n + 1) / 24 - sum(t ** 3 - t for t in ties) / 48
    if var <= 0:
        return 1.0
    z = (w - n * (n + 1) / 4 - 0.5) / math.sqrt(var)
    return 1 - NORMAL.cdf(z)


def robust_cv(values: list[float]) -> float:
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    return 1.4826 * mad / med if med else math.inf


def benjamini_hochberg(pvalues: dict[str, float], alpha: float) -> set[str]:
    """The names whose p-values are discoveries at false-discovery rate `alpha`."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    cutoff = 0
    for k, (_, p) in enumerate(ordered, 1):
        if p <= alpha * k / m:
            cutoff = k
    return {name for name, _ in ordered[:cutoff]}


# --- metrics ------------------------------------------------------------------------------------

def structural(m: dict) -> dict:
    name = m["name"]
    worse_up = not m.get("higherIsBetter", False)
    cand = m.get("candidate")
    base = m.get("baseline")
    budget = m.get("budget")
    if cand is None:
        raise BadInput(f"{name}: a structural metric needs a candidate")
    if base is None and budget is None:
        raise BadInput(f"{name}: a structural metric needs a baseline, a budget, or both")
    if isinstance(cand, list) or isinstance(base, list):
        if not isinstance(cand, list) or not isinstance(base, list):
            raise BadInput(f"{name}: a findings metric needs lists on both sides")
        new = Counter(map(str, cand)) - Counter(map(str, base))
        gone = Counter(map(str, base)) - Counter(map(str, cand))
        verdict = FAIL if new else PASS
        detail = f"{sum(new.values())} new" + (f": {', '.join(sorted(new))}" if new else "")
        if gone:
            detail += f"; {sum(gone.values())} fixed (ratchet the baseline)"
        return {"name": name, "class": "structural", "verdict": verdict, "detail": detail,
                "new": sorted(new.elements()), "fixed": sorted(gone.elements())}
    tol = float(m.get("tolerance", 0))
    reasons = []
    verdict = PASS
    if base is not None:
        delta = (cand - base) if worse_up else (base - cand)
        if delta > tol:
            verdict = FAIL
            reasons.append(f"{base:g} -> {cand:g} (tolerance {tol:g})")
        elif delta < 0:
            reasons.append(f"{base:g} -> {cand:g}, better (ratchet the baseline)")
        else:
            reasons.append(f"{base:g} -> {cand:g}")
    if budget is not None:
        over = cand > budget if worse_up else cand < budget
        if over:
            verdict = FAIL
            reasons.append(f"over the budget of {budget:g}")
        elif base is None:
            reasons.append(f"{cand:g} within the budget of {budget:g}")
    return {"name": name, "class": "structural", "verdict": verdict, "detail": "; ".join(reasons)}


def bootstrap(stat, groups, resamples: int, rng: random.Random) -> list[float]:
    out = []
    for _ in range(resamples):
        out.append(stat(*[[g[rng.randrange(len(g))] for _ in g] for g in groups]))
    return out


def timing(m: dict, conf: float, resamples: int, seed: int, noisy: str | None) -> dict:
    name = m["name"]
    b = [float(x) for x in m.get("baseline", [])]
    c = [float(x) for x in m.get("candidate", [])]
    paired = bool(m.get("paired", False))
    worse_up = not m.get("higherIsBetter", False)
    min_effect = float(m.get("minEffect", 0.10))
    min_abs = float(m.get("minAbsolute", 0))
    n_min = int(m.get("minSamples", 10))
    budget = m.get("budget")
    out = {"name": name, "class": "timing", "n": [len(b), len(c)], "paired": paired}
    if paired and len(b) != len(c):
        raise BadInput(f"{name}: paired samples need the same count on both sides")
    if noisy:
        return {**out, "verdict": INCONCLUSIVE, "detail": noisy}
    if min(len(b), len(c)) < n_min:
        return {**out, "verdict": INCONCLUSIVE, "detail": f"needs at least {n_min} samples per side",
                "suggestedSamples": n_min}

    # Orient everything so that "greater" means "worse".
    sign = 1 if worse_up else -1
    rng = random.Random(f"{seed}:{name}")
    lo_q, hi_q = 1 - conf, conf
    med_b, med_c = statistics.median(b), statistics.median(c)
    if paired:
        d = [sign * (y - x) for x, y in zip(b, c)]
        p = wilcoxon_greater(d)
        pairs = list(zip(b, c))
        shifts = bootstrap(lambda s: statistics.median([sign * (y - x) for x, y in s]), [pairs], resamples, rng)
        ratios = bootstrap(lambda s: ratio(statistics.median([x for x, _ in s]), statistics.median([y for _, y in s]), worse_up),
                           [pairs], resamples, rng)
        spread = statistics.median([abs(x - statistics.median(d)) for x in d]) * 1.4826
    else:
        p = mann_whitney_greater(b, c) if worse_up else mann_whitney_greater(c, b)
        shifts = bootstrap(lambda x, y: sign * (statistics.median(y) - statistics.median(x)), [b, c], resamples, rng)
        ratios = bootstrap(lambda x, y: ratio(statistics.median(x), statistics.median(y), worse_up), [b, c], resamples, rng)
        spread = math.sqrt((robust_spread(b) ** 2 + robust_spread(c) ** 2) / 2)
    shift_lo, shift_hi = quantile(shifts, lo_q), quantile(shifts, hi_q)
    ratio_lo, ratio_hi = quantile(ratios, lo_q), quantile(ratios, hi_q)
    relative = med_b != 0
    material_lo = shift_lo > min_abs and (not relative or ratio_lo > 1 + min_effect)
    immaterial_hi = shift_hi <= min_abs or (relative and ratio_hi <= 1 + min_effect)
    out.update({
        "medianBaseline": round(med_b, 3), "medianCandidate": round(med_c, 3), "p": round(p, 6),
        "shiftBounds": [round(shift_lo, 3), round(shift_hi, 3)],
        "ratioBounds": [round(ratio_lo, 4), round(ratio_hi, 4)] if relative else None,
        "materialLow": material_lo, "immaterialHigh": immaterial_hi,
    })
    delta = max(min_abs, min_effect * abs(med_b)) or spread
    if spread > 0 and delta > 0:
        # Two-sample normal-theory size, inflated by 1/0.955 for a rank test's efficiency.
        z = NORMAL.inv_cdf(conf) + NORMAL.inv_cdf(0.8)
        need = (1 if paired else 2) * (z * spread / delta) ** 2 / 0.955
        out["suggestedSamples"] = min(MAX_SUGGESTED, max(n_min, math.ceil(need)))
    if budget is not None:
        cand_meds = bootstrap(lambda y: statistics.median(y), [c], resamples, rng)
        b_lo, b_hi = quantile(cand_meds, lo_q), quantile(cand_meds, hi_q)
        out["budgetBounds"] = [round(b_lo, 3), round(b_hi, 3)]
        over_lo = b_lo > budget if worse_up else b_hi < budget
        under_hi = b_hi <= budget if worse_up else b_lo >= budget
        out["budget"] = {"value": budget, "state": "over" if over_lo else "within" if under_hi else "undecided"}
    return out


def ratio(base_med: float, cand_med: float, worse_up: bool) -> float:
    if worse_up:
        return cand_med / base_med if base_med else (math.inf if cand_med > 0 else 1.0)
    return base_med / cand_med if cand_med else math.inf


def robust_spread(values: list[float]) -> float:
    med = statistics.median(values)
    return 1.4826 * statistics.median([abs(v - med) for v in values])


def decide_timing(results: list[dict], alpha: float) -> None:
    pvals = {r["name"]: r["p"] for r in results if "p" in r}
    discoveries = benjamini_hochberg(pvals, alpha) if pvals else set()
    for r in results:
        if "verdict" in r:
            continue
        significant = r["name"] in discoveries
        unit = f"median {r['medianBaseline']:g} -> {r['medianCandidate']:g}"
        bounds = f"shift in [{r['shiftBounds'][0]:g}, {r['shiftBounds'][1]:g}]"
        if r["ratioBounds"]:
            bounds += f", x[{r['ratioBounds'][0]:g}, {r['ratioBounds'][1]:g}]"
        budget = r.get("budget")
        if (r["materialLow"] and significant) or (budget and budget["state"] == "over"):
            r["verdict"] = FAIL
            why = "regression: significant after FDR and material at the confidence bound" if r["materialLow"] and significant \
                else f"over the budget of {budget['value']:g}"
        elif r["immaterialHigh"] and (not budget or budget["state"] == "within"):
            r["verdict"] = PASS
            why = "any regression is below the material threshold"
        else:
            r["verdict"] = INCONCLUSIVE
            why = "the evidence cannot separate a material regression from noise"
            if r.get("suggestedSamples"):
                n = r["suggestedSamples"]
                why += f"; about {n} samples per side would decide it" if n < MAX_SUGGESTED else \
                    "; the effect is below what this host's noise can resolve: measure work, not time"
        r["detail"] = f"{unit} ({bounds}, p={r['p']:.4f}); {why}"


def evaluate(data: dict, seed: int = 1, resamples: int = 2000) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("metrics"), list) or not data["metrics"]:
        raise BadInput("the input needs a non-empty \"metrics\" list")
    alpha = float(data.get("alpha", 0.05))
    conf = float(data.get("confidence", 0.95))
    if not 0.5 < conf < 1:
        raise BadInput("confidence must be in (0.5, 1)")
    noisy = None
    calibration = None
    cal = data.get("calibration")
    if cal:
        samples = [float(x) for x in cal.get("samples", [])]
        max_cv = float(cal.get("maxCv", 0.05))
        if len(samples) < 5:
            raise BadInput("calibration needs at least 5 samples")
        cv = robust_cv(samples)
        calibration = {"cv": round(cv, 4), "maxCv": max_cv, "ok": cv <= max_cv}
        if cv > max_cv:
            noisy = f"host too noisy for timing: calibration CV {cv:.1%} > {max_cv:.1%}"
    names = [m.get("name") for m in data["metrics"]]
    if None in names or len(set(names)) != len(names):
        raise BadInput("every metric needs a unique name")
    results = []
    for m in data["metrics"]:
        kind = m.get("class")
        if kind == "structural":
            results.append(structural(m))
        elif kind == "timing":
            results.append(timing(m, conf, resamples, seed, noisy))
        else:
            raise BadInput(f"{m['name']}: class must be \"structural\" or \"timing\"")
    decide_timing([r for r in results if r["class"] == "timing"], alpha)
    counts = Counter(r["verdict"] for r in results)
    verdict = FAIL if counts[FAIL] else INCONCLUSIVE if counts[INCONCLUSIVE] else PASS
    return {"verdict": verdict, "counts": dict(counts), "calibration": calibration, "metrics": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Three-valued UI quality gate: structural exact, timing statistical.")
    ap.add_argument("metrics", help="metrics JSON file (see the module docstring)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--seed", type=int, default=1, help="bootstrap seed (the verdict is reproducible)")
    ap.add_argument("--resamples", type=int, default=2000, help="bootstrap resamples (2000)")
    args = ap.parse_args(argv)
    try:
        data = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
        result = evaluate(data, args.seed, args.resamples)
    except (OSError, json.JSONDecodeError, BadInput, KeyError, TypeError, ValueError) as err:
        print(f"gate.py: {err}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["calibration"]:
            c = result["calibration"]
            print(f"calibration CV {c['cv']:.1%} (max {c['maxCv']:.1%}): {'ok' if c['ok'] else 'TOO NOISY, timing abstains'}")
        for r in result["metrics"]:
            print(f"{r['verdict']:<12} {r['name']:<28} {r['class']:<10} {r['detail']}")
        counts = ", ".join(f"{v} {k.lower()}" for k, v in sorted(result["counts"].items()))
        print(f"verdict: {result['verdict']} ({counts})")
    return {PASS: 0, FAIL: 1, INCONCLUSIVE: 3}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
