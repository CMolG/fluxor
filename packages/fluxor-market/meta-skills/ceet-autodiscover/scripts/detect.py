#!/usr/bin/env python3
"""Deterministic CEET detector for the ceet-autodiscover skill.

Finds the CEET role meta-skills installed next to this skill, matches the user's request against
each role's keywords, and reports which roles already have a pack in the project, so the host
model can decide how to proceed before it runs anything. Standard library only, plus ceet-core 2's
`ceet_common`, which must be installed beside this skill.

- A **role** is a sibling skill folder named `ceet-*` with `interview/form.json`. Its title and its
  routing keywords (`routing.keywords`) come from that form, so a new role is routed with no change
  here; its slots come from its `templates/cognitive-profile.md`.
- A **pack** is a folder under the packs directory carrying a marker of pack contract v2:
  `core.md` or `cognitive-profile.json` (a v1 `cognitive-profile.md` alone is still listed). Its
  role is the `role` of its `cognitive-profile.json`, else the `metaSkill` of its `pack.json`, else
  the `Role: **...**` line of its `cognitive-profile.md`.
- A role is **initialized** when the project holds a rendered pack for it: `core.md` exists and no
  slot of the role is left in `core.md` or `cognitive-profile.md`. Any other pack is reported as
  incomplete, with what is missing, never as initialized.
- **Examples** are packs shipped in any sibling skill's `examples/` folder. They are someone else's
  sample or simulated profile, never the user's own, and they are reported separately.

Usage (paths are relative to this skill's folder):
    python3 scripts/detect.py --request "review my backend migration"
    python3 scripts/detect.py --request "..." --project /path/to/project --skills-dir /other/skills

The project root is `--project`, else `$CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel`,
else the current directory. Packs live in `--packs-dir`, else `$HARNESS_DIR/packs`, else
`<project>/.harness/packs` (the default of the pack contract in ceet-core).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2.1.0"
CORE = Path(__file__).resolve().parents[2] / "ceet-core"
REQUIRED_CORE_MAJOR = "2"
ROLE_LINE = re.compile(r"Role:\s*\*\*(.+?)\*\*")


def load_core():
    """ceet-core's `ceet_common`, or SystemExit(2) when ceet-core 2 is not installed beside us."""
    manifest = CORE / "skill.json"
    version = json.loads(manifest.read_text(encoding="utf-8")).get("version", "") if manifest.is_file() else ""
    if version.split(".")[0] != REQUIRED_CORE_MAJOR:
        print(f"error: ceet-autodiscover requires ceet-core@{REQUIRED_CORE_MAJOR} next to it ({CORE}), "
              f"found {version or 'none'}", file=sys.stderr)
        raise SystemExit(2)
    spec = importlib.util.spec_from_file_location("ceet_common", CORE / "scripts" / "ceet_common.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cc = load_core()
Role = cc.Role
project_root = cc.project_root


def packs_directory(root: Path, explicit: str | None) -> Path:
    """`--packs-dir`, else `$HARNESS_DIR/packs`, else `<root>/.harness/packs`."""
    return Path(explicit).resolve() if explicit else cc.packs_dir(root)


def default_skills_dirs() -> list[Path]:
    """The folder this skill is installed in: its siblings are the other skills."""
    return [Path(__file__).resolve().parents[2]]


def keywords(role: Role) -> list[str]:
    """The role's routing keywords, lowercase, as its form declares them."""
    return [kw.lower() for kw in role.form.get("routing", {}).get("keywords", [])]


def find_roles(skills_dirs: list[Path]) -> list[Role]:
    """Every `ceet-*` role meta-skill in the given folders; the first folder wins on a duplicate."""
    roles: dict[str, Role] = {}
    for base in skills_dirs:
        if not base.is_dir():
            continue
        for folder in sorted(p for p in base.iterdir() if p.is_dir() and p.name.startswith("ceet-")):
            is_role = (folder / "interview" / "form.json").is_file()
            if is_role and folder.name not in roles:
                roles[folder.name] = Role(folder)
    return sorted(roles.values(), key=lambda role: role.id)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def declared(path: Path, key: str) -> str | None:
    """`key` of the JSON object at `path`, when it is a string."""
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def pack_role(pack: Path, roles: list[Role]) -> Role | None:
    """The role a pack belongs to: its profile JSON, else its manifest, else the Markdown role line."""
    by_id = {role.id: role for role in roles}
    for role_id in (declared(pack / "cognitive-profile.json", "role"),
                    (declared(pack / "pack.json", "metaSkill") or "").split("@")[0]):
        if role_id in by_id:
            return by_id[role_id]
    match = ROLE_LINE.search(read_text(pack / "cognitive-profile.md"))
    if match:
        title = match.group(1).strip().lower()
        return next((role for role in roles if role.title.lower() == title), None)
    return None


def describe_packs(folder: Path, roles: list[Role], root: Path) -> dict[str, list[dict[str, Any]]]:
    """Packs under `folder`, grouped by role id, with the role's slots left and the files missing."""
    found: dict[str, list[dict[str, Any]]] = {}
    if not folder.is_dir():
        return found
    markers = ("core.md", "cognitive-profile.json", "cognitive-profile.md")
    for pack in sorted(p for p in folder.iterdir() if p.is_dir() and any((p / m).is_file() for m in markers)):
        role = pack_role(pack, roles)
        if role is None:
            continue
        text = read_text(pack / "core.md") + read_text(pack / "cognitive-profile.md")
        found.setdefault(role.id, []).append({
            "path": display(pack, root),
            "unfilledSlots": len(role.slots & set(cc.SLOT.findall(text))),
            "missing": [] if (pack / "core.md").is_file() else ["core.md"],
        })
    return found


def complete(pack: dict[str, Any]) -> bool:
    return not pack["unfilledSlots"] and not pack["missing"]


def display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def tokenize(value: str) -> set[str]:
    """Lower-case `value`, split on non-alphanumeric, drop empties."""
    return {tok for tok in re.split(r"[^a-z0-9]+", value.lower()) if tok}


def mentions(request_lc: str, phrase: str) -> bool:
    """`phrase` appears in `request_lc` as whole words, plural allowed: `interview` matches
    `interviews`, `ui` does not match `quick`, and `design system` spans the space."""
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?:e?s)?(?![a-z0-9])", request_lc) is not None


