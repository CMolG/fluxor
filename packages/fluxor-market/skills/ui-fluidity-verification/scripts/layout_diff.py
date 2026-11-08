#!/usr/bin/env python3
"""layout_diff.py: structural layout regression, from two geometry snapshots.

A pixel diff fails on antialiasing, font hinting and GPU differences, and when it fails for a
real reason it reports 4,000 changed pixels for one cause. This compares the boxes instead: two
snapshots of the same page, state and viewport (probe.js `__fluidity.snapshot()`), matched by
stable keys, and reduces a cascade of moved boxes to its causes.

- A box that only moved, by the same offset as its nearest matched ancestor, was carried: it is
  dropped (counted, not reported).
- Every other changed box (added, removed, resized, or moved on its own) joins a change cluster:
  boxes are linked to a changed parent and to changed siblings, so a header that grew and the
  content it pushed down are one cluster, not two hundred findings.
- Each cluster names its probable origins: added and removed boxes, the deepest resized boxes
  (block sizes flow up from content), the topmost box if its inline size changed (inline sizes
  flow down from the container), and boxes that moved with no change around them.

Usage:
    python3 scripts/layout_diff.py <baseline.json> <candidate.json> [--tolerance 0.5] [--json]

Exit: 0 no structural change, 1 at least one change cluster, 2 bad input or snapshots that are
not comparable (different viewport or device pixel ratio).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class BadInput(Exception):
    pass


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise BadInput(f"{path}: not a snapshot (no \"nodes\" list)")
    for n in data["nodes"]:
        if not isinstance(n, dict) or "key" not in n or len(n.get("rect", [])) != 4:
            raise BadInput(f"{path}: every node needs a key and a rect [x, y, width, height]")
    return data


def diff(base: dict, cand: dict, tol: float = 0.5) -> dict:
    vb, vc = base.get("viewport", {}), cand.get("viewport", {})
    for k in ("width", "height", "dpr"):
        if vb.get(k) != vc.get(k):
            raise BadInput(f"snapshots are not comparable: viewport {k} {vb.get(k)} vs {vc.get(k)}")
    B = {n["key"]: n for n in base["nodes"]}
    C = {n["key"]: n for n in cand["nodes"]}
    common = [k for k in C if k in B]
    added = [k for k in C if k not in B]
    removed = [k for k in B if k not in C]

    def zero(v: float) -> float:
        return 0.0 if abs(v) <= tol else round(v, 3)

    delta = {}
    for k in common:
        (bx, by, bw, bh), (cx, cy, cw, ch) = B[k]["rect"], C[k]["rect"]
        delta[k] = (zero(cx - bx), zero(cy - by), zero(cw - bw), zero(ch - bh))

    def parent(k: str) -> str | None:
        node = C.get(k) or B.get(k)
        return node.get("parent")

    def nearest_common_ancestor(k: str) -> str | None:
        p = parent(k)
        while p is not None and p not in delta:
            p = parent(p)
        return p

    resized = {k for k, (_, _, dw, dh) in delta.items() if dw or dh}
    moved = {k for k, (dx, dy, _, _) in delta.items() if dx or dy}
    reparented = {k for k in common if B[k].get("parent") != C[k].get("parent")}
    carried = set()
    for k in moved - resized - reparented:
        a = nearest_common_ancestor(k)
        if a is not None and delta[a][:2] == delta[k][:2]:
            carried.add(k)
    changed = (resized | moved | reparented | set(added) | set(removed)) - carried

    # Clusters: union-find over changed boxes, linking each to a changed parent and to its changed
    # siblings (a sibling's growth is what displaces the next one).
    up = {k: k for k in changed}

    def find(k: str) -> str:
        while up[k] != k:
            up[k] = up[up[k]]
            k = up[k]
        return k

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            up[max(ra, rb)] = min(ra, rb)

    by_parent: dict[str | None, list[str]] = {}
    for k in sorted(changed):
        p = parent(k)
        by_parent.setdefault(p, []).append(k)
        if p in changed:
            union(k, p)
    for kids in by_parent.values():
        for k in kids[1:]:
            union(kids[0], k)

    order = {k: i for i, k in enumerate([n["key"] for n in cand["nodes"]] + removed)}
    groups: dict[str, list[str]] = {}
    for k in changed:
        groups.setdefault(find(k), []).append(k)

    def is_descendant(k: str, of: str) -> bool:
        p = parent(k)
        while p is not None:
            if p == of:
                return True
            p = parent(p)
        return False

    def change_of(k: str) -> dict:
        if k in added:
            return {"key": k, "change": "added", "rect": C[k]["rect"]}
        if k in removed:
            return {"key": k, "change": "removed", "rect": B[k]["rect"]}
        dx, dy, dw, dh = delta[k]
        kinds = [c for c, on in (("resized", dw or dh), ("moved", dx or dy), ("reparented", k in reparented)) if on]
        return {"key": k, "change": "+".join(kinds), "delta": {"x": dx, "y": dy, "width": dw, "height": dh}}

    clusters = []
    for members in groups.values():
        members.sort(key=lambda k: order.get(k, 0))
        top = [k for k in members if not any(is_descendant(k, other) for other in members if other != k)]
        origins = []
        for k in members:
            if k in added or k in removed or k in reparented:
                origins.append(k)
            elif k in resized and not any(is_descendant(o, k) for o in members if o in resized or o in added or o in removed):
                origins.append(k)
        for k in top:
            if k in delta and delta[k][2] and k not in origins:
                origins.append(k)  # its inline size changed and nothing above it did
        siblings_changed = {p: len(kids) for p, kids in by_parent.items()}
        for k in members:
            if k in moved and k not in resized and k not in origins and siblings_changed.get(parent(k), 0) == 1 \
                    and parent(k) not in changed:
                origins.append(k)  # moved with no change around it: alignment, order or offset
        clusters.append({
            "extent": [change_of(k) for k in top],
            "origins": [change_of(k) for k in sorted(set(origins), key=lambda k: order.get(k, 0))],
            "size": len(members),
        })
    clusters.sort(key=lambda c: order.get(c["extent"][0]["key"], 0))
    return {
        "tolerance": tol,
        "viewport": vc,
        "compared": len(common),
        "added": len(added),
        "removed": len(removed),
        "carried": len(carried),
        "changed": len(changed),
        "clusters": clusters,
    }


def describe(c: dict) -> str:
    if "delta" not in c:
        return f"{c['change']} {c['key']}"
    d = c["delta"]
    parts = [f"{k}{v:+g}" for k, v in d.items() if v]
    return f"{c['change']} {c['key']} ({', '.join(parts)})"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Structural layout regression between two probe.js snapshots.")
    ap.add_argument("baseline", help="baseline snapshot JSON")
    ap.add_argument("candidate", help="candidate snapshot JSON")
    ap.add_argument("--tolerance", type=float, default=0.5,
                    help="CSS px under which a delta is no change (0.5; 1/64 for the same engine and host)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    try:
        result = diff(load(args.baseline), load(args.candidate), args.tolerance)
    except (OSError, json.JSONDecodeError, BadInput) as err:
        print(f"layout_diff.py: {err}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['compared']} boxes compared, {result['added']} added, {result['removed']} removed, "
              f"{result['carried']} carried by their parent; {len(result['clusters'])} change clusters")
        for i, c in enumerate(result["clusters"], 1):
            print(f"{i}. {c['size']} changed boxes under {', '.join(e['key'] for e in c['extent'])}")
            for o in c["origins"]:
                print(f"   origin? {describe(o)}")
    return 1 if result["clusters"] else 0


if __name__ == "__main__":
    sys.exit(main())
