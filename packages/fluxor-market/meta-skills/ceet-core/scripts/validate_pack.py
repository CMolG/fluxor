#!/usr/bin/env python3
"""Validate a CEET pack against its role: the checks a pack must pass before anyone loads it.

  validate_pack.py .harness/packs/backend-engineer-alex
  validate_pack.py <pack> --role-dir path/to/ceet-backend-engineer --json

For every pack:
- `cognitive-profile.json` is valid (schemas/cognitive-profile.schema.json) and names its role;
- a consent record exists, excludes the uses no pack may serve, and fits the source (a simulated
  pack of a private individual needs that person's consent);
- every slot the role declares has a value or an explicit "not synthesized";
- every directive cites its evidence (`[Q<n>]`, `[E<n>]` or `[teachback]`), every `[Q<n>]` is a
  question of the role's form, and every cited question has an answer in `private/answers.json`;
- no slot survives in a rendered file, no hidden character reaches one, no special-category detail
  sits in a shared file unless the person cleared it, `private/` is git-ignored, and a pack kept
  local is git-ignored as a whole;
- the shared files match the hashes in `pack.json` (an edit is reported as drift), and every entry of
  `profile-changelog.md` has its heading and lists what moved.

For a simulated pack (`source: simulation`), also: every file carries the Simulation Notice, and
`evidence-map.md` has a row for **every** directive the role declares, each with a source (a URL, a
commit as the whole cell or `commit: <hash>`, or `doc: <document>`) or an explicit `unknown`; a
populated directive or identity slot cites its own rows, none of them `unknown`; `identity.core_values`
and `identity.frustration_triggers` are never populated; a "not synthesized" note is one of the fixed
reasons, never free text; and nothing private (no reflection on the person) exists. In any evidence
map, a ref names one row.

Exit 0 when valid, 1 with findings, 2 on usage errors. Standard library only (Python 3.9+).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ceet_common as cc  # noqa: E402

# A commit is the whole cell or prefixed like a document: a hex-only word in prose ("defaced") is not one.
SOURCE = re.compile(r"(https?://\S+|^[0-9a-f]{7,40}$|\bcommit:\s*[0-9a-f]{7,40}\b|\bdoc:\s*\S.*)", re.I)
CONFIDENCE = {"high", "medium", "low", "unknown"}
# What `render_pack.py reprofile` writes: one entry per re-profile, newest first, each under this heading.
CHANGELOG = "profile-changelog.md"
CHANGELOG_ENTRY = re.compile(r"^## [0-9]{4}-[0-9]{2}-[0-9]{2} · profile [0-9]+\.[0-9]+\.[0-9]+ → [0-9]+\.[0-9]+\.[0-9]+$")


def changelog_findings(text: str) -> list[str]:
    """A malformed entry: a heading that is not the entry heading, or an entry that lists nothing."""
    errors: list[str] = []
    for entry in re.split(r"(?m)^(?=## )", text)[1:]:
        heading, _, body = entry.partition("\n")
        if not CHANGELOG_ENTRY.match(heading):
            errors.append(f"{CHANGELOG}: {heading!r} is not an entry heading (## <date> · profile <old> → <new>)")
        if not any(line.startswith("- ") for line in body.splitlines()):
            errors.append(f"{CHANGELOG}: the entry {heading!r} lists nothing that moved")
    return errors


def evidence_rows(text: str) -> dict[str, dict]:
    """`| E<n> | directives.x.y | confidence | source | evidence |` rows, by reference. A ref used by
    more than one row keeps its first row, marked `duplicated`, so the finding names it."""
    rows: dict[str, dict] = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not re.fullmatch(r"E[1-9][0-9]*", cells[0]):
            continue
        if cells[0] in rows:
            rows[cells[0]]["duplicated"] = True
            continue
        rows[cells[0]] = {"directive": cells[1].strip("`"), "confidence": cells[2].lower(),
                          "source": cells[3], "evidence": cells[4]}
    return rows


def slot_values(profile: dict, role: cc.Role) -> dict[str, object]:
    values: dict[str, object] = {}
    for slot in role.content_slots():
        values[slot] = cc.lookup(profile, slot)
    if values.get("identity.contradictions") is None and profile.get("contradictions"):
        values["identity.contradictions"] = "(rendered from contradictions)"
    return values


def profile_findings(profile: dict, role: cc.Role, answers: dict | None, evidence: dict | None) -> tuple[list[str], list[str]]:
    """Errors and warnings about the profile's content, independent of rendered files."""
    errors: list[str] = []
    warnings: list[str] = []
    source = profile.get("source")
    consent = profile.get("consent", {})
    missing_exclusions = sorted(set(cc.EXCLUDED_USES) - set(consent.get("excludedUses", [])))
    if missing_exclusions:
        errors.append("consent.excludedUses must list " + ", ".join(missing_exclusions))
    if source == "interview" and consent.get("basis") != "consent":
        errors.append("an interview pack needs consent.basis 'consent'")
    if profile.get("formVersion") != role.form.get("formVersion"):
        same_major = str(profile.get("formVersion", "")).split(".")[0] == str(role.form.get("formVersion")).split(".")[0]
        (warnings if same_major else errors).append(
            f"answers were given to form {profile.get('formVersion')}, the role's form is {role.form.get('formVersion')}"
            + ("" if same_major else ": question ids may have changed meaning; re-profile"))

    question_ids = role.question_ids()
    answered = {q for q, entry in (answers or {}).get("answers", {}).items() if entry.get("text", "").strip()}
    cleared = set(profile.get("review", {}).get("specialCategoryCleared", []))
    values = slot_values(profile, role)
    for slot, value in values.items():
        if value is None:
            errors.append(f"{{{slot}}} has no value: synthesize it or mark it not synthesized (rule 11)")
            continue
        if source == "simulation" and cc.is_not_synthesized(value) and value.get("_note") not in cc.SIMULATION_NOTES:
            errors.append(f"{{{slot}}} is not synthesized with a note of its own: a simulated pack's note is one of "
                          + ", ".join(repr(n) for n in cc.SIMULATION_NOTES) + ", never a claim")
        if source == "simulation" and slot in cc.NEVER_SIMULATED and not cc.is_not_synthesized(value):
            errors.append(f"{{{slot}}} is never simulated: a value or a frustration is a trait; "
                          f"mark it not synthesized ({cc.TRAIT_NOTE!r})")
            continue
        if cc.is_not_synthesized(value) or not isinstance(value, str):
            continue
        cited = cc.refs(value)
        if slot.startswith("directives.") and not cited:
            errors.append(f"{{{slot}}} cites no evidence: add [Q<n>] references (rule 6)")
        elif not cited and slot != "identity.contradictions" and source != "simulation":
            warnings.append(f"{{{slot}}} cites no question")
        for ref in cited:
            if ref.startswith("Q"):
                if source == "simulation":
                    errors.append(f"{{{slot}}} cites {ref}, but a simulated pack cites evidence rows [E<n>]")
                elif ref not in question_ids:
                    errors.append(f"{{{slot}}} cites {ref}, which form {role.form.get('formVersion')} does not have")
                elif answers is not None and ref not in answered:
                    errors.append(f"{{{slot}}} cites {ref}, which has no answer in private/answers.json")
            elif ref.startswith("E"):
                if evidence is None:
                    errors.append(f"{{{slot}}} cites {ref}, but the pack has no evidence-map.md")
                elif ref not in evidence:
                    errors.append(f"{{{slot}}} cites {ref}, which evidence-map.md does not have")
                elif evidence[ref]["directive"] != slot:
                    errors.append(f"{{{slot}}} cites {ref}, a row evidence-map.md gives to {evidence[ref]['directive']}: "
                                  "a slot cites its own rows")
                elif evidence[ref]["confidence"] == "unknown":
                    errors.append(f"{{{slot}}} cites {ref}, whose confidence is unknown: mark the slot not synthesized")
        if source == "simulation" and not any(r[0] in "EQ" for r in cited):
            errors.append(f"{{{slot}}} cites none of its own sourced rows: a simulated slot cites [E<n>] "
                          "or is not synthesized")
        hits = cc.special_category_hits(value)
        if hits and slot not in cleared:
            errors.append(f"{{{slot}}} mentions {', '.join(hits)}: special-category details stay out of a pack "
                          "unless the person cleared them (review.specialCategoryCleared)")
    if answers is None and source == "interview":
        warnings.append("private/answers.json is not here (a shared copy?): cited questions were not checked for answers")
    for item in profile.get("contradictions", []):
        for key in ("question_a", "question_b"):
            ref = item.get(key, "")
            if ref.startswith("Q") and ref not in question_ids:
                errors.append(f"a contradiction cites {ref}, which the form does not have")

    for ref, row in (evidence or {}).items():
        if row.get("duplicated"):
            errors.append(f"evidence-map.md {ref}: more than one row uses this ref; give each row its own E<n>")
    if source == "simulation":
        evidence = evidence or {}
        by_directive: dict[str, list[dict]] = {}
        for ref, row in evidence.items():
            by_directive.setdefault(row["directive"], []).append(row)
            if row["directive"] in cc.NEVER_SIMULATED:
                errors.append(f"evidence-map.md {ref}: {row['directive']} is never simulated, so it has no evidence")
            if row["confidence"] not in CONFIDENCE:
                errors.append(f"evidence-map.md {ref}: confidence {row['confidence']!r} is not high, medium, low or unknown")
            elif row["confidence"] != "unknown" and not SOURCE.search(row["source"]):
                errors.append(f"evidence-map.md {ref}: no source (a URL, a commit, or `doc: <document>`; "
                              "a commit is the whole cell or `commit: <hash>`)")
            if row["directive"] not in role.slots:
                errors.append(f"evidence-map.md {ref}: {row['directive']} is not a slot of {role.id}")
        uncovered = [d for d in role.directive_slots() if d not in by_directive]
        if uncovered:
            errors.append(f"evidence-map.md has no row for {len(uncovered)} of {len(role.directive_slots())} "
                          f"directives (each needs a sourced row or an explicit unknown): "
                          + ", ".join(uncovered[:5]) + ("…" if len(uncovered) > 5 else ""))
    return errors, warnings


