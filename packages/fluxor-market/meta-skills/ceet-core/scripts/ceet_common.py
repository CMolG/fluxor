"""Shared helpers for the ceet-core scripts: locating the project and the packs, reading a role's
form, profile and templates, the slot syntax, a small JSON Schema validator, and the sanitizer that
every value passes through before it reaches a rendered file.

Standard library only (Python 3.9+). Not a command; the scripts next to it import it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
SCHEMAS = CORE / "schemas"

SLOT = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)\}")
QREF = re.compile(r"\bQ([1-9][0-9]*)\b")
REF_GROUP = re.compile(r"\[((?:Q[1-9][0-9]*|E[1-9][0-9]*|teachback)(?:\s*,\s*(?:Q[1-9][0-9]*|E[1-9][0-9]*|teachback))*)\]")
NOT_SYNTHESIZED = "not_synthesized"
PROFILE_SCHEMA_VERSION = "2.0.0"
PACK_SCHEMA_VERSION = "1.0.0"
CONSENT_STATEMENT_VERSION = "ceet-consent-1"
# The statement for an interview Fluxor online keeps on its servers (references/consent.md).
HOSTED_CONSENT_STATEMENT_VERSION = "ceet-consent-2"
CONSENT_STATEMENT_VERSIONS = (CONSENT_STATEMENT_VERSION, HOSTED_CONSENT_STATEMENT_VERSION)
SIMULATION_NOTICE = ("> **Simulation Notice:** This artifact is inferred from external evidence, not from a "
                     "first-person CEET interview. Treat it as a draft hypothesis, not as the person. Evidence "
                     "and confidence are in `evidence-map.md`.")
# What a simulated pack says about a slot it leaves empty: one of these reasons, never free text, which
# would carry a claim about the person past the evidence map (card://JAVA-549).
UNKNOWN_NOTE = "unknown: no evidence found."
TRAIT_NOTE = "never simulated: this slot describes a trait."
SIMULATION_NOTES = (UNKNOWN_NOTE, TRAIT_NOTE)
# Identity slots a simulation never fills: a value or a frustration is a motive, and a simulated pack
# infers none (ceet-impersonator's safety policy, "No inferred traits").
NEVER_SIMULATED = ("identity.core_values", "identity.frustration_triggers")
# Uses a pack may never serve, whatever the consent says: they would make the system high-risk under
# the EU AI Act (Annex III) and rarely have a valid legal basis in employment.
EXCLUDED_USES = ["performance-evaluation", "hiring-or-screening", "task-allocation-by-traits",
                 "promotion-or-termination", "monitoring"]


def configure_output() -> None:
    import sys
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


# ─── Locating things ─────────────────────────────────────────────────────────────────────────────

def project_root(explicit: str | None = None) -> Path:
    """`explicit`, else `$CLAUDE_PROJECT_DIR`, else the git top level, else the current directory."""
    if explicit:
        return Path(explicit).resolve()
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        if out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        pass
    return Path.cwd().resolve()


def harness_dir(root: Path) -> Path:
    harness = os.environ.get("HARNESS_DIR")
    return (root / harness).resolve() if harness else root / ".harness"


def packs_dir(root: Path) -> Path:
    return harness_dir(root) / "packs"


def fidelity_dir(root: Path, pack_id: str) -> Path:
    """Held-out decisions live outside the pack, so nothing that loads the pack can see them."""
    return harness_dir(root) / "fidelity" / pack_id


def skills_dir() -> Path:
    """The folder ceet-core is installed in: the roles are its siblings."""
    return CORE.parent


def role_dir(role: str, explicit: str | None = None) -> Path:
    folder = Path(explicit).resolve() if explicit else skills_dir() / role
    if not (folder / "interview" / "form.json").is_file():
        raise SystemExit(f"error: {folder} is not a CEET role (no interview/form.json)")
    return folder


# ─── JSON ────────────────────────────────────────────────────────────────────────────────────────

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(answers: dict) -> str:
    """The first 12 hex characters of the SHA-256 of the answers, sorted keys, no whitespace."""
    canonical = json.dumps(answers, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_text(canonical)[:12]


# ─── A role ──────────────────────────────────────────────────────────────────────────────────────

class Role:
    """A `ceet-<role>` meta-skill: its form, the slots its profile declares, its templates."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.id = folder.name
        self.form = read_json(folder / "interview" / "form.json")
        self.profile_template = folder / "templates" / "cognitive-profile.md"
        self.slots = set(SLOT.findall(self.profile_template.read_text(encoding="utf-8")))
        self.name_slot = self.form.get("nameSlot", "")
        self.title = self.form.get("title", self.id)

    def questions(self) -> list[dict]:
        return [q for m in self.form["modules"] for s in m["sections"] for q in s["questions"]]

    def question_ids(self) -> set[str]:
        return {q["id"] for q in self.questions()}

    def templates(self) -> list[Path]:
        base = self.folder / "templates"
        return sorted(p for p in base.rglob("*") if p.is_file() and p != self.profile_template)

    def directive_slots(self) -> list[str]:
        return sorted(s for s in self.slots if s.startswith("directives."))

    def content_slots(self) -> list[str]:
        """Every slot synthesis fills (not the header, not the name)."""
        return sorted(s for s in self.slots if not s.startswith("meta.") and s != self.name_slot)


