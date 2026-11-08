#!/usr/bin/env python3
"""Run a CEET interview as a resumable state file: consent first, answers verbatim, and what to ask
next chosen by which profile slots still have no evidence.

  interview.py statement [--version ceet-consent-2]   print the consent statement to read to the person
  interview.py start --role ceet-backend-engineer --person alex --name Alex \\
                     --use "help me review code the way I do" --storage local --consented
  interview.py next --pack backend-engineer-alex [--limit 3]
  interview.py answer --pack backend-engineer-alex --question Q5 --text "..."   (or the text on stdin)
  interview.py answer --pack ... --question Q5 --probe "Give me a recent example" --text "..."
  interview.py skip --pack ... --question Q3 --reason "does not apply: solo developer"
  interview.py status --pack backend-engineer-alex [--json]
  interview.py elicit --role ceet-backend-engineer --section B      (an MCP elicitation schema)

The state is `<pack>/private/answers.json` (schemas/answers.schema.json). `private/` is never shared
and never loaded by an agent doing work; the pack folder is git-ignored unless the person chose
`--storage repository`. `--pack` takes a pack id (resolved under `.harness/packs/`) or a path.
Standard library only (Python 3.9+).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ceet_common as cc  # noqa: E402

CONSENT_DOC = cc.CORE / "references" / "consent.md"


def today() -> str:
    return dt.date.today().isoformat()


def statement_text(version: str = cc.CONSENT_STATEMENT_VERSION) -> str:
    """A consent statement: the fenced block of references/consent.md that names its version, so it
    has one source (Fluxor online reads the same block from the catalog)."""
    text = CONSENT_DOC.read_text(encoding="utf-8")
    for block in re.findall(r"```text\n(.*?)\n```", text, re.S):
        if f"version {version})" in block.split("\n", 1)[0]:
            return block
    raise SystemExit(f"error: references/consent.md has no ```text block with statement {version}")


def resolve_pack(value: str, project: str | None) -> Path:
    path = Path(value)
    if path.is_dir() or "/" in value or "\\" in value:
        return path.resolve()
    return cc.packs_dir(cc.project_root(project)) / value


def load_state(pack: Path) -> dict:
    state_path = pack / "private" / "answers.json"
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} does not exist; run `interview.py start` first")
    return cc.read_json(state_path)


def save_state(pack: Path, state: dict) -> None:
    errors = cc.validate_schema(state, "answers.schema.json")
    if errors:
        raise SystemExit("error: the interview state would be invalid:\n  " + "\n  ".join(errors[:10]))
    cc.write_json(pack / "private" / "answers.json", state)


def write_gitignores(pack: Path, storage: str) -> None:
    """`private/` is never committed; the whole pack is ignored unless the person opted in."""
    cc.write_text(pack / "private" / ".gitignore", "# Verbatim answers and private reflection: never committed.\n*\n")
    ignore = pack / ".gitignore"
    if storage == "local":
        cc.write_text(ignore, "# This pack is personal data kept local (consent: storage local).\n*\n")
    elif ignore.is_file() and ignore.read_text(encoding="utf-8").strip().endswith("*"):
        ignore.unlink()


def answered(state: dict) -> set[str]:
    return {qid for qid, entry in state.get("answers", {}).items() if entry.get("text", "").strip()}


def evidence(role: cc.Role, state: dict) -> dict[str, list[str]]:
    """slot → the answered questions that feed it."""
    done = answered(state)
    found: dict[str, list[str]] = {slot: [] for slot in role.content_slots()}
    for q in role.questions():
        if q["id"] in done:
            for slot in q.get("feeds", []):
                found.setdefault(slot, []).append(q["id"])
    return found


def plan_next(role: cc.Role, state: dict, limit: int) -> list[dict]:
    """Required questions in order; then optional questions that close a gap; then the rest."""
    done = answered(state) | set(state.get("skipped", {}))
    ev = evidence(role, state)
    derived = set(role.form.get("derived", {}))
    gaps = {slot for slot, qs in ev.items() if not qs and slot not in derived}
    picked: list[dict] = []
    ordered = []
    for module in role.form["modules"]:
        for section in module["sections"]:
            for q in section["questions"]:
                ordered.append((module, section, q))
    for module, section, q in ordered:
        if q["id"] not in done and q.get("required"):
            picked.append({"question": q, "section": section, "module": module, "why": "required"})
    for module, section, q in ordered:
        closes = sorted(set(q.get("feeds", [])) & gaps)
        if q["id"] not in done and not q.get("required") and closes:
            picked.append({"question": q, "section": section, "module": module,
                           "why": "closes a gap: " + ", ".join(closes)})
    for module, section, q in ordered:
        if q["id"] not in done and all(p["question"]["id"] != q["id"] for p in picked):
            picked.append({"question": q, "section": section, "module": module, "why": "optional depth"})
    return picked[:limit]


def cmd_statement(args) -> int:
    print(statement_text(args.version))
    return 0


def cmd_start(args) -> int:
    role = cc.Role(cc.role_dir(args.role, args.role_dir))
    if not args.consented:
        print("error: read the consent statement (`interview.py statement`) to the person and pass "
              "--consented only once they agreed. No consent, no interview.", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.person):
        print("error: --person must be kebab-case (it becomes part of the pack id)", file=sys.stderr)
        return 2
    pack_id = f"{role.id.removeprefix('ceet-')}-{args.person}"
    root = cc.project_root(args.project)
    pack = Path(args.out).resolve() if args.out else cc.packs_dir(root) / pack_id
    if (pack / "private" / "answers.json").is_file() and not args.force:
        print(f"error: {pack} already has an interview; resume it with `next`, or pass --force", file=sys.stderr)
        return 1
    consent = {
        "statementVersion": cc.CONSENT_STATEMENT_VERSION,
        "subject": args.name,
        "basis": "consent",
        "recordedAt": today(),
        "uses": args.use,
        "storage": args.storage,
        "excludedUses": list(cc.EXCLUDED_USES),
    }
    if args.recorded_by:
        consent["recordedBy"] = args.recorded_by
    if args.shared_with:
        consent["sharedWith"] = args.shared_with
    if args.retention:
        consent["retention"] = args.retention
    state = {"schemaVersion": "1.0.0", "role": role.id, "formVersion": role.form["formVersion"],
             "packId": pack_id, "startedAt": today(), "consent": consent, "answers": {}, "skipped": {}}
    save_state(pack, state)
    write_gitignores(pack, args.storage)
    print(f"started {pack_id} in {pack}")
    print(f"form {role.form['formVersion']}: {len(role.questions())} questions; "
          f"next: `interview.py next --pack {pack_id}`")
    return 0


def read_text_arg(args) -> str:
    if args.text is not None:
        return args.text
    data = sys.stdin.read()
    if not data.strip():
        raise SystemExit("error: no answer text (pass --text or pipe it on stdin)")
    return data.rstrip("\n")


def cmd_answer(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    state = load_state(pack)
    role = cc.Role(cc.role_dir(state["role"], args.role_dir))
    if args.question not in role.question_ids():
        print(f"error: {args.question} is not a question of {role.id} form {role.form['formVersion']}", file=sys.stderr)
        return 2
    text = read_text_arg(args)
    entry = state["answers"].get(args.question)
    if args.probe:
        if entry is None:
            print(f"error: {args.question} has no answer yet to follow up on", file=sys.stderr)
            return 2
        entry.setdefault("followUps", []).append({"probe": args.probe, "text": text})
    else:
        if entry is not None and not args.replace:
            print(f"error: {args.question} is already answered; add a follow-up with --probe, "
                  "or pass --replace if the person restated it", file=sys.stderr)
            return 2
        state["answers"][args.question] = {"text": text, "answeredAt": today()}
    state.get("skipped", {}).pop(args.question, None)
    save_state(pack, state)
    print(f"recorded {args.question}{' follow-up' if args.probe else ''} ({len(text)} characters, verbatim)")
    return 0


def cmd_skip(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    state = load_state(pack)
    role = cc.Role(cc.role_dir(state["role"], args.role_dir))
    if args.question not in role.question_ids():
        print(f"error: {args.question} is not a question of {role.id}", file=sys.stderr)
        return 2
    state.setdefault("skipped", {})[args.question] = args.reason
    save_state(pack, state)
    print(f"skipped {args.question}: {args.reason}")
    return 0


def cmd_next(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    state = load_state(pack)
    role = cc.Role(cc.role_dir(state["role"], args.role_dir))
    picks = plan_next(role, state, args.limit)
    if args.json:
        print(json.dumps([{"id": p["question"]["id"], "section": p["section"]["title"],
                           "module": p["module"]["id"], "why": p["why"], "prompt": p["question"]["prompt"],
                           "probes": p["question"].get("probes", []), "kind": p["question"]["kind"],
                           "feeds": p["question"].get("feeds", [])} for p in picks], indent=2, ensure_ascii=False))
        return 0
    if not picks:
        print("every question is answered or skipped: synthesize the profile (references/interview-protocol.md)")
        return 0
    for p in picks:
        q = p["question"]
        print(f"{q['id']} [{p['module']['title']} / {p['section']['id']}. {p['section']['title']}] ({p['why']})")
        print(f"  {q['prompt']}")
        for probe in q.get("probes", []):
            print(f"  - probe: {probe}")
    return 0


def cmd_status(args) -> int:
    pack = resolve_pack(args.pack, args.project)
    state = load_state(pack)
    role = cc.Role(cc.role_dir(state["role"], args.role_dir))
    done = answered(state)
    skipped = set(state.get("skipped", {}))
    ev = evidence(role, state)
    derived = set(role.form.get("derived", {}))
    gaps = sorted(slot for slot, qs in ev.items() if not qs and slot not in derived)
    remaining = [q for q in role.questions() if q["id"] not in done | skipped]
    required_left = [q["id"] for q in remaining if q.get("required")]
    decisions = [q["id"] for q in role.questions() if "decisions" in q.get("captures", []) and q["id"] in done]
    report = {
        "packId": state["packId"], "role": role.id, "formVersion": state["formVersion"],
        "formVersionNow": role.form["formVersion"],
        "answered": len(done), "skipped": len(skipped), "questions": len(role.questions()),
        "requiredLeft": required_left, "minutesLeft": sum(q["minutes"] for q in remaining),
        "slotsWithEvidence": sum(1 for s, qs in ev.items() if qs), "slotsWithoutEvidence": gaps,
        "decisionQuestionsAnswered": decisions,
        "readyToSynthesize": not required_left,
    }
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(f"{report['packId']}: {report['answered']}/{report['questions']} answered, {report['skipped']} skipped, "
          f"~{report['minutesLeft']} min left")
    if report["formVersion"] != report["formVersionNow"]:
        print(f"note: answers were given to form {report['formVersion']}; the role's form is now "
              f"{report['formVersionNow']} (re-profile to move)")
    print(f"required questions left: {', '.join(required_left) or 'none'}")
    print(f"slots with evidence: {report['slotsWithEvidence']}; without: {len(gaps)}")
    for slot in gaps:
        print(f"  - {slot}")
    print(f"decision-capture answers: {len(decisions)}")
    print("ready to synthesize" if report["readyToSynthesize"] else "not ready: answer or skip the required questions")
    return 0


def cmd_elicit(args) -> int:
    """One section as an MCP elicitation `requestedSchema`: a flat object of strings."""
    role = cc.Role(cc.role_dir(args.role, args.role_dir))
    for module in role.form["modules"]:
        for section in module["sections"]:
            if section["id"] != args.section:
                continue
            props = {}
            for q in section["questions"]:
                description = q["prompt"]
                if q.get("probes"):
                    description += " (" + " ".join(q["probes"]) + ")"
                props[q["id"]] = {"type": "string", "title": q["id"], "description": description}
            schema = {"type": "object", "properties": props,
                      "required": [q["id"] for q in section["questions"] if q.get("required")]}
            print(json.dumps({"message": f"{role.title}: {section['id']}. {section['title']}",
                              "requestedSchema": schema}, indent=2, ensure_ascii=False))
            return 0
    print(f"error: {role.id} has no section {args.section!r}", file=sys.stderr)
    return 2


def main(argv=None) -> int:
    cc.configure_output()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", help="project root (default: $CLAUDE_PROJECT_DIR, git, cwd)")
    parser.add_argument("--role-dir", help="the role's folder, when it is not installed next to ceet-core")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("statement", help="print the consent statement")
    p.add_argument("--version", choices=cc.CONSENT_STATEMENT_VERSIONS, default=cc.CONSENT_STATEMENT_VERSION,
                   help="ceet-consent-2 is the statement for answers Fluxor online keeps")
    p.set_defaults(func=cmd_statement)
    p = sub.add_parser("start", help="record consent and create the interview state")
    p.add_argument("--role", required=True)
    p.add_argument("--person", required=True, help="kebab-case, part of the pack id")
    p.add_argument("--name", required=True, help="the name or alias the person wants in the pack")
    p.add_argument("--use", action="append", required=True, help="what the person agreed the pack is for (repeatable)")
    p.add_argument("--storage", choices=["local", "repository"], default="local")
    p.add_argument("--shared-with", action="append")
    p.add_argument("--retention")
    p.add_argument("--recorded-by")
    p.add_argument("--consented", action="store_true", help="the person heard the statement and agreed")
    p.add_argument("--out", help="pack folder (default: .harness/packs/<role>-<person>)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_start)
    for name, func in (("answer", cmd_answer), ("skip", cmd_skip), ("next", cmd_next), ("status", cmd_status)):
        p = sub.add_parser(name)
        p.add_argument("--pack", required=True)
        if name in ("answer", "skip"):
            p.add_argument("--question", required=True)
        if name == "answer":
            p.add_argument("--text")
            p.add_argument("--probe", help="record a follow-up to this probe instead of the main answer")
            p.add_argument("--replace", action="store_true")
        if name == "skip":
            p.add_argument("--reason", required=True)
        if name == "next":
            p.add_argument("--limit", type=int, default=3)
        if name in ("next", "status"):
            p.add_argument("--json", action="store_true")
        p.set_defaults(func=func)
    p = sub.add_parser("elicit", help="print one section as an MCP elicitation schema")
    p.add_argument("--role", required=True)
    p.add_argument("--section", required=True)
    p.set_defaults(func=cmd_elicit)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