def shared_files(pack: Path) -> list[Path]:
    return sorted(p for p in pack.rglob("*") if p.is_file() and "private" not in p.relative_to(pack).parts
                  and p.name != ".gitignore")


def file_findings(pack: Path, profile: dict, role: cc.Role) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    simulation = profile.get("source") == "simulation"
    cleared = set(profile.get("review", {}).get("specialCategoryCleared", []))
    for path in shared_files(pack):
        rel = path.relative_to(pack).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if path.suffix == ".md":
            left = sorted(set(cc.SLOT.findall(text)) & role.slots)
            if left:
                errors.append(f"{rel}: slot(s) left unrendered: {', '.join(left[:5])}")
            if simulation and "Simulation Notice" not in text:
                errors.append(f"{rel}: missing the Simulation Notice")
            if "composite_scores" in text:
                errors.append(f"{rel}: composite scores have no method and never ship (plan item 0.2)")
        if any(ch in cc.INVISIBLE for ch in text):
            errors.append(f"{rel}: contains invisible or bidirectional characters")
        if not cleared and path.suffix == ".md" and not rel.startswith("adapters/"):
            hits = cc.special_category_hits(text)
            if hits and rel not in ("README.md",):
                warnings.append(f"{rel}: mentions {', '.join(hits)}; check it is not about the person")
    private_ignore = pack / "private" / ".gitignore"
    if (pack / "private").is_dir() and (not private_ignore.is_file() or "*" not in private_ignore.read_text(encoding="utf-8")):
        errors.append("private/ must hold a .gitignore that ignores everything (*)")
    if profile.get("consent", {}).get("storage") == "local":
        ignore = pack / ".gitignore"
        if not ignore.is_file() or "*" not in ignore.read_text(encoding="utf-8").split():
            errors.append("consent.storage is local, so the pack needs a .gitignore that ignores everything (*)")
    if (pack / CHANGELOG).is_file():
        errors += changelog_findings((pack / CHANGELOG).read_text(encoding="utf-8"))
    if simulation and (pack / "private" / "reflection.md").exists():
        errors.append("a simulated pack never holds a reflection on the person (plan item 0.2)")
    manifest = pack / "pack.json"
    if manifest.is_file():
        data = cc.read_json(manifest)
        errors += [f"pack.json {e}" for e in cc.validate_schema(data, "pack.schema.json")]
        for entry in data.get("files", []):
            target = pack / entry.get("path", "")
            if not target.is_file():
                warnings.append(f"{entry.get('path')}: listed in pack.json but missing")
            elif cc.sha256_text(target.read_text(encoding="utf-8")) != entry.get("sha256"):
                warnings.append(f"{entry.get('path')}: drift (edited since it was rendered; re-render or keep the edit on purpose)")
    else:
        warnings.append("no pack.json: render the pack with render_pack.py")
    return errors, warnings