# ─── Profile values ──────────────────────────────────────────────────────────────────────────────

def lookup(data: dict, path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def is_not_synthesized(value: Any) -> bool:
    return isinstance(value, dict) and value.get("_status") == NOT_SYNTHESIZED


def refs(text: str) -> list[str]:
    """Every reference in `[Q5, Q12]`, `[E3]` or `[teachback]` groups, in order, without duplicates."""
    found: list[str] = []
    for group in REF_GROUP.findall(text or ""):
        for item in re.split(r"\s*,\s*", group):
            if item not in found:
                found.append(item)
    return found


# ─── Sanitizing ─────────────────────────────────────────────────────────────────────────────────

INVISIBLE = {chr(c) for c in list(range(0x200B, 0x2010)) + list(range(0x202A, 0x202F))
             + list(range(0x2060, 0x2065)) + list(range(0x2066, 0x206A)) + [0xFEFF, 0x00AD, 0x180E]}
INSTRUCTION_MARKERS = [
    re.compile(r"(?i)\b(ignore|disregard|forget)\b[^.\n]{0,40}\b(previous|prior|above|earlier|all)\b[^.\n]{0,20}\b(instructions?|rules?|prompts?|directives?)"),
    re.compile(r"(?i)\byou are now\b"),
    re.compile(r"(?i)\b(system|developer)\s*(prompt|message)\s*:"),
    re.compile(r"(?i)<\|?/?\s*(system|assistant|user|im_start|im_end|instructions?)\s*\|?>"),
    re.compile(r"(?i)\bdo not (tell|inform|show) the (user|person|human)\b"),
]
# Words that suggest a special category of personal data (GDPR Art. 9). Deliberately phrases, not
# single ambiguous words: "race condition", "union type" and "culture diagnosis" must pass.
SPECIAL_CATEGORY = re.compile(
    r"(?i)\b(ethnic(ity)?|racial|religio(n|us)|church|mosque|synagogue|political (party|views?|affiliation)|"
    r"trade union|union member(ship)?|sexual orientation|sex life|gay|lesbian|bisexual|transgender|"
    r"diagnosed with|(medical|clinical|psychiatric) diagnosis|disorder|adhd|autis(m|tic)|dyslexi[ac]|depression|anxiety|bipolar|medication|"
    r"therap(y|ist)|chronic (illness|pain)|disabilit(y|ies)|pregnan(t|cy)|mental health|health condition)\b")


def strip_invisible(value: str) -> str:
    return "".join(ch for ch in value if ch not in INVISIBLE)


def sanitize(value: str) -> tuple[str, list[str]]:
    """Strip invisible and control characters and neutralize markup that could act as an instruction
    to a tool reading the rendered file. Returns the clean text and what was changed or flagged."""
    notes: list[str] = []
    stripped = strip_invisible(value)
    if stripped != value:
        notes.append(f"removed {len(value) - len(stripped)} invisible or bidirectional character(s)")
    cleaned = "".join(ch for ch in stripped if ch in "\n\t" or unicodedata.category(ch) != "Cc")
    if cleaned != stripped:
        notes.append("removed control character(s)")
    text = cleaned
    if "<!--" in text or "-->" in text:
        text = text.replace("<!--", "&lt;!--").replace("-->", "--&gt;")
        notes.append("escaped an HTML comment (hidden text)")
    # A line starting with @ is an import in CLAUDE.md-style files: it would pull a file into context.
    new_text = re.sub(r"(?m)^(\s*)@", r"\1\\@", text)
    if new_text != text:
        notes.append("escaped a line starting with @ (an import in some tools)")
        text = new_text
    for marker in INSTRUCTION_MARKERS:
        if marker.search(text):
            notes.append(f"instruction-like text: {marker.search(text).group(0)!r} (review before approving)")
    return text, notes


def special_category_hits(text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in SPECIAL_CATEGORY.finditer(text or "")})


