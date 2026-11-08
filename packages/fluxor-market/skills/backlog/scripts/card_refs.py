#!/usr/bin/env python3
"""Card references in the code: list them, count them per card, and check them against closed cards.

  card_refs.py list [KEY ...]            every reference (file:line, kind, text), optionally for some cards
  card_refs.py keys                      the cards referenced, with temporary / rationale counts
  card_refs.py check --closed KEY[,KEY]  exit 1 if a closed card still has temporary references,
                                         or if a reference is malformed
  card_refs.py touching PATH... [--days N]  JSON: per path, the cards whose recent commits changed it

A reference is `<scheme>://<KEY>` in a comment, Apple Radar style (`rdar://12345678`):

  // card://<KEY>: why this code exists, readable without opening the card
  // card://<KEY> [temporary]: what to remove, and when

The scheme, the key prefixes and the paths to skip come from `.harness/config/backlog.json`
(`codeReferences.scheme`, default `card`; `keyPrefix` and `legacyKeyPrefixes`;
`codeReferences.ignore`, globs of tracked paths). Which cards are closed is the tracker's
answer, not this script's: ask the MCP server, then pass the keys to `check`.

In Markdown, a reference inside inline code or a fenced block is an example, not a reference, and
`card://KEY` or `card://<KEY>` (no digit) is a placeholder: documenting the format reports
nothing, neither as a reference nor as a malformed one.

Reads only files tracked by git (falls back to walking the tree), writes nothing.
Exit codes: 0 ok, 1 findings (`check`), 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".gradle", ".groovy", ".h", ".hpp", ".html", ".java",
    ".js", ".jsx", ".kt", ".kts", ".m", ".md", ".mdx", ".mjs", ".cjs", ".mm", ".php", ".properties",
    ".py", ".rb", ".rs", ".scss", ".sh", ".sql", ".swift", ".toml", ".ts", ".tsx", ".vue", ".xml",
    ".yaml", ".yml", ".json",
}
SKIP_DIRS = {".git", "node_modules", "dist", "build", "target", ".next", "__pycache__", ".venv", "venv"}
TEMPORARY = "[temporary]"


def utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def load_config(root: Path) -> dict:
    harness = Path(os.environ.get("HARNESS_DIR", ".harness"))
    if not harness.is_absolute():
        harness = root / harness
    path = harness / "config" / "backlog.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def key_pattern(config: dict) -> str:
    prefixes = [p for p in [config.get("keyPrefix"), *config.get("legacyKeyPrefixes", [])] if p]
    return "(?:" + "|".join(re.escape(p) for p in prefixes) + r")-\d+" if prefixes else r"[A-Z][A-Z0-9]*-\d+"


def patterns(config: dict) -> tuple[str, re.Pattern, re.Pattern]:
    scheme = config.get("codeReferences", {}).get("scheme", "card")
    key = key_pattern(config)
    reference = re.compile(rf"\b{re.escape(scheme)}://({key})\b(\s*\[temporary\])?")
    # Anything that looks like a reference with this scheme and a number, to catch keys with the
    # wrong shape. Without a digit it is a placeholder in documentation (card://KEY, card://<KEY>).
    loose = re.compile(rf"\b{re.escape(scheme)}://(\S*\d\S*)")
    return scheme, reference, loose


def glob_regex(pattern: str) -> re.Pattern:
    """`**/` spans any number of folders, `**` anything, `*` stays within one folder."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(f"^{out}$")


def git_files(root: Path, needles: list[str]) -> list[str] | None:
    """The tracked files that contain one of `needles`, or None when git cannot answer. `git grep`
    does the reading: a tree on a network share (WSL's from Windows) costs seconds this way and a
    minute file by file. git refuses a repository whose owner it cannot verify, which is every
    repository on such a share, so the root the caller asked to read is named safe for this one
    command."""
    git = ["git", "-c", f"safe.directory={root.as_posix()}"]
    patterns = [arg for needle in needles for arg in ("-e", needle)]
    try:
        out = subprocess.run([*git, "grep", "-l", "-z", "-I", "-F", *patterns], cwd=root, capture_output=True)
    except OSError:
        return None
    if out.returncode not in (0, 1):   # 1: no file matches
        return None
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


def candidate_files(root: Path, ignore: list[str], needles: list[str]) -> list[Path]:
    rels = git_files(root, needles)
    if rels is not None:
        files = [root / p for p in rels]
    else:
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            files += [Path(dirpath) / f for f in filenames]
    skip = [glob_regex(g) for g in ignore]
    return sorted(f for f in files if f.suffix in TEXT_SUFFIXES and f.is_file()
                  and not any(s.match(f.relative_to(root).as_posix()) for s in skip))


MARKDOWN_SUFFIXES = {".md", ".mdx"}
CODE_SPAN = re.compile(r"(`+).*?\1")
FENCE = ("```", "~~~")


