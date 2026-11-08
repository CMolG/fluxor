#!/usr/bin/env python3
"""Retrieve the person's real decisions closest to a task (plan item 2.1).

A few demonstrations of a person's own decisions move a model toward that person more than pages of
directives do. A pack keeps them in `examples/decisions.json`; this script ranks them against the
task with BM25 and prints the closest ones, to put into the task at hand.

  examples.py select --pack <pack> --task "review this migration that adds a NOT NULL column" [-k 5]
  examples.py inject --pack <pack>     Claude Code UserPromptSubmit hook: reads the payload on stdin
                                       and prints the closest decisions as context (fails open)

The render copies this file into the pack's `bin/`. Standard library only (Python 3.9+).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

STOP = set("a an and are as at be but by for from has have i if in into is it its my of on or so that the "
           "their them then there these they this to was we were what when where which who will with you your".split())
MIN_SCORE = 1.0


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1]


def document(decision: dict) -> str:
    return " ".join([decision.get("domain", "").replace("_", " "), decision.get("situation", ""),
                     " ".join(decision.get("cues", [])), decision.get("choice", ""), decision.get("rationale", "")])


def rank(decisions: list[dict], task: str, k: int) -> list[tuple[float, dict]]:
    docs = [tokens(document(d)) for d in decisions]
    if not docs:
        return []
    avg = sum(len(d) for d in docs) / len(docs) or 1.0
    df: dict[str, int] = {}
    for doc in docs:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
    query = set(tokens(task))
    scored = []
    for decision, doc in zip(decisions, docs):
        score = 0.0
        for term in query:
            tf = doc.count(term)
            if not tf:
                continue
            idf = math.log(1 + (len(docs) - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(doc) / avg))
        scored.append((score, decision))
    scored.sort(key=lambda pair: -pair[0])
    return [pair for pair in scored[:k] if pair[0] > 0]


def render(decision: dict) -> str:
    lines = [f"- **{decision['id']}** ({decision.get('domain', 'general')}, {decision.get('when', 'undated')}, "
             f"from {decision.get('source', '?')}): {decision['situation']}"]
    if decision.get("cues"):
        lines.append(f"  - What I noticed: {'; '.join(decision['cues'])}")
    if decision.get("options"):
        lines.append(f"  - Options: {'; '.join(decision['options'])}")
    lines.append(f"  - What I did: {decision['choice']}")
    lines.append(f"  - Why: {decision['rationale']}")
    if decision.get("noviceWould"):
        lines.append(f"  - What a less experienced person would do: {decision['noviceWould']}")
    return "\n".join(lines)


def load(pack: Path) -> list[dict]:
    return json.loads((pack / "examples" / "decisions.json").read_text(encoding="utf-8")).get("decisions", [])


def cmd_select(args) -> int:
    picks = rank(load(args.pack), args.task, args.k)
    if args.json:
        print(json.dumps([{"score": round(s, 3), **d} for s, d in picks], indent=2, ensure_ascii=False))
        return 0
    if not picks:
        print("no recorded decision resembles this task")
        return 0
    print("Decisions I made in similar cases (follow what I did and why, unless the task says otherwise):\n")
    print("\n".join(render(d) for _, d in picks))
    return 0


def cmd_inject(args) -> int:
    try:
        payload = json.load(sys.stdin)
        picks = [(s, d) for s, d in rank(load(args.pack), payload.get("prompt", ""), args.k) if s >= MIN_SCORE]
    except Exception as exc:  # fail open: never block a prompt
        print(f"examples: skipped ({exc})", file=sys.stderr)
        return 0
    if picks:
        print("Decisions the pack's person made in similar cases:\n")
        print("\n".join(render(d) for _, d in picks))
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("select")
    p.add_argument("--pack", required=True, type=Path)
    p.add_argument("--task", required=True)
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_select)
    p = sub.add_parser("inject")
    p.add_argument("--pack", required=True, type=Path)
    p.add_argument("-k", type=int, default=3)
    p.set_defaults(func=cmd_inject)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
