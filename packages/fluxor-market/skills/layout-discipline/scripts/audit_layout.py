#!/usr/bin/env python3
"""
audit_layout.py — static audit for the layout anti-patterns that make UI collapse, overflow,
refuse to scroll, or drift into duplicated components.

Usage:
    python audit_layout.py <file-or-dir> [more...] [--json] [--strict]

Scans .tsx .jsx .ts .js .html .mdx .astro .vue .svelte and .css files. Prints one line per
finding as  path:line: LEVEL code  message  and a summary. Exit code is 1 when any ERROR is
found (or any WARN with --strict), 0 otherwise.

Levels:
    ERROR  will break in production or cannot work (dynamic class names, template-string merge)
    WARN   almost always a bug in a layout (missing min-size reset, vh units, fixed sizes, 1fr tracks)
    INFO   needs a human/agent look (truncate, overflow-hidden, sticky, space-*, @apply, many booleans)

The checks are regex heuristics on a per-line basis. Class lists that span several lines can
produce false positives for the "flexible item without min-size reset" check — treat those as
review prompts, not verdicts. To record a justified exception, put a comment containing
`layout-ok: <reason>` on the same line (e.g. `{/* layout-ok: page grows in document mode */}`);
the line is then skipped.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

EXTENSIONS = {".tsx", ".jsx", ".ts", ".js", ".html", ".mdx", ".astro", ".vue", ".svelte", ".css"}
SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "coverage", "out", ".turbo"}

SPACING = r"(?:-?m[trblxyse]?|p[trblxyse]?|gap(?:-[xy])?|space-[xy]|inset(?:-[xy])?|top|right|bottom|left)"
CLASS_PREFIX = r"(?:bg|text|border|ring|outline|fill|stroke|from|to|via|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|w|h|size|gap|grid-cols|grid-rows|col-span|row-span|rounded|shadow|opacity|z|order|basis|max-w|min-w|max-h|min-h)"


@dataclass
class Finding:
    path: str
    line: int
    level: str
    code: str
    message: str


CHECKS: list[tuple[str, str, re.Pattern[str], str]] = [
    # code, level, pattern, message
    (
        "dynamic-class",
        "ERROR",
        re.compile(rf"\b{CLASS_PREFIX}-\$\{{|\b{CLASS_PREFIX}-\{{\{{|\b{CLASS_PREFIX}-'\s*\+"),
        "class name built at runtime — the scanner only sees complete literal strings; map props to full class strings",
    ),
    (
        "template-merge",
        "ERROR",
        re.compile(r"className\s*=\s*\{\s*`[^`]*\$\{\s*className\s*\}"),
        "className merged with a template string — use cn(base, VARIANT[variant], className) so conflicting utilities resolve",
    ),
    (
        "vh-unit",
        "WARN",
        re.compile(r"\b(?:min-|max-)?h-screen\b|\[[^\]]*\d+vh[^\]]*\]"),
        "viewport height in vh — mobile toolbars make it taller than the visible area; use dvh (h-dvh, min-h-dvh, calc(100dvh-…))",
    ),
    (
        "w-screen",
        "WARN",
        re.compile(r"\bw-screen\b|\[[^\]]*100vw[^\]]*\]"),
        "w-screen/100vw includes the scrollbar width and causes horizontal overflow; use w-full",
    ),
    # A percentage is a fraction of the containing block (`top-[40%]` on an arrow over a cover),
    # not a length the scale could hold, so it is not off-scale.
    (
        "off-scale-spacing",
        "WARN",
        re.compile(rf"(?<![\w-])(?:[a-z@\[\]:-]+:)?{SPACING}-\[(?!calc|var|min|max|clamp|env|--|-?[\d.]+%\])[^\]]+\]"),
        "off-scale spacing value — use the scale (or add the token to the theme once)",
    ),
    (
        "fixed-px-size",
        "WARN",
        re.compile(r"(?<![\w-])(?:[a-z@\[\]:-]+:)?(?:w|h|size|basis)-\[\d+(?:px|rem)\]"),
        "fixed pixel size on an element — allowed only for icons/avatars/rails; content boxes use w-full max-w-* / min-h-*",
    ),
    (
        "important-flag",
        "INFO",
        re.compile(r"(?<=[\s\"'`])![a-z][\w-]*|\b[a-z][\w:-]*!(?=[\s\"'`])"),
        "important flag — fix the merge order or add a variant instead of forcing specificity",
    ),
    (
        "truncate-needs-width",
        "INFO",
        re.compile(r"\b(?:truncate|text-ellipsis|whitespace-nowrap|text-nowrap|line-clamp-\d+)\b"),
        "truncation/nowrap needs a constrained width — the nearest flex/grid item must have min-w-0 (or an explicit width)",
    ),
    (
        "overflow-hidden",
        "INFO",
        re.compile(r"\boverflow-(?:hidden|clip)\b"),
        "clipping — confirm content can never exceed this box; otherwise use overflow-auto, wrapping, or remove the fixed size",
    ),
    (
        "h-full-chain",
        "INFO",
        re.compile(r"(?<![\w-])h-full\b"),
        "h-full needs a definite-height parent — inside flex columns use flex-1 min-h-0 instead",
    ),
    (
        "space-utility",
        "INFO",
        re.compile(r"\bspace-[xy]-"),
        "space-* is margin-based and breaks with wrapping/hidden children — prefer gap on the parent",
    ),
    (
        "sticky",
        "INFO",
        re.compile(r"\bsticky\b"),
        "sticky sticks to the nearest scrolling ancestor — check no in-between ancestor sets overflow, and that the parent is taller than the sticky element",
    ),
]

APPLY_RE = re.compile(r"@apply\b")
FLEX_ITEM_RE = re.compile(r"(?<![\w-])(?:flex-1|flex-auto|grow|grow-\[?\d|basis-(?!auto)[\w\[\]/%.-]+)(?![\w-])")
MIN_RESET_RE = re.compile(r"(?<![\w-])(?:min-w-0|min-h-0|w-0|shrink-0|truncate|overflow-(?:hidden|auto|scroll|clip)|overflow-[xy]-(?:hidden|auto|scroll|clip))(?![\w-])|(?<![\w-])min-[wh]-\[")
SUPPRESS_RE = re.compile(r"layout-ok")
CLASSNAME_LINE_RE = re.compile(r"className|class=|class:|:class")
BOOLEAN_PROP_RE = re.compile(r"\b(?!disabled|loading|selected|open|checked|required|readOnly|invalid|pressed|active|expanded|visible|hidden|busy)[a-zA-Z_]\w*\??\s*:\s*boolean\b")
COMPONENT_FILE_RE = re.compile(r"\.(?:tsx|jsx)$")
TRACK_RE = re.compile(r"grid-(?:cols|rows)-\[([^\]]*)\]")
FR_RE = re.compile(r"(?<![A-Za-z0-9.])\d*\.?\d*fr(?![A-Za-z0-9])")
ROOT_MARGIN_RE = re.compile(r"return\s*\(\s*<[a-zA-Z][\w.]*\s[^>]*?className=(?:\{\s*cn\(\s*)?[\"'`]([^\"'`]*)[\"'`]")
# Only a positive margin spaces a component from its siblings. `mx-auto`/`mt-auto` align the box
# itself, `m-0` resets, and a negative margin is a bleed or the gutter of a wrapping row (the
# portable way to space wrapped items on targets without `gap`): none of them is spacing a
# parent's gap could take over. On a real codebase they were over half of this check's findings.
MARGIN_CLASS_RE = re.compile(r"(?<![\w-])m[tbxyse]?-(?:0?\.\d|[1-9]|px|\[)")
FORK_NAME_RE = re.compile(r"export\s+(?:default\s+)?(?:function|const)\s+([A-Z]\w*(?:V\d+|Copy|Alt|Custom|Duplicate|Clone|\d)\b)")
WIDTH_HINT_RE = re.compile(r"(?<![\w-])(?:min-w-0|max-w-[\w\[]|w-\d|w-\[|w-full|basis-)")


def _is_minmax_max_arg(before: str) -> bool:
    """True when the text before an fr token places it as the max argument of an open minmax(...)."""
    i = before.rfind("minmax(")
    if i < 0:
        return False
    tail = before[i + len("minmax("):]
    depth = 0
    for ch in tail:
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return False  # that minmax closed before the fr token
            depth -= 1
    return depth == 0 and tail.rstrip().endswith(",")


def bare_fr_tracks(line: str) -> bool:
    """True when a custom grid template uses a bare fr track (i.e. minmax(auto, Nfr))."""
    for m in TRACK_RE.finditer(line):
        content = m.group(1)
        for fr in FR_RE.finditer(content):
            if not _is_minmax_max_arg(content[:fr.start()]):
                return True
    return False


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    rel = str(path)
    lines = text.splitlines()
    is_css = path.suffix == ".css"

    for idx, line in enumerate(lines, start=1):
        if is_css:
            if APPLY_RE.search(line):
                findings.append(Finding(rel, idx, "INFO", "apply-directive", "@apply extracts utilities into CSS — prefer a component with variant maps; keep @apply for third-party markup only"))
            continue

        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        if SUPPRESS_RE.search(line):
            continue  # justified exception: a `layout-ok: <reason>` comment on the same line

        for code, level, pattern, message in CHECKS:
            if pattern.search(line):
                if code == "truncate-needs-width" and WIDTH_HINT_RE.search(line):
                    continue  # the element itself is constrained; still verify the ancestor chain
                findings.append(Finding(rel, idx, level, code, message))

        if bare_fr_tracks(line):
            findings.append(Finding(rel, idx, "WARN", "bare-fr-track", "fr track not wrapped in minmax(0,…) = minmax(auto,…): the column refuses to shrink below its content; use minmax(0,1fr)"))

        # flexible item without a min-size reset on the same class list (same line heuristic)
        if CLASSNAME_LINE_RE.search(line) and FLEX_ITEM_RE.search(line) and not MIN_RESET_RE.search(line):
            findings.append(Finding(rel, idx, "WARN", "flex-item-no-min-reset", "flexible item without min-w-0 / min-h-0 — text or media inside will refuse to shrink and overflow (ignore if the item only holds fixed-size content)"))

    # file-level checks (multi-line aware)
    if COMPONENT_FILE_RE.search(path.name):
        booleans = BOOLEAN_PROP_RE.findall(text)
        if len(booleans) >= 3:
            findings.append(Finding(rel, 1, "INFO", "boolean-props", f"{len(booleans)} non-state boolean props in this file — looks like variants/slots disguised as flags; consider a variant map or composition"))

        for m in ROOT_MARGIN_RE.finditer(text):
            if MARGIN_CLASS_RE.search(m.group(1)):
                line_no = text.count("\n", 0, m.start()) + 1
                findings.append(Finding(rel, line_no, "WARN", "outer-margin", "component root carries an outer margin — components position nothing; move sibling spacing to the parent's gap"))

        for m in FORK_NAME_RE.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            findings.append(Finding(rel, line_no, "INFO", "fork-name", f"'{m.group(1)}' looks like a fork of an existing component — reuse, evolve within limits, or compose instead"))

    return findings


def iter_files(targets: list[str]):
    for t in targets:
        p = Path(t)
        if p.is_file():
            if p.suffix in EXTENSIONS:
                yield p
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in EXTENSIONS and not any(part in SKIP_DIRS for part in f.parts):
                    yield f


def utf8_console() -> None:
    """Print non-ASCII (—, …, → and paths from the scanned tree) on a legacy Windows code page without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str]) -> int:
    utf8_console()
    parser = argparse.ArgumentParser(prog="audit_layout.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", metavar="file-or-dir", help="files or directories to scan")
    parser.add_argument("--json", action="store_true", help="print the findings as a JSON array")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any WARN as well as on ERROR")
    args, _unknown = parser.parse_known_args(argv)  # unknown options are ignored, as they always were
    as_json, strict, targets = args.json, args.strict, args.targets
    if not targets:
        print(__doc__)
        return 2

    findings: list[Finding] = []
    for f in iter_files(targets):
        findings.extend(scan_file(f))

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda x: (order[x.level], x.path, x.line))

    if as_json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.level} {f.code}  {f.message}")
        counts = {lvl: sum(1 for f in findings if f.level == lvl) for lvl in order}
        print()
        print(f"Summary: {counts['ERROR']} error(s), {counts['WARN']} warning(s), {counts['INFO']} info")
        if not findings:
            print("No layout anti-patterns detected. Now run the stress-test matrix — the audit cannot see spacing hierarchy or missing wrap strategies.")

    has_error = any(f.level == "ERROR" for f in findings)
    has_warn = any(f.level == "WARN" for f in findings)
    return 1 if has_error or (strict and has_warn) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