def scan(root: Path, config: dict, keys=()) -> tuple[list[dict], list[dict]]:
    """Every reference, or only those that could be to `keys` (malformed ones are then incomplete)."""
    scheme, reference, loose = patterns(config)
    refs, malformed = [], []
    # Every reference and every malformed one carries `<scheme>://`: no other file needs reading.
    needles = [f"{scheme}://{key}" for key in keys] or [f"{scheme}://"]
    for path in candidate_files(root, config.get("codeReferences", {}).get("ignore", []), needles):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        markdown = path.suffix in MARKDOWN_SUFFIXES
        fenced = False
        for number, line in enumerate(lines, 1):
            if markdown and line.lstrip().startswith(FENCE):
                fenced = not fenced
                continue
            if fenced:
                continue
            # Markdown code is where the format gets documented: an example, not a reference.
            spans = [m.span() for m in CODE_SPAN.finditer(line)] if markdown else []

            def in_code(start: int) -> bool:
                return any(a <= start < b for a, b in spans)

            found = {m.start() for m in reference.finditer(line)}
            for m in reference.finditer(line):
                if in_code(m.start()):
                    continue
                refs.append({
                    "file": rel,
                    "line": number,
                    "key": m.group(1),
                    "kind": "temporary" if m.group(2) else "rationale",
                    "text": line.strip()[:200],
                })
            for m in loose.finditer(line):
                if m.start() not in found and not in_code(m.start()):
                    malformed.append({"file": rel, "line": number, "text": line.strip()[:200],
                                      "problem": f"{scheme}://{m.group(1)} is not a key of this project"})
    return refs, malformed


def touching(root: Path, config: dict, paths: list[str], days: int) -> list[dict] | None:
    """For each path, the cards named in the commits that changed it in the last `days`, most recent
    first and at most 30. A key in a commit message is read in any case and answered upper case.
    None when git cannot read one of the paths."""
    key = re.compile(rf"\b({key_pattern(config)})\b", re.IGNORECASE)
    git = ["git", "-c", f"safe.directory={root.as_posix()}"]
    answer = []
    for path in paths:
        out = subprocess.run([*git, "log", f"--since={days} days ago", "--format=%B%x1e", "--", path],
                             cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode != 0:
            return None
        cards: list[str] = []
        for message in out.stdout.split("\x1e"):
            for m in key.finditer(message):
                card = m.group(1).upper()
                if card not in cards:
                    cards.append(card)
        answer.append({"path": path, "cards": cards[:30]})
    return answer


def print_refs(refs: list[dict], url_template: str | None) -> None:
    for r in refs:
        url = f"  <{url_template.format(key=r['key'])}>" if url_template else ""
        print(f"{r['file']}:{r['line']}: {r['key']} ({r['kind']}){url}\n    {r['text']}")


def main(argv=None) -> int:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    parser.add_argument("--json", action="store_true", help="machine-readable output on stdout")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list", help="every reference, optionally only for some cards")
    p.add_argument("keys", nargs="*")
    sub.add_parser("keys", help="the cards referenced, with counts")
    p = sub.add_parser("check", help="temporary references to closed cards, and malformed references")
    p.add_argument("--closed", default="", help="comma-separated keys of cards the tracker reports as done")
    p = sub.add_parser("touching", help="the cards whose recent commits changed these paths, as JSON")
    p.add_argument("paths", nargs="+")
    p.add_argument("--days", type=int, default=90, help="how far back the commits are read (default 90)")
    args = parser.parse_args(argv)

    root = project_root()
    config = load_config(root)
    if args.command == "touching":
        if args.days < 1:
            parser.error("--days must be at least 1")
        answer = touching(root, config, args.paths, args.days)
        if answer is None:
            print("error: git cannot read one of the paths", file=sys.stderr)
            return 2
        print(json.dumps(answer, indent=2))
        return 0
    url_template = config.get("codeReferences", {}).get("urlTemplate")
    refs, malformed = scan(root, config, args.keys if args.command == "list" else ())

    if args.command == "list":
        wanted = set(args.keys)
        chosen = [r for r in refs if not wanted or r["key"] in wanted]
        if args.json:
            print(json.dumps({"references": chosen}, indent=2))
        else:
            print_refs(chosen, url_template)
            print(f"{len(chosen)} reference(s)")
        return 0

    if args.command == "keys":
        counts: dict[str, dict[str, int]] = {}
        for r in refs:
            counts.setdefault(r["key"], {"temporary": 0, "rationale": 0})[r["kind"]] += 1
        if args.json:
            print(json.dumps({"keys": counts}, indent=2, sort_keys=True))
        else:
            for key in sorted(counts, key=lambda k: (k.split("-")[0], int(k.rsplit("-", 1)[1]))):
                c = counts[key]
                print(f"{key:14} temporary: {c['temporary']:3}  rationale: {c['rationale']:3}")
        return 0

    closed = {k.strip() for k in args.closed.split(",") if k.strip()}
    stale = [r for r in refs if r["key"] in closed and r["kind"] == "temporary"]
    if args.json:
        print(json.dumps({"stale": stale, "malformed": malformed}, indent=2))
    else:
        for r in stale:
            print(f"{r['file']}:{r['line']}: {r['key']} is closed but this is still marked temporary\n    {r['text']}")
        for m in malformed:
            print(f"{m['file']}:{m['line']}: {m['problem']}\n    {m['text']}")
        print(f"{len(stale)} stale temporary reference(s), {len(malformed)} malformed")
    return 1 if stale or malformed else 0


if __name__ == "__main__":
    sys.exit(main())
