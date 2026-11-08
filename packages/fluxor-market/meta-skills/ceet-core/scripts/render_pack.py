#!/usr/bin/env python3
"""Render a CEET pack from its cognitive-profile.json, deterministically, and manage it afterwards.

  render_pack.py render <pack> [--adapter claude-code|cursor|copilot|agents-md|agent-skills|all]...
                               [--write] [--diff] [--core-size 10]
  render_pack.py teachback <pack>                 write private/teachback.md for the person to review
  render_pack.py apply-teachback <pack> [--write] apply the verdicts in private/teachback.json
  render_pack.py reprofile <pack> --profile <new.json> [--decisions <new.json>] [--adapter ...] [--write]
  render_pack.py install <pack> --adapter claude-code [--yes] [--force]
  render_pack.py erase <pack> [--yes] [--force]

`render` reads the synthesis (`cognitive-profile.json`, `private/answers.json`, and for a simulated
pack `evidence-map.md`), refuses to go on without a consent record or with a slot that has neither a
value nor an explicit "not synthesized", sanitizes every value, fills every template of the role,
and writes the pack: the rendered artifacts, `core.md` (the short always-on core), the examples,
the mechanical checks, the adapters asked for, a README and `pack.json` with the hash of every
shared file. Without `--write` it only shows what would change, so the person can approve it.

`reprofile` takes a new synthesis from a scratch file, says which slots moved against the pack's
current profile, and with `--write` replaces the profile, bumps its version, adds the entry to
`profile-changelog.md` and renders as `render --write` does.

`--pack`-style arguments take a pack id (resolved under `.harness/packs/`) or a path. Standard
library only (Python 3.9+).
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ceet_common as cc  # noqa: E402
import validate_pack  # noqa: E402

ADAPTERS = ["agents-md", "agent-skills", "claude-code", "cursor", "copilot"]
MERGE_BY_HAND = ("section.md", "settings.hooks.json")
CHANGELOG = validate_pack.CHANGELOG


def today() -> str:
    return dt.date.today().isoformat()


def resolve_pack(value: str, project: str | None) -> Path:
    path = Path(value)
    if path.is_dir() or "/" in value or "\\" in value:
        return path.resolve()
    return cc.packs_dir(cc.project_root(project)) / value


def pack_display(pack: Path, root: Path) -> str:
    try:
        return pack.resolve().relative_to(root).as_posix()
    except ValueError:
        return pack.resolve().as_posix()


# ─── Values ─────────────────────────────────────────────────────────────────────────────────────

def slot_texts(profile: dict, role: cc.Role, answers: dict | None, evidence_text: str | None,
               notes: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    if role.name_slot:
        values[role.name_slot] = cc.sanitize(profile["name"])[0]
    meta = profile.get("meta", {})
    values["meta.date"] = meta.get("date") or today()
    values["meta.version"] = meta.get("version") or "1.0.0"
    if meta.get("fingerprint_hash"):
        values["meta.fingerprint_hash"] = meta["fingerprint_hash"]
    elif answers is not None:
        values["meta.fingerprint_hash"] = cc.fingerprint(answers.get("answers", {}))
    elif evidence_text is not None:
        values["meta.fingerprint_hash"] = cc.sha256_text(evidence_text)[:12]
    else:
        values["meta.fingerprint_hash"] = "unknown"
    for slot in role.content_slots():
        value = cc.lookup(profile, slot)
        if slot == "identity.contradictions" and value is None and profile.get("contradictions"):
            value = "\n".join(
                f"- {c['tension']} [{c['question_a']}, {c['question_b']}]"
                + (f" How I resolve it: {c['resolution']}" if c.get("resolution") else "")
                for c in profile["contradictions"])
        if cc.is_not_synthesized(value):
            values[slot] = f"Not synthesized: {value['_note']}"
        elif isinstance(value, str):
            clean, changes = cc.sanitize(value)
            notes += [f"{{{slot}}}: {c}" for c in changes]
            values[slot] = clean
    return values


def fill(template: str, values: dict[str, str]) -> str:
    return cc.SLOT.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def with_notice(text: str) -> str:
    """The Simulation Notice right after the first heading (or at the top)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[:i + 1] + ["", cc.SIMULATION_NOTICE] + lines[i + 1:])
    return cc.SIMULATION_NOTICE + "\n\n" + text


def describe(text: str) -> str:
    """A file's one-line description: its first blockquote after the title, else the title."""
    title = ""
    for line in text.splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("> ") and title and "Simulation Notice" not in line:
            return line[2:].strip()
    return title


def evidence_count(value: str) -> int:
    return len([r for r in cc.refs(value) if r != "teachback"])


# ─── The pack's own files ────────────────────────────────────────────────────────────────────────