# ─── A small JSON Schema validator (the subset the schemas in ../schemas use) ───────────────────

def validate_schema(instance: Any, schema_name: str) -> list[str]:
    cache: dict[str, dict] = {}

    def load(name: str) -> dict:
        if name not in cache:
            cache[name] = read_json(SCHEMAS / name)
        return cache[name]

    def resolve(ref: str, doc: str) -> tuple[dict, str]:
        name, _, pointer = ref.partition("#")
        name = name or doc
        node: Any = load(name)
        for part in [p for p in pointer.split("/") if p]:
            node = node[part]
        return node, name

    types = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
    errors: list[str] = []

    def is_type(value: Any, expected: str) -> bool:
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return isinstance(value, types[expected])

    def check(value: Any, schema: dict, doc: str, path: str) -> None:
        if "$ref" in schema:
            target, target_doc = resolve(schema["$ref"], doc)
            check(value, target, target_doc, path)
        for sub in schema.get("allOf", []):
            check(value, sub, doc, path)
        if "anyOf" in schema:
            branches = []
            for sub in schema["anyOf"]:
                before = len(errors)
                check(value, sub, doc, path)
                branches.append(errors[before:])
                del errors[before:]
            if all(branches):
                errors.append(f"{path}: matches none of the allowed shapes ({branches[0][0]})")
        if "const" in schema and value != schema["const"]:
            errors.append(f"{path}: must be {json.dumps(schema['const'])}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: {json.dumps(value)} is not one of {schema['enum']}")
        expected = schema.get("type")
        if expected:
            kinds = expected if isinstance(expected, list) else [expected]
            if not any(is_type(value, k) for k in kinds):
                errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
                return
        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                errors.append(f"{path}: shorter than {schema['minLength']} characters")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errors.append(f"{path}: {json.dumps(value)} does not match {schema['pattern']}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: below the minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: above the maximum {schema['maximum']}")
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
            for i, item in enumerate(value):
                if "items" in schema:
                    check(item, schema["items"], doc, f"{path}[{i}]")
        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    errors.append(f"{path}: missing required key {key!r}")
            props = schema.get("properties", {})
            patterns = schema.get("patternProperties", {})
            for key, item in value.items():
                matched = [sub for pattern, sub in patterns.items() if re.search(pattern, key)]
                for sub in matched:
                    check(item, sub, doc, f"{path}.{key}")
                if key in props:
                    check(item, props[key], doc, f"{path}.{key}")
                elif matched:
                    continue
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{path}: unknown key {key!r}")
                elif isinstance(schema.get("additionalProperties"), dict):
                    check(item, schema["additionalProperties"], doc, f"{path}.{key}")

    check(instance, load(schema_name), schema_name, "$")
    return errors