def validate(pack: Path, role_dir: str | None = None) -> tuple[list[str], list[str]]:
    profile_path = pack / "cognitive-profile.json"
    if not profile_path.is_file():
        return ["cognitive-profile.json is missing"], []
    try:
        profile = cc.read_json(profile_path)
    except ValueError as exc:
        return [f"cognitive-profile.json is not valid JSON ({exc})"], []
    errors = [f"cognitive-profile.json {e}" for e in cc.validate_schema(profile, "cognitive-profile.schema.json")]
    if errors:
        return errors, []
    role = cc.Role(cc.role_dir(profile["role"], role_dir))
    answers = None
    answers_path = pack / "private" / "answers.json"
    if answers_path.is_file():
        answers = cc.read_json(answers_path)
        errors += [f"private/answers.json {e}" for e in cc.validate_schema(answers, "answers.schema.json")]
    evidence = None
    evidence_path = pack / "evidence-map.md"
    if evidence_path.is_file():
        evidence = evidence_rows(evidence_path.read_text(encoding="utf-8"))
    elif profile.get("source") == "simulation":
        errors.append("evidence-map.md is missing (a simulated pack's evidence)")
    e1, w1 = profile_findings(profile, role, answers, evidence)
    e2, w2 = file_findings(pack, profile, role)
    return errors + e1 + e2, w1 + w2


def main(argv=None) -> int:
    cc.configure_output()
    parser = argparse.ArgumentParser(description="Validate a CEET pack against its role.")
    parser.add_argument("pack", help="the pack folder (e.g. .harness/packs/<pack-id>)")
    parser.add_argument("--role-dir", help="the role's folder, when it is not installed next to ceet-core")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    pack = Path(args.pack).resolve()
    if not pack.is_dir():
        print(f"error: not a directory: {pack}", file=sys.stderr)
        return 2
    errors, warnings = validate(pack, args.role_dir)
    if args.json:
        print(json.dumps({"pack": pack.name, "valid": not errors, "errors": errors, "warnings": warnings}, indent=2))
        return 1 if errors else 0
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"pack {pack.name}: {'invalid' if errors else 'ok'}"
          + (f" ({len(errors)} error(s))" if errors else "") + (f" ({len(warnings)} warning(s))" if warnings else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