def core_md(profile: dict, role: cc.Role, values: dict[str, str], rendered: dict[str, str], size: int,
            has_examples: bool) -> str:
    """The short always-on core: how the person thinks, decides and speaks, their best-evidenced
    directives, and an index of what loads on demand (plan item 2.2)."""
    ranked = []
    for slot in role.directive_slots():
        value = cc.lookup(profile, slot)
        if isinstance(value, str):
            ranked.append((-evidence_count(value), role.directive_slots().index(slot), slot))
    ranked.sort()
    firm = [slot for _, _, slot in ranked[:size]]
    name = values.get(role.name_slot, profile["name"])
    lines = [f"# Core — {name} ({role.title})", "",
             f"> Always-on context for any AI tool working as or with {name}. Everything else in this pack",
             "> loads with the agent, skill or command that needs it. Generated from cognitive-profile.json;",
             "> edit the profile and re-render, not this file.", ""]
    for slot, heading in (("identity.cognitive_signature", "How I think"),
                          ("identity.decision_framework", "How I decide"),
                          ("identity.communication_voice", "How I communicate")):
        if slot in values:
            lines += [f"## {heading}", "", values[slot], ""]
    if firm:
        lines += ["## My best-evidenced rules", ""]
        for slot in firm:
            _, domain, field = slot.split(".", 2)
            label = f"{domain.replace('_', ' ').capitalize()} / {field.replace('_', ' ')}"
            lines.append(f"- **{label}:** {values[slot]}")
        lines.append("")
    if has_examples:
        lines += ["## Before deciding", "",
                  "When a task resembles a decision I have made, read the three to five closest cases in",
                  "`examples/decisions.md` (or run `bin/examples.py select --pack <this pack> --task \"...\"`) and",
                  "follow what I did and why, unless the task says otherwise.", ""]
    index = [(rel, describe(text)) for rel, text in sorted(rendered.items())
             if rel.split("/")[0] in ("agents", "skills", "commands", "rules", "hooks") and rel.endswith(".md")]
    if index:
        lines += ["## Load on demand", ""]
        lines += [f"- `{rel}`: {desc}" for rel, desc in index]
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def decisions_md(decisions: list[dict], name: str) -> str:
    lines = [f"# Decisions — {name}", "",
             "> Real decisions with their rationale, from the decision-capture part of the interview. Use the",
             "> closest ones as demonstrations of how I decide; they are not rules.", ""]
    for d in decisions:
        lines.append(f"## {d['id']}: {d['situation'][:80]}{'…' if len(d['situation']) > 80 else ''}")
        lines.append("")
        lines.append(f"- **Situation:** {d['situation']}")
        if d.get("domain"):
            lines.append(f"- **Domain:** {d['domain']}")
        if d.get("cues"):
            lines.append(f"- **What I noticed:** {'; '.join(d['cues'])}")
        if d.get("options"):
            lines.append(f"- **Options:** {'; '.join(d['options'])}")
        lines.append(f"- **What I did:** {d['choice']}")
        lines.append(f"- **Why:** {d['rationale']}")
        if d.get("noviceWould"):
            lines.append(f"- **What a less experienced person would do:** {d['noviceWould']}")
        lines.append(f"- **Source:** [{d['source']}]" + (f", {d['when']}" if d.get("when") else ""))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def readme_md(pack_id: str, profile: dict, role: cc.Role, name: str, has_examples: bool, has_checks: bool,
              adapters: list[str]) -> str:
    simulated = profile.get("source") == "simulation"
    lines = [f"# CEET pack — {pack_id}", ""]
    if simulated:
        lines += [cc.SIMULATION_NOTICE, ""]
    lines += [f"{name}'s cognitive clone as a **{role.title}**, rendered by ceet-core from `cognitive-profile.json`.",
              "", "| Load | Files |", "| --- | --- |",
              "| Always | `core.md` |",
              "| With the task | `agents/`, `skills/`, `commands/`, `rules/`" + (", `hooks/`" if (role.folder / "templates" / "hooks").is_dir() else "") + " |"]
    if has_examples:
        lines.append("| As demonstrations | the closest cases of `examples/decisions.md` (`bin/examples.py select`) |")
    lines += ["| For people | `cognitive-profile.md` (the full clone) |", ""]
    if has_checks:
        lines += ["The checks that are not judgment calls are in `hooks/checks.json` and run with `bin/ceet_check.py`;",
                  "run `bin/ceet_check.py bench --pack <pack>` and wire a hook only when the bench is green.", ""]
    if adapters:
        lines += ["Adapters for " + ", ".join(adapters) + " are under `adapters/`; install them with",
                  "`render_pack.py install <pack> --adapter <tool>`.", ""]
    consent = profile.get("consent", {})
    lines += ["## Personal data", "",
              f"This pack is personal data about {consent.get('subject', name)}. Agreed uses: "
              + "; ".join(consent.get("uses", [])) + ". Never used for: " + ", ".join(consent.get("excludedUses", [])) + ".",
              f"Storage: {consent.get('storage', 'local')}. `private/` (verbatim answers, private reflection) is never shared.",
              "Erase everything, installed adapters included, with `render_pack.py erase <pack> --yes`.", ""]
    return "\n".join(lines)


# ─── Adapters ────────────────────────────────────────────────────────────────────────────────────

