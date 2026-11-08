#!/usr/bin/env python3
"""breakpoints.py: derive the viewport matrix a layout must be verified at from the CSS itself.

A layout is piecewise: it only changes shape where a media or container query flips (or where
content wraps). So the widths worth rendering are the ones on both sides of every threshold the
stylesheets declare, at every user font scale, plus the floor and ceiling the product supports.
Testing "mobile, tablet, desktop" checks three points of a function whose breaks are elsewhere.

Usage:
    python3 scripts/breakpoints.py <css file or dir> [more...] [--json]
        [--base 16] [--scales 1,1.25,1.5,2] [--floor 320] [--ceil 1920]
        [--extra-widths 360,390] [--extra-heights 360]

Directories are searched for *.css (node_modules skipped unless named directly). Point it at the
BUILT css (`.next/static/css`, `dist/`) when a utility framework generates the queries: only the
built output holds the thresholds that are actually used. Tailwind v4 `--breakpoint-*` and
`--container-*` theme variables are read too, as declared (possibly unused) thresholds.

em and rem in a media query are relative to the user's default font size, not to the root
element's font-size: a 40rem breakpoint fires at 800px for someone who set 20px. So em/rem
thresholds move with each scale in --scales and px thresholds do not. Container thresholds are
container sizes, not viewport sizes: they are listed apart, for a harness that sizes the container.

Exit code 0; 2 on bad arguments.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RULE = re.compile(r"@(media|container)\b([^{;]*)\{", re.I)
GROUP = re.compile(r"\(([^()]*)\)")
FEATURE = re.compile(r"\b(?:(?:min|max)-)?(?:device-)?(width|height|inline-size|block-size)\b", re.I)
LENGTH = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?|\.\d+)(px|em|rem)\b", re.I)
THEME = re.compile(r"--(breakpoint|container)-([\w-]+)\s*:\s*(\d+(?:\.\d+)?|\.\d+)(px|em|rem)\b", re.I)
COMMENT = re.compile(r"/\*.*?\*/", re.S)
AXIS = {"width": "width", "inline-size": "width", "height": "height", "block-size": "height"}


def strip_comments(text: str) -> str:
    """Comments out, line count kept, so offsets still map to the right line."""
    return COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def thresholds(text: str, source: str) -> list[dict]:
    """Every length a media or container query compares a size feature against."""
    text = strip_comments(text)
    out = []
    for rule in RULE.finditer(text):
        kind = rule.group(1).lower()
        line = text.count("\n", 0, rule.start()) + 1
        for group in GROUP.finditer(rule.group(2)):
            feature = FEATURE.search(group.group(1))
            if not feature:
                continue
            axis = AXIS[feature.group(1).lower()]
            for value, unit in LENGTH.findall(group.group(1)):
                out.append({"kind": kind, "axis": axis, "value": float(value), "unit": unit.lower(),
                            "source": f"{source}:{line}"})
    for theme in THEME.finditer(text):
        line = text.count("\n", 0, theme.start()) + 1
        kind = "media" if theme.group(1).lower() == "breakpoint" else "container"
        out.append({"kind": kind, "axis": "width", "value": float(theme.group(3)),
                    "unit": theme.group(4).lower(), "source": f"{source}:{line} (theme --{theme.group(1)}-{theme.group(2)})"})
    return out


def to_px(t: dict, base: float, scale: float) -> float:
    return t["value"] if t["unit"] == "px" else t["value"] * base * scale


def neighbors(px: float) -> set[int]:
    """The integer sizes on both sides of a threshold: whichever operator the query uses (min-,
    max-, <, <=, >, >=), one of them matches and the other does not."""
    if abs(px - round(px)) < 1e-9:
        v = int(round(px))
        return {v - 1, v, v + 1}
    return {math.floor(px), math.ceil(px)}


def matrix(found: list[dict], base: float, scales: list[float], floor: int, ceil: int,
           extra_w: list[int], extra_h: list[int]) -> dict:
    out = {}
    for scale in scales:
        widths = {floor, ceil, *extra_w}
        heights = set(extra_h)
        for t in found:
            if t["kind"] != "media":
                continue
            sizes = neighbors(to_px(t, base, scale))
            (widths if t["axis"] == "width" else heights).update(sizes)
        out[format_scale(scale)] = {
            "widths": sorted(w for w in widths if floor <= w <= ceil),
            "heights": sorted(h for h in heights if h > 0),
            "belowFloor": sorted({w for w in widths if w < floor}),
            "aboveCeil": sorted({w for w in widths if w > ceil}),
        }
    return out


def containers(found: list[dict], base: float) -> dict:
    sizes = {"inline": set(), "block": set()}
    for t in found:
        if t["kind"] == "container":
            sizes["inline" if t["axis"] == "width" else "block"].update(neighbors(to_px(t, base, 1)))
    return {k: sorted(v) for k, v in sizes.items()}


def format_scale(scale: float) -> str:
    return f"{scale:g}"


def css_files(paths: list[str]) -> list[Path]:
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(f for f in p.rglob("*.css") if "node_modules" not in f.relative_to(p).parts))
        else:
            raise SystemExit(f"breakpoints.py: {raw}: no such file or directory")
    return files


def parse_list(raw: str, kind=float) -> list:
    return [kind(x) for x in raw.split(",") if x.strip()] if raw else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Derive the viewport test matrix from CSS media and container queries.")
    ap.add_argument("paths", nargs="+", help="CSS files or directories")
    ap.add_argument("--base", type=float, default=16.0, help="the default user font size in px (16)")
    ap.add_argument("--scales", default="1,1.25,1.5,2", help="user font scales to cover (1,1.25,1.5,2)")
    ap.add_argument("--floor", type=int, default=320, help="narrowest supported width (320, WCAG 1.4.10)")
    ap.add_argument("--ceil", type=int, default=1920, help="widest width to render (1920)")
    ap.add_argument("--extra-widths", default="", help="more widths to always include, comma separated")
    ap.add_argument("--extra-heights", default="", help="heights to always include, comma separated")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    files = css_files(args.paths)
    found = []
    for f in files:
        found.extend(thresholds(f.read_text(encoding="utf-8", errors="replace"), f.as_posix()))
    result = {
        "base": args.base,
        "floor": args.floor,
        "ceil": args.ceil,
        "files": len(files),
        "thresholds": found,
        "matrix": matrix(found, args.base, parse_list(args.scales), args.floor, args.ceil,
                         parse_list(args.extra_widths, int), parse_list(args.extra_heights, int)),
        "container": containers(found, args.base),
    }
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"{len(found)} thresholds in {len(files)} files (base {args.base:g}px)")
    distinct = sorted({(t['kind'], t['axis'], t['value'], t['unit']) for t in found})
    for kind, axis, value, unit in distinct:
        print(f"  {kind:<9} {axis:<6} {value:g}{unit}")
    for scale, m in result["matrix"].items():
        print(f"font scale {scale}: widths {' '.join(map(str, m['widths']))}")
        if m["heights"]:
            print(f"  heights {' '.join(map(str, m['heights']))}")
        if m["belowFloor"]:
            print(f"  below the {args.floor}px floor, not rendered: {' '.join(map(str, m['belowFloor']))}")
    c = result["container"]
    if c["inline"] or c["block"]:
        print(f"container inline sizes {' '.join(map(str, c['inline'])) or '-'}; block sizes {' '.join(map(str, c['block'])) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
