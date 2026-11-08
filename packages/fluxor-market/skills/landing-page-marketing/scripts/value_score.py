#!/usr/bin/env python3
"""Compute the value perception score from per-lever scores (see references/audit-rubric.md).

Input JSON:
{
  "levers": {
    "clarity":         {"score": 2, "evidence": "H1 'Revolutionizing…' doesn't say what it is"},
    "outcome":         {"score": 1, "evidence": "..."},
    "proof":           {"score": 0, "evidence": "..."},
    "differentiation": {"score": 1, "evidence": "..."},
    "time":            {"score": 0, "evidence": "..."},
    "effort":          {"score": 1, "evidence": "..."},
    "risk":            {"score": 0, "evidence": "..."},
    "price_frame":     {"score": 0, "evidence": "..."}
  },
  "caps": ["fake_urgency"]
}

Prints the weighted total, the band, the applied cap and the lever to fix first ("the one thing"
candidate: the biggest weighted gap). Use --json to write the result, or --markdown for a table.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys

WEIGHTS = {"clarity": 15, "outcome": 15, "proof": 20, "differentiation": 10,
           "time": 10, "effort": 10, "risk": 10, "price_frame": 10}
CAPS = {"fabricated_proof": 40, "fake_urgency": 40, "broken_path": 30, "hidden_costs": 50,
        "no_first_screen_cta": 70}
BANDS = [(85, "Compelling"), (70, "Convincing"), (50, "Unclear value"), (30, "Weak"), (0, "Broken")]
LABELS = {"clarity": "Clarity & message match", "outcome": "Dream outcome", "proof": "Perceived likelihood (proof)",
          "differentiation": "Differentiation", "time": "Time to value", "effort": "Effort & sacrifice",
          "risk": "Risk reversal", "price_frame": "Price frame"}


def compute(data: dict) -> dict:
    levers = data.get("levers", {})
    errors = []
    for k in WEIGHTS:
        if k not in levers:
            errors.append(f"missing lever '{k}'")
            continue
        s = levers[k].get("score")
        if not isinstance(s, int) or not 0 <= s <= 5:
            errors.append(f"'{k}' score must be an integer 0-5 (got {s!r})")
        ev = (levers[k].get("evidence") or "").strip()
        if isinstance(s, int) and s > 2 and not ev:
            errors.append(f"'{k}' scores {s} but has no evidence (rubric: no evidence, no score above 2)")
    for k in levers:
        if k not in WEIGHTS:
            errors.append(f"unknown lever '{k}' (valid: {', '.join(WEIGHTS)})")
    unknown_caps = [c for c in data.get("caps", []) if c not in CAPS]
    if unknown_caps:
        errors.append(f"unknown caps {unknown_caps} (valid: {', '.join(CAPS)})")
    if errors:
        return {"errors": errors}
    raw = sum(WEIGHTS[k] * levers[k]["score"] / 5 for k in WEIGHTS)
    raw = round(raw)
    caps = data.get("caps", [])
    cap_val = min([CAPS[c] for c in caps], default=100)
    total = min(raw, cap_val)
    band = next(name for floor, name in BANDS if total >= floor)
    gaps = sorted(WEIGHTS, key=lambda k: (-(WEIGHTS[k] * (5 - levers[k]["score"])), k))
    return {"raw": raw, "total": total, "band": band, "caps_applied": caps if cap_val < raw else [],
            "cap_value": cap_val if cap_val < raw else None,
            "biggest_gaps": [{"lever": k, "score": levers[k]["score"], "points_lost": round(WEIGHTS[k] * (5 - levers[k]["score"]) / 5, 1)}
                             for k in gaps[:3]],
            "levers": {k: {"score": levers[k]["score"], "weight": WEIGHTS[k],
                           "points": round(WEIGHTS[k] * levers[k]["score"] / 5, 1),
                           "evidence": levers[k].get("evidence", "")} for k in WEIGHTS}}


def markdown(r: dict) -> str:
    lines = ["| Lever | Score 0–5 | Points | Evidence |", "|---|---|---|---|"]
    for k, v in r["levers"].items():
        lines.append(f"| {LABELS[k]} | {v['score']} | {v['points']}/{v['weight']} | {v['evidence']} |")
    lines.append("")
    cap = f" (capped from {r['raw']} by {', '.join(r['caps_applied'])})" if r["caps_applied"] else ""
    lines.append(f"**Value perception score: {r['total']}/100 ({r['band']})**{cap}")
    return "\n".join(lines)


def utf8_console():
    """Print non-ASCII (✓, ≥, —, emoji from the input) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scores", help="JSON file with levers and caps")
    ap.add_argument("--json", help="write the result here")
    ap.add_argument("--markdown", action="store_true", help="print a markdown table for the report")
    a = ap.parse_args()
    with open(a.scores, encoding="utf-8") as f:
        r = compute(json.load(f))
    if "errors" in r:
        print("INVALID:\n  - " + "\n  - ".join(r["errors"]))
        sys.exit(1)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    if a.markdown:
        print(markdown(r))
    else:
        cap = f" (capped from {r['raw']}: {', '.join(r['caps_applied'])})" if r["caps_applied"] else ""
        print(f"Value perception score: {r['total']}/100 ({r['band']}){cap}")
    print("Biggest gaps: " + ", ".join(f"{g['lever']} ({g['score']}/5, -{g['points_lost']} pts)" for g in r["biggest_gaps"]))


if __name__ == "__main__":
    main()
