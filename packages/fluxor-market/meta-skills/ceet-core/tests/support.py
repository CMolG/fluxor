"""Test helpers: a synthetic pack built from a role's own form, so every role can be rendered and
validated end to end without a real interview."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
META = CORE.parent
SCRIPTS = CORE / "scripts"
sys.path.insert(0, str(SCRIPTS))
import ceet_common as cc  # noqa: E402

EXCLUDED = list(cc.EXCLUDED_USES)


def roles() -> list[Path]:
    """Every role folder that has a form.json."""
    return sorted(p for p in META.glob("ceet-*") if (p / "interview" / "form.json").is_file())


def run(script: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd, capture_output=True,
                          text=True, input=stdin)


def consent(subject: str = "Alex", basis: str = "consent", storage: str = "local") -> dict:
    return {"statementVersion": cc.CONSENT_STATEMENT_VERSION, "subject": subject, "basis": basis,
            "recordedAt": "2026-09-29", "uses": ["help me work the way I do"], "storage": storage,
            "excludedUses": list(EXCLUDED)}


def set_path(data: dict, path: str, value) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        data = data.setdefault(part, {})
    data[parts[-1]] = value


def synthetic_pack(role_dir: Path, packs: Path, person: str = "alex", with_decisions: bool = True) -> Path:
    """Answers for every question, a value citing a feeding question for every slot, two decisions."""
    role = cc.Role(role_dir)
    pack = packs / f"{role.id.removeprefix('ceet-')}-{person}"
    feeders: dict[str, str] = {}
    for q in role.questions():
        for slot in q.get("feeds", []):
            feeders.setdefault(slot, q["id"])
    answers = {q["id"]: {"text": f"My answer to {q['id']}, in my own words.", "answeredAt": "2026-09-29"}
               for q in role.questions()}
    state = {"schemaVersion": "1.0.0", "role": role.id, "formVersion": role.form["formVersion"],
             "packId": pack.name, "startedAt": "2026-09-29", "consent": consent(), "answers": answers, "skipped": {}}
    cc.write_json(pack / "private" / "answers.json", state)
    cc.write_text(pack / "private" / ".gitignore", "*\n")
    profile = {"schemaVersion": "2.0.0", "artifactType": "cognitive-profile", "role": role.id,
               "formVersion": role.form["formVersion"], "source": "interview", "name": "Alex",
               "meta": {"date": "2026-09-29", "version": "1.0.0"}, "consent": consent(),
               "identity": {}, "directives": {}}
    first, second = role.questions()[0]["id"], role.questions()[1]["id"]
    for slot in role.content_slots():
        if slot == "identity.contradictions":
            continue
        ref = feeders.get(slot, first)
        set_path(profile, slot, f"I handle {slot.split('.')[-1].replace('_', ' ')} my way. [{ref}]")
    profile["contradictions"] = [{"tension": "I say speed first but block slow reviews.", "question_a": first,
                                  "question_b": second, "resolution": "Context decides."}]
    cc.write_json(pack / "cognitive-profile.json", profile)
    if with_decisions:
        capturing = [q["id"] for q in role.questions() if "decisions" in q.get("captures", [])] or [first]
        decisions = {"schemaVersion": "1.0.0", "decisions": [
            {"id": "D1", "source": capturing[0], "domain": "review",
             "situation": "A migration renamed a column used by four services during a rolling deploy.",
             "cues": ["rolling deploy", "shared column"], "options": ["merge", "expand and contract"],
             "choice": "Asked for expand and contract.", "rationale": "Old readers break mid-deploy."},
            {"id": "D2", "source": capturing[-1], "domain": "planning",
             "situation": "A stakeholder asked to ship the pricing page without the legal review.",
             "choice": "Held the launch a day.", "rationale": "A wrong price is a promise."},
        ]}
        cc.write_json(pack / "examples" / "decisions.json", decisions)
    return pack


def simulated_pack(role_dir: Path, packs: Path, slug: str = "backend-public-figure", drop_row: bool = False,
                   unsourced: bool = False) -> Path:
    """A simulated pack of a made-up public figure: an evidence row for every directive (every fifth one
    `unknown`), `[E<n>]` citations, and the Simulation Notice in the evidence map as in every other file.
    Of the identity slots, `cognitive_signature` cites its own sourced row and the rest are not
    synthesized, the never-simulated ones as traits."""
    role = cc.Role(role_dir)
    pack = packs / slug
    rows = ["| Ref | Directive | Confidence | Source | Evidence |", "|---|---|---|---|---|"]
    profile = {"schemaVersion": "2.0.0", "artifactType": "cognitive-profile", "role": role.id,
               "formVersion": role.form["formVersion"], "source": "simulation", "name": "A Public Engineer",
               "consent": consent("A Public Engineer", "public-work"), "identity": {}, "directives": {}}
    for n, slot in enumerate(role.content_slots(), 1):
        sourced = slot == "identity.cognitive_signature" or (slot.startswith("directives.") and n % 5)
        if slot.startswith("identity.") and not sourced:
            note = cc.TRAIT_NOTE if slot in cc.NEVER_SIMULATED else cc.UNKNOWN_NOTE
            set_path(profile, slot, {"_status": "not_synthesized", "_note": note})
            continue
        if not sourced:
            rows.append(f"| E{n} | `{slot}` | unknown | — | No public evidence found. |")
            set_path(profile, slot, {"_status": "not_synthesized", "_note": cc.UNKNOWN_NOTE})
            continue
        source = "a talk, no link" if unsourced and n == 2 else f"https://example.com/talk-{n}"
        rows.append(f"| E{n} | `{slot}` | medium | {source} | A public talk on this topic. |")
        set_path(profile, slot, f"I work this way. [E{n}]")
    if drop_row:
        rows.remove(next(row for row in reversed(rows) if "`directives." in row))
    cc.write_text(pack / "evidence-map.md", "# Evidence Map\n\n" + cc.SIMULATION_NOTICE + "\n\n" + "\n".join(rows) + "\n")
    cc.write_json(pack / "cognitive-profile.json", profile)
    return pack


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