def front_matter(pairs: list[tuple[str, object]]) -> str:
    lines = ["---"]
    for key, value in pairs:
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines += [f"  {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in value.items()]
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def skill_name(pack_id: str, stem: str) -> str:
    return f"{pack_id}-{stem}"[:64].rstrip("-")


def build_adapters(tools: list[str], pack_id: str, pack_path: str, rendered: dict[str, str], core: str,
                   profile: dict, has_examples: bool, checks_green: bool) -> dict[str, str]:
    out: dict[str, str] = {}
    meta = {"ceet-pack": pack_id, "ceet-role": profile["role"], "ceet-source": profile["source"]}
    by_kind: dict[str, list[tuple[str, str]]] = {}
    for rel, text in sorted(rendered.items()):
        kind = rel.split("/")[0]
        if kind in ("agents", "skills", "commands", "rules") and rel.endswith(".md"):
            by_kind.setdefault(kind, []).append((Path(rel).stem, text))
    for tool in tools:
        base = f"adapters/{tool}"
        if tool == "agents-md":
            out[f"{base}/AGENTS.section.md"] = (
                f"## Working with {profile['name']} ({profile['role']})\n\n"
                f"Follow the core below on every task. For a specific task, load the matching file from "
                f"`{pack_path}/agents/`, `skills/`, `commands/` or `rules/`.\n\n" + core.split("\n", 2)[2])
        elif tool == "agent-skills":
            for stem, text in by_kind.get("skills", []):
                name = skill_name(pack_id, stem)
                out[f"{base}/{name}/SKILL.md"] = front_matter(
                    [("name", name), ("description", describe(text)[:1024]), ("metadata", meta)]) + text
        elif tool == "claude-code":
            for stem, text in by_kind.get("agents", []):
                out[f"{base}/.claude/agents/{stem}.md"] = front_matter(
                    [("name", stem), ("description", describe(text)[:1024])]) + text
            for stem, text in by_kind.get("commands", []):
                out[f"{base}/.claude/commands/{stem}.md"] = front_matter([("description", describe(text)[:300])]) + text
            for stem, text in by_kind.get("skills", []):
                name = skill_name(pack_id, stem)
                out[f"{base}/.claude/skills/{name}/SKILL.md"] = front_matter(
                    [("name", name), ("description", describe(text)[:1024]), ("metadata", meta)]) + text
            out[f"{base}/CLAUDE.section.md"] = f"@{pack_path}/core.md\n"
            hooks: dict[str, list] = {}
            if checks_green:
                hooks["PreToolUse"] = [{"matcher": "Bash", "hooks": [{"type": "command", "command":
                                        f"python3 {pack_path}/bin/ceet_check.py claude-code --pack {pack_path}"}]}]
            if has_examples:
                hooks["UserPromptSubmit"] = [{"hooks": [{"type": "command", "command":
                                              f"python3 {pack_path}/bin/examples.py inject --pack {pack_path}"}]}]
            if hooks:
                out[f"{base}/settings.hooks.json"] = json.dumps({"hooks": hooks}, indent=2) + "\n"
        elif tool == "cursor":
            out[f"{base}/.cursor/rules/{pack_id}-core.mdc"] = front_matter(
                [("description", f"{profile['name']}'s core: how they think, decide and speak"), ("alwaysApply", True)]) + core
            for stem, text in by_kind.get("rules", []) + by_kind.get("agents", []):
                out[f"{base}/.cursor/rules/{pack_id}-{stem}.mdc"] = front_matter(
                    [("description", describe(text)), ("alwaysApply", False)]) + text
        elif tool == "copilot":
            out[f"{base}/.github/instructions/{pack_id}.instructions.md"] = front_matter([("applyTo", "**")]) + core
            for stem, text in by_kind.get("agents", []):
                out[f"{base}/.github/agents/{stem}.agent.md"] = front_matter([("description", describe(text))]) + text
    return out


# ─── Render ─────────────────────────────────────────────────────────────────────────────────────

def load_inputs(pack: Path, role_dir: str | None):
    profile_path = pack / "cognitive-profile.json"
    if not profile_path.is_file():
        raise SystemExit(f"error: {profile_path} does not exist: synthesize the profile first")
    profile = cc.read_json(profile_path)
    errors = cc.validate_schema(profile, "cognitive-profile.schema.json")
    if errors:
        raise SystemExit("error: cognitive-profile.json is invalid:\n  " + "\n  ".join(errors[:15]))
    role = cc.Role(cc.role_dir(profile["role"], role_dir))
    answers_path = pack / "private" / "answers.json"
    answers = cc.read_json(answers_path) if answers_path.is_file() else None
    evidence_path = pack / "evidence-map.md"
    evidence_text = evidence_path.read_text(encoding="utf-8") if evidence_path.is_file() else None
    return profile, role, answers, evidence_text


def templates_hash(role: cc.Role) -> str:
    lines = []
    for path in sorted(p for p in (role.folder / "templates").rglob("*") if p.is_file()):
        rel = path.relative_to(role.folder).as_posix()
        lines.append(f"{rel} {cc.sha256_text(path.read_text(encoding='utf-8'))}")
    return cc.sha256_text("\n".join(lines) + "\n")


def run_bench(pack_bin: Path, pack: Path, root: Path) -> bool:
    try:
        out = subprocess.run([sys.executable, str(pack_bin), "bench", "--pack", str(pack)], cwd=root,
                             capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return out.returncode == 0


def build(pack: Path, args) -> tuple[dict[str, str], dict[str, Path], list[str], list[str], dict]:
    profile, role, answers, evidence_text = load_inputs(pack, args.role_dir)
    evidence = validate_pack.evidence_rows(evidence_text) if evidence_text is not None else None
    if answers is None and profile["source"] == "interview":
        raise SystemExit("error: an interview pack renders from its private/answers.json (run interview.py)")
    errors, warnings = validate_pack.profile_findings(profile, role, answers, evidence)
    notes: list[str] = list(warnings)
    values = slot_texts(profile, role, answers, evidence_text, notes)
    simulated = profile["source"] == "simulation"
    outputs: dict[str, str] = {}
    copies: dict[str, Path] = {}
    rendered: dict[str, str] = {}
    for path in [role.profile_template] + role.templates():
        rel = path.relative_to(role.folder / "templates").as_posix()
        text = fill(path.read_text(encoding="utf-8"), values)
        if simulated:
            text = with_notice(text)
        outputs[rel] = text
        if path != role.profile_template:
            rendered[rel] = text
    decisions: list[dict] = []
    decisions_path = pack / "examples" / "decisions.json"
    if decisions_path.is_file():
        data = cc.read_json(decisions_path)
        problems = cc.validate_schema(data, "decisions.schema.json")
        errors += [f"examples/decisions.json {p}" for p in problems]
        if not problems:
            decisions = data["decisions"]
            answered = set((answers or {}).get("answers", {}))
            for d in decisions:
                src = d["source"]
                if src.startswith("Q") and (src not in role.question_ids() or (answers is not None and src not in answered)):
                    errors.append(f"examples/decisions.json {d['id']}: source {src} is not an answered question")
                if src.startswith("E") and (evidence is None or src not in evidence):
                    errors.append(f"examples/decisions.json {d['id']}: source {src} is not an evidence row")
                for key in ("situation", "choice", "rationale"):
                    d[key], changes = cc.sanitize(d[key])
                    notes += [f"{d['id']}.{key}: {c}" for c in changes]
            name = values.get(role.name_slot, profile["name"])
            outputs["examples/decisions.md"] = decisions_md(decisions, name)
            if simulated:
                outputs["examples/decisions.md"] = with_notice(outputs["examples/decisions.md"])
            copies["bin/examples.py"] = cc.HERE / "examples.py"
    has_hooks = (role.folder / "templates" / "hooks").is_dir()
    checks = dict(profile.get("checks", {}))
    has_checks = has_hooks or bool(checks)
    if has_checks:
        checks.setdefault("secrets", has_hooks)
        outputs["hooks/checks.json"] = json.dumps({"schemaVersion": "1.0.0", **checks}, indent=2, ensure_ascii=False) + "\n"
        copies["bin/ceet_check.py"] = cc.HERE / "ceet_check.py"
    core = core_md(profile, role, values, rendered, args.core_size, bool(decisions))
    if simulated:
        core = with_notice(core)
    outputs["core.md"] = core
    root = cc.project_root(args.project)
    pack_path = pack_display(pack, root)
    tools = ADAPTERS if "all" in (args.adapter or []) else sorted(set(args.adapter or []))
    checks_green = False
    if has_checks and "claude-code" in tools and not errors:
        # The bench needs the pack's checks on disk: judge it from a scratch copy.
        scratch = pack / "private" / ".bench"
        (scratch / "hooks").mkdir(parents=True, exist_ok=True)
        cc.write_text(scratch / "hooks" / "checks.json", outputs["hooks/checks.json"])
        checks_green = run_bench(cc.HERE / "ceet_check.py", scratch, root)
        shutil.rmtree(scratch, ignore_errors=True)
        notes.append("checks bench: " + ("green, the Claude Code hook is included" if checks_green
                                         else "red, the Claude Code hook is left out (run bin/ceet_check.py bench)"))
    outputs.update(build_adapters(tools, pack.name, pack_path, rendered, core, profile, bool(decisions), checks_green))
    name = values.get(role.name_slot, profile["name"])
    outputs["README.md"] = readme_md(pack.name, profile, role, name, bool(decisions), has_checks, tools)
    unsynthesized = [s for s in role.content_slots() if cc.is_not_synthesized(cc.lookup(profile, s))]
    if unsynthesized:
        notes.append(f"{len(unsynthesized)} slot(s) not synthesized: {', '.join(unsynthesized[:6])}"
                     + ("…" if len(unsynthesized) > 6 else ""))
    meta = {"profile": profile, "role": role, "answers": answers, "templatesHash": templates_hash(role)}
    return outputs, copies, errors, notes, meta


def pack_manifest(pack: Path, profile: dict, role: cc.Role, texts: dict[str, str], templates_sha: str,
                  previous: dict | None) -> dict:
    version = None
    manifest = role.folder / "skill.json"
    if manifest.is_file():
        version = cc.read_json(manifest).get("version")
    files = [{"path": rel, "sha256": cc.sha256_text(text)} for rel, text in sorted(texts.items())]
    data = {"schemaVersion": cc.PACK_SCHEMA_VERSION, "packId": pack.name,
            "metaSkill": role.id + (f"@{version}" if version else ""), "formVersion": role.form["formVersion"],
            "source": profile["source"], "profileVersion": profile.get("meta", {}).get("version", "1.0.0"),
            "renderedAt": today(), "consent": profile["consent"], "templatesHash": templates_sha, "files": files}
    if previous and previous.get("installed"):
        data["installed"] = previous["installed"]
    return data


def cmd_render(args) -> int:
    return render(resolve_pack(args.pack, args.project), args)[0]


def render(pack: Path, args) -> tuple[int, bool]:
    """Render the pack (written with `args.write`). Returns the exit code and whether it wrote."""
    outputs, copies, errors, notes, meta = build(pack, args)
    for n in notes:
        print(f"note: {n}")
    if errors:
        for e in errors:
            print(f"error: {e}")
        print(f"not rendered: {len(errors)} error(s)")
        return 1, False
    texts = dict(outputs)
    for rel, src in copies.items():
        texts[rel] = src.read_text(encoding="utf-8")
    # The pack ships these sources as they are, so a hidden character in one reaches every tool
    # that reads the pack: it is stripped from the file too, not only from the rendered values.
    cleaned_sources: dict[str, str] = {}
    for rel in ("cognitive-profile.json", "evidence-map.md", "examples/decisions.json", CHANGELOG):
        if (pack / rel).is_file():
            raw = (pack / rel).read_text(encoding="utf-8")
            texts[rel] = cc.strip_invisible(raw)
            if texts[rel] != raw:
                cleaned_sources[rel] = texts[rel]
                print(f"note: {rel}: removed {len(raw) - len(texts[rel])} invisible or bidirectional character(s)")
    previous = cc.read_json(pack / "pack.json") if (pack / "pack.json").is_file() else None
    manifest = pack_manifest(pack, meta["profile"], meta["role"], texts, meta["templatesHash"], previous)
    new_files = {**outputs, **{rel: texts[rel] for rel in copies}, **cleaned_sources}
    new_files["pack.json"] = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    stale = []
    if previous:
        old_hashes = {f["path"]: f["sha256"] for f in previous.get("files", [])}
        for rel, sha in old_hashes.items():
            if rel not in texts and (pack / rel).is_file():
                stale.append((rel, cc.sha256_text((pack / rel).read_text(encoding="utf-8")) == sha))
    counts = {"new": 0, "changed": 0, "unchanged": 0}
    for rel, text in sorted(new_files.items()):
        target = pack / rel
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current is None:
            counts["new"] += 1
            status = "+"
        elif current == text:
            counts["unchanged"] += 1
            continue
        else:
            counts["changed"] += 1
            status = "~"
        if rel != "pack.json":
            print(f"{status} {rel}")
        if args.diff and current is not None and rel != "pack.json":
            sys.stdout.writelines(difflib.unified_diff(current.splitlines(True), text.splitlines(True),
                                                       f"a/{rel}", f"b/{rel}"))
    for rel, unchanged in stale:
        print(f"- {rel}" + ("" if unchanged else " (edited by hand: kept)"))
    print(f"{counts['new']} new, {counts['changed']} changed, {counts['unchanged']} unchanged, {len(stale)} stale")
    if not args.write:
        print("dry run: show this to the person, then re-run with --write")
        return 0, False
    for rel, text in new_files.items():
        cc.write_text(pack / rel, text)
    for rel, unchanged in stale:
        if unchanged:
            (pack / rel).unlink()
    storage = meta["profile"]["consent"]["storage"]
    cc.write_text(pack / "private" / ".gitignore", "# Verbatim answers and private reflection: never committed.\n*\n")
    if storage == "local":
        cc.write_text(pack / ".gitignore", "# This pack is personal data kept local (consent: storage local).\n*\n")
    errors, warnings = validate_pack.validate(pack, args.role_dir)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"wrote {pack}: {'valid' if not errors else 'INVALID'}")
    return (1 if errors else 0), True


# ─── Teachback ──────────────────────────────────────────────────────────────────────────────────

def cmd_teachback(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    profile, role, answers, _ = load_inputs(pack, args.role_dir)
    given = (answers or {}).get("answers", {})
    lines = [f"# Teachback — {profile['name']}", "",
             "Read each directive with the answers it came from. For each one, say **accept**, **edit** (and",
             "give your wording) or **reject**. Your edits are kept: they are how the clone learns your",
             "preferences.", ""]
    verdicts_path = pack / "private" / "teachback.json"
    verdicts = cc.read_json(verdicts_path) if verdicts_path.is_file() else {}
    for slot in role.content_slots():
        value = cc.lookup(profile, slot)
        if not isinstance(value, str):
            continue
        lines += [f"## `{slot}`", "", "> " + value.replace("\n", "\n> "), ""]
        for ref in cc.refs(value):
            if ref in given:
                excerpt = given[ref]["text"].strip().replace("\n", " ")
                lines.append(f"- {ref}: “{excerpt[:400]}{'…' if len(excerpt) > 400 else ''}”")
        lines += ["", "Verdict: accept / edit / reject", ""]
        verdicts.setdefault(slot, {"verdict": "pending"})
    cc.write_text(pack / "private" / "teachback.md", "\n".join(lines))
    cc.write_json(verdicts_path, verdicts)
    print(f"wrote {pack / 'private' / 'teachback.md'} and {verdicts_path} ({len(verdicts)} directives to review)")
    return 0


def cmd_apply_teachback(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    profile, role, _, _ = load_inputs(pack, args.role_dir)
    verdicts = cc.read_json(pack / "private" / "teachback.json")
    changed, pending = [], []
    for slot, verdict in sorted(verdicts.items()):
        kind = verdict.get("verdict")
        parts = slot.split(".")
        parent = profile
        for part in parts[:-1]:
            parent = parent.setdefault(part, {})
        if kind == "edit" and verdict.get("text"):
            text = verdict["text"].strip()
            parent[parts[-1]] = text if cc.refs(text) else f"{text} [teachback]"
            changed.append(f"edited {slot}")
        elif kind == "reject":
            parent[parts[-1]] = {"_status": cc.NOT_SYNTHESIZED, "_note": "Rejected by the person at teachback."}
            changed.append(f"rejected {slot}")
        elif kind != "accept":
            pending.append(slot)
    profile["teachback"] = {"status": "pending" if pending else "done", "date": today()}
    for c in changed:
        print(c)
    print(f"{len(changed)} change(s), {len(pending)} still pending")
    if args.write:
        cc.write_json(pack / "cognitive-profile.json", profile)
        print("updated cognitive-profile.json: re-render the pack")
    else:
        print("dry run: re-run with --write")
    return 0


# ─── Re-profile ─────────────────────────────────────────────────────────────────────────────────

SECTIONS = ("identity", "directives", "checks", "contradictions", "decisions")
REF_ITEM = re.compile(r"(?:Q|E)[1-9][0-9]*")


def profile_items(profile: dict, decisions: list[dict] | None = None) -> dict[str, object]:
    """Every part of a profile a re-profile can move, by a stable key: `identity.*` and
    `directives.*` slots, `checks.<kind>`, `contradictions.<Qa>-<Qb>` and `decisions.<id>`."""
    items: dict[str, object] = {}

    def walk(node: dict, prefix: str) -> None:
        for key, value in node.items():
            if isinstance(value, dict) and not cc.is_not_synthesized(value):
                walk(value, f"{prefix}.{key}")
            else:
                items[f"{prefix}.{key}"] = value

    walk(profile.get("identity", {}), "identity")
    walk(profile.get("directives", {}), "directives")
    for kind, value in profile.get("checks", {}).items():
        items[f"checks.{kind}"] = value
    for c in profile.get("contradictions", []):
        key, n = f"contradictions.{c['question_a']}-{c['question_b']}", 2
        while key in items:
            key, n = f"contradictions.{c['question_a']}-{c['question_b']}-{n}", n + 1
        items[key] = c
    for d in decisions or []:
        items[f"decisions.{d['id']}"] = d
    return items


def citations(value: object) -> list[str]:
    """The evidence a value cites: `[Q<n>]`/`[E<n>]`/`[teachback]` groups in text, and the
    `source`/`question_a`/`question_b` fields of checks, contradictions and decisions."""
    found: list[str] = []

    def collect(node: object) -> None:
        if isinstance(node, str):
            for ref in cc.refs(node) or ([node] if REF_ITEM.fullmatch(node) else []):
                if ref not in found:
                    found.append(ref)
        elif isinstance(node, dict) and not cc.is_not_synthesized(node):
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)

    collect(value)
    return found


def shown(value: object) -> str:
    """A value on one line, without its citation groups, through the render's sanitizer."""
    if cc.is_not_synthesized(value):
        text = f"Not synthesized: {value.get('_note', '')}"
    elif isinstance(value, str):
        text = cc.REF_GROUP.sub("", value)
    elif isinstance(value, dict) and "tension" in value:
        text = value["tension"] + (f" How I resolve it: {value['resolution']}" if value.get("resolution") else "")
    elif isinstance(value, dict) and "choice" in value:
        text = f"{value['situation']} Choice: {value['choice']}"
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return " ".join(cc.sanitize(text)[0].split())


def profile_diff(old: dict, new: dict, old_decisions: list[dict] | None = None,
                 new_decisions: list[dict] | None = None) -> list[dict]:
    """What moved between two profiles: one entry per added, removed or changed item, in section
    order. A change that only re-cites the same text is marked `citationsOnly`."""
    before, after = profile_items(old, old_decisions), profile_items(new, new_decisions)
    moved = []
    for key in sorted(set(before) | set(after), key=lambda k: (SECTIONS.index(k.split(".")[0]), k)):
        if key not in before:
            moved.append({"slot": key, "change": "added", "value": after[key], "citations": citations(after[key])})
        elif key not in after:
            moved.append({"slot": key, "change": "removed", "value": before[key], "citations": citations(before[key])})
        elif before[key] != after[key]:
            moved.append({"slot": key, "change": "changed", "value": after[key], "citations": citations(after[key]),
                          "citationsOnly": shown(before[key]) == shown(after[key])})
    return moved


def form_major(version: object) -> str:
    return str(version).split(".")[0]


def bumped(version: str, major: bool) -> str:
    first, second = (int(part) for part in version.split(".")[:2])
    return f"{first + 1}.0.0" if major else f"{first}.{second + 1}.0"


def moved_line(item: dict) -> str:
    cites = ", ".join(item["citations"]) or "none"
    if item["change"] == "removed":
        return f"- **removed** `{item['slot']}` (cited {cites})"
    label = "changed (citations only)" if item.get("citationsOnly") else item["change"]
    return f"- **{label}** `{item['slot']}` (cites {cites}): {shown(item['value'])}"


def changelog_entry(date: str, old_version: str, new_version: str, moved: list[dict], form_change: str | None) -> str:
    lines = [f"## {date} · profile {old_version} → {new_version}", ""]
    if form_change:
        lines.append(f"- **form** {form_change}: the previous answers were mapped to the new question ids by hand")
    lines += [moved_line(item) for item in moved]
    return "\n".join(lines) + "\n"


def with_entry(current: str | None, entry: str, name: str) -> str:
    """The changelog with `entry` first: newest first, under a fixed header."""
    if current is None:
        return (f"# Profile changelog — {cc.sanitize(name)[0]}\n\n"
                "> What moved at each re-profile, newest first. Written by `render_pack.py reprofile` from the\n"
                "> profile's own slots and citations, never from the answers; a hand edit shows as drift.\n\n" + entry)
    head, sep, rest = current.partition("\n## ")
    return head.rstrip("\n") + "\n\n" + entry + ("\n## " + rest if sep else "")


def cmd_reprofile(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    old, role, answers, evidence_text = load_inputs(pack, args.role_dir)
    if old["source"] == "simulation":
        print("error: a simulated pack is re-profiled through ceet-impersonator and its evidence map", file=sys.stderr)
        return 2
    new = cc.read_json(Path(args.profile))
    problems = cc.validate_schema(new, "cognitive-profile.schema.json")
    if problems:
        print("error: the new profile is invalid:\n  " + "\n  ".join(problems[:15]), file=sys.stderr)
        return 1
    if (new["role"], new["source"]) != (old["role"], old["source"]):
        print(f"error: the new profile is a {new['source']} profile for {new['role']}; this pack is an "
              f"{old['source']} pack for {old['role']}", file=sys.stderr)
        return 1
    form = str(role.form["formVersion"])
    if form_major(new["formVersion"]) != form_major(form):
        print(f"error: the new profile cites form {new['formVersion']}, but {role.id} asks form {form}, whose "
              f"question ids mean something else. Re-synthesize against form {form} (map the previous answers to "
              f"its question ids by hand: interview-protocol.md, Re-profiling), or re-profile with the version "
              f"of {role.id} whose form is {new['formVersion']}.", file=sys.stderr)
        return 1
    evidence = validate_pack.evidence_rows(evidence_text) if evidence_text is not None else None
    errors, warnings = validate_pack.profile_findings(new, role, answers, evidence)
    for w in warnings:
        print(f"note: {w}")
    if errors:
        for e in errors:
            print(f"error: {e}")
        print(f"not re-profiled: {len(errors)} error(s) in the new profile")
        return 1
    decisions_path = pack / "examples" / "decisions.json"
    old_decisions = cc.read_json(decisions_path)["decisions"] if decisions_path.is_file() else []
    new_decisions_data = cc.read_json(Path(args.decisions)) if args.decisions else None
    if new_decisions_data is not None:
        problems = cc.validate_schema(new_decisions_data, "decisions.schema.json")
        if problems:
            print("error: the new decisions are invalid:\n  " + "\n  ".join(problems[:15]), file=sys.stderr)
            return 1
    new_decisions = new_decisions_data["decisions"] if new_decisions_data is not None else old_decisions

    moved = profile_diff(old, new, old_decisions, new_decisions)
    if not moved:
        print("nothing moved: the new synthesis says what the pack already says; nothing written")
        return 0
    old_version = old.get("meta", {}).get("version", "1.0.0")
    form_changed = form_major(old["formVersion"]) != form_major(new["formVersion"])
    new_version = bumped(old_version, form_changed)
    form_change = f"{old['formVersion']} → {new['formVersion']}" if form_changed else None
    entry = changelog_entry(today(), old_version, new_version, moved, form_change)
    print(entry, end="")
    print(f"{len(moved)} moved; profile {old_version} → {new_version}")
    if not args.write:
        print("dry run: show this to the person, then re-run with --write")
        return 0

    new["meta"] = {**new.get("meta", {}), "date": today(), "version": new_version}
    if answers is not None:
        new["meta"].pop("fingerprint_hash", None)  # the render recomputes it from the current answers
    changelog = pack / CHANGELOG
    previous = {path: path.read_text(encoding="utf-8") if path.is_file() else None
                for path in (pack / "cognitive-profile.json", decisions_path, changelog)}
    cc.write_json(pack / "cognitive-profile.json", new)
    if new_decisions_data is not None:
        cc.write_json(decisions_path, new_decisions_data)
    cc.write_text(changelog, with_entry(previous[changelog], entry, new["name"]))
    if not args.adapter and (pack / "adapters").is_dir():
        # Re-render the adapters the pack already has, or the render would drop them as stale.
        args.adapter = sorted(p.name for p in (pack / "adapters").iterdir() if p.name in ADAPTERS)
    args.write = True
    code, wrote = render(pack, args)
    if not wrote:
        for path, text in previous.items():
            if text is None:
                path.unlink(missing_ok=True)
            else:
                cc.write_text(path, text)
        print("not re-profiled: the render refused the new profile; the pack is as it was")
    return code


# ─── Install and erase ──────────────────────────────────────────────────────────────────────────

def cmd_install(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    root = cc.project_root(args.project)
    base = pack / "adapters" / args.adapter
    if not base.is_dir():
        print(f"error: {base} does not exist: render with --adapter {args.adapter}", file=sys.stderr)
        return 2
    manifest_path = pack / "pack.json"
    manifest = cc.read_json(manifest_path)
    installed = {entry["path"]: entry for entry in manifest.get("installed", [])}
    plan, by_hand, blocked = [], [], []
    for src in sorted(p for p in base.rglob("*") if p.is_file()):
        rel = src.relative_to(base).as_posix()
        if rel.endswith(MERGE_BY_HAND):
            by_hand.append(src)
            continue
        target = root / rel
        if target.exists() and not args.force:
            if rel not in installed:
                blocked.append((rel, "a file this pack did not install is already there"))
                continue
            if cc.sha256_text(target.read_text(encoding="utf-8")) != installed[rel]["sha256"]:
                blocked.append((rel, "edited by hand since this pack installed it"))
                continue
        plan.append((src, rel))
    for src, rel in plan:
        print(f"{'install' if args.yes else 'would install'} {rel}")
    for rel, why in blocked:
        print(f"skip {rel}: {why} (--force to replace)")
    for src in by_hand:
        print(f"merge by hand: {src.relative_to(pack).as_posix()}")
    if not args.yes:
        print("dry run: nothing written; re-run with --yes once the person approved it")
        return 0
    for src, rel in plan:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        installed[rel] = {"adapter": args.adapter, "path": rel, "sha256": cc.sha256_text(src.read_text(encoding="utf-8"))}
    manifest["installed"] = sorted(installed.values(), key=lambda e: e["path"])
    cc.write_json(manifest_path, manifest)
    print(f"installed {len(plan)} file(s); recorded in pack.json for erasure")
    return 0


def cmd_erase(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    root = cc.project_root(args.project)
    if not pack.is_dir():
        print(f"error: {pack} does not exist", file=sys.stderr)
        return 2
    manifest = cc.read_json(pack / "pack.json") if (pack / "pack.json").is_file() else {}
    doomed, kept = [], []
    for entry in manifest.get("installed", []):
        target = root / entry["path"]
        if not target.is_file():
            continue
        same = cc.sha256_text(target.read_text(encoding="utf-8")) == entry["sha256"]
        (doomed if same or args.force else kept).append(target)
    fidelity = cc.fidelity_dir(root, pack.name)
    targets = doomed + [pack] + ([fidelity] if fidelity.exists() else [])
    for t in targets:
        print(f"{'erase' if args.yes else 'would erase'} {t}")
    for t in kept:
        print(f"keep {t}: edited since it was installed (--force to erase it too)")
    if not args.yes:
        print("dry run: nothing erased; re-run with --yes")
        return 0
    for t in doomed:
        t.unlink()
    shutil.rmtree(pack)
    if fidelity.exists():
        shutil.rmtree(fidelity)
    print("erased. Copies outside the project (a chat's knowledge, another machine) must be removed there.")
    return 0


def main(argv=None) -> int:
    cc.configure_output()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", help="project root (default: $CLAUDE_PROJECT_DIR, git, cwd)")
    parser.add_argument("--role-dir", help="the role's folder, when it is not installed next to ceet-core")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("render")
    p.add_argument("pack")
    p.add_argument("--adapter", action="append", choices=ADAPTERS + ["all"])
    p.add_argument("--write", action="store_true")
    p.add_argument("--diff", action="store_true")
    p.add_argument("--core-size", type=int, default=10)
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("teachback")
    p.add_argument("pack")
    p.set_defaults(func=cmd_teachback)
    p = sub.add_parser("apply-teachback")
    p.add_argument("pack")
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_apply_teachback)
    p = sub.add_parser("reprofile")
    p.add_argument("pack")
    p.add_argument("--profile", required=True, help="the new synthesis, written to a scratch file")
    p.add_argument("--decisions", help="the new examples/decisions.json, when the decisions changed too")
    p.add_argument("--adapter", action="append", choices=ADAPTERS + ["all"],
                   help="adapters to render (default: the ones the pack already has)")
    p.add_argument("--write", action="store_true")
    p.add_argument("--core-size", type=int, default=10)
    p.set_defaults(func=cmd_reprofile, diff=False)
    p = sub.add_parser("install")
    p.add_argument("pack")
    p.add_argument("--adapter", required=True, choices=ADAPTERS)
    p.add_argument("--yes", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_install)
    p = sub.add_parser("erase")
    p.add_argument("pack")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_erase)
    args = parser.parse_args(argv)
    args.pack = getattr(args, "pack", None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