def score_request(request: str, role: Role) -> tuple[int, list[str]]:
    """Score how well `request` matches a role, plus the matched signals.

    The form's `routing.keywords` and the tokens of the role id are the signals. A keyword weighs
    its number of words, so a specific phrase (`discovery call`) outweighs a word another role also
    uses (`discovery`); an id token that is also a keyword counts once.
    """
    request_lc = request.lower()
    role_keywords = keywords(role)
    score, matched = 0, []
    for kw in role_keywords:
        if mentions(request_lc, kw):
            score += len(kw.split())
            matched.append(f"kw:{kw}")
    for token in sorted(tokenize(role.id.removeprefix("ceet-")) - set(role_keywords)):
        if mentions(request_lc, token):
            score += 1
            matched.append(f"folder:{token}")
    return score, matched


def detect(request: str, root: Path, skills_dirs: list[Path], packs_dir: Path) -> dict[str, Any]:
    """Build the full detection report."""
    roles = find_roles(skills_dirs)
    packs = describe_packs(packs_dir, roles, root)
    examples: dict[str, list[dict[str, Any]]] = {}
    for base in skills_dirs:
        if base.is_dir():
            for skill in sorted(p for p in base.iterdir() if (p / "examples").is_dir()):
                for role_id, found in describe_packs(skill / "examples", roles, root).items():
                    examples.setdefault(role_id, []).extend(found)

    scoring: list[dict[str, Any]] = []
    for role in roles:
        score, matched = score_request(request, role) if request else (0, [])
        own = packs.get(role.id, [])
        scoring.append({
            "ceet": role.id,
            "title": role.title,
            "score": score,
            "matched": matched,
            "initialized": any(complete(p) for p in own),
            "packs": [p["path"] for p in own if complete(p)],
            "incompletePacks": [p for p in own if not complete(p)],
            "examples": [p["path"] for p in examples.get(role.id, []) if complete(p)],
        })
    scoring.sort(key=lambda entry: (-entry["score"], entry["ceet"]))

    best = scoring[0] if scoring and scoring[0]["score"] > 0 else None
    if best:
        reason = f"matched signals {best['matched']}"
    elif not roles:
        reason = "no CEET role meta-skills found next to this skill; pass --skills-dir"
    elif not request:
        reason = "no request supplied; only enumeration produced"
    else:
        reason = "no CEET keywords matched the request"

    return {
        "schemaVersion": SCHEMA_VERSION,
        "project": root.as_posix(),
        "packsDir": display(packs_dir, root),
        "skillsDirs": [p.as_posix() for p in skills_dirs],
        "detectedCEETs": sorted(entry["ceet"] for entry in scoring if entry["score"] > 0),
        "initializedCEETs": sorted(entry["ceet"] for entry in scoring if entry["initialized"]),
        "scoring": scoring,
        "recommendation": {
            "primary": best["ceet"] if best else None,
            "reason": reason,
            "needsInitialization": bool(best) and not best["initialized"],
            "packs": best["packs"] if best else [],
            "examples": best["examples"] if best else [],
        },
    }


def main(argv: list[str] | None = None) -> int:
    cc.configure_output()
    parser = argparse.ArgumentParser(description="Deterministic CEET detector for ceet-autodiscover.")
    parser.add_argument("--request", default="", help="User request to match against role keywords.")
    parser.add_argument("--project", default=None, help="Project root (default: $CLAUDE_PROJECT_DIR, git, cwd).")
    parser.add_argument("--skills-dir", action="append", default=None,
                        help="Folder holding the ceet-* skills; repeatable (default: the folder this skill is in).")
    parser.add_argument("--packs-dir", default=None,
                        help="Folder holding generated packs (default: $HARNESS_DIR/packs or <project>/.harness/packs).")
    parser.add_argument("--output", default=None, help="Write JSON to this file instead of stdout.")
    args = parser.parse_args(argv)

    root = project_root(args.project)
    skills_dirs = [Path(p).resolve() for p in args.skills_dir] if args.skills_dir else default_skills_dirs()
    report = detect(args.request, root, skills_dirs, packs_directory(root, args.packs_dir))
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
