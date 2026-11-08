#!/usr/bin/env python3
"""The marketplace's build tool: this repository is the single source of truth for it.

  marketplace.py validate            schemas, references, SKILL.md front matter, config examples, lock,
                                     inventory, language
  marketplace.py list [KIND]         the catalog, one atom per line
  marketplace.py inventory [--check] write (or check) market/inventory.json, the Fluxor projection
  marketplace.py forms [--check]     render (or check) each meta-skill's form.json into its questions.md
  marketplace.py lock [--only ID]    record every atom's version and content hash (or only some)
  marketplace.py build --out DIR     the publishable bundle: DIR/index.json + DIR/blobs/<sha256>
                                     + DIR/compatibility.json
  marketplace.py install [--check]   install a project's selection (<harness>/harness.json) into its
                                     harness, or check the installed copies for drift (installer.py)

Every atom has a manifest: `market/<kind>s/<id>.json` next to its `<id>.md`, `skills/<id>/skill.json`
(or `meta-skills/<id>/skill.json`) next to its SKILL.md, and `market/engine.json` for the runtime
files. A hook's `market/hooks/<id>.json` sits next to its scripts (`<id>.sh`, `<id>.ps1`) and its
fallback `<id>.md`. A preset's `market/presets/<id>.json` is a manifest with no files, listing the
skills and hooks it adds. The manifest format is defined once, in `schemas/*.schema.json`; this tool validates against
those files, so the pipeline that seeds a database can use the same schemas without this tool.

Standard library only (Python 3.9+), so a deployment pipeline can run it on a bare image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compatibility  # noqa: E402
import english  # noqa: E402
import fluxor_sync  # noqa: E402
import forms  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
MARKET = ROOT / "market"
SKILLS = ROOT / "skills"
# Meta-skills are skills too (kind `skill`, installed under `skills/<id>/`); the repository keeps
# them in their own folder so the family that depends on a form stays visible.
META_SKILLS = ROOT / "meta-skills"
LOCK = ROOT / "marketplace.lock.json"
INVENTORY = MARKET / "inventory.json"
CONFIG = ROOT / "marketplace.json"

MARKET_KINDS = {"role": "roles", "mod": "mods", "step": "steps", "flow": "flows"}
# A hook (card://JAVA-673) lives in `market/hooks/`, but it is not a MARKET_KINDS atom: Fluxor's
# inventory has no hooks, and its files are scripts next to a fallback, not one prompt.
HOOKS = MARKET / "hooks"
HOOK_SCRIPTS = ("sh", "ps1")
# The events fluxor-sync can wire: every client's neutral names, plus Claude Code's status line.
HOOK_EVENTS = sorted({event for events in fluxor_sync.EVENTS.values() for event in events} | {fluxor_sync.STATUS_LINE})
# A preset (card://JAVA-161) is a manifest with no files that names the skills and hooks a project
# adds in one step. Those are what the catalog seeds and a snapshot renders; a meta-skill needs a
# person's interview first, and a preset inside a preset would make applying one recursive.
PRESETS = MARKET / "presets"
PRESET_ITEM_KINDS = ("skill", "hook")
# Fluxor's MarketInventory, per kind and in its key order. The projection keeps exactly these keys.
FLUXOR_KEYS = {
    "flow": ["betterOn", "recommendedComplexity", "cost", "icon", "iconLibrary", "description", "tags", "usableBy",
             "noteTypes", "steps"],
    "role": ["icon", "iconLibrary", "description", "tags", "domains", "betterOn", "color", "palette", "toolTier"],
    "mod": ["icon", "iconLibrary", "description", "tags", "incompatibleWith", "exclusiveGroup", "domains", "runtime"],
    "step": ["icon", "iconLibrary", "description", "tags"],
}
# Fluxor's MarketFlowStep, in its key order. Catalog-only keys such as `stepRef` are dropped.
FLUXOR_FLOW_STEP_KEYS = ["id", "prompt", "roleId", "modIds", "prevStepIds", "loopBackTo", "noteBindings"]
AUTHORING_DOCS = {"AGENTS.md", "CLAUDE.md"}
ALWAYS_EXCLUDED = ["**/__pycache__/**", "**/*.pyc", "**/.DS_Store"]
TEXT_SUFFIXES = {".md", ".py", ".json", ".sh", ".cjs", ".mjs", ".js", ".ts", ".tsx", ".jsx", ".html",
                 ".css", ".yml", ".yaml", ".toml", ".txt", ".tsv", ".csv"}
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")
# A market atom's config schema and example sit next to its manifest as `<id>.config.schema.json`
# and `<id>.config.example.json`; they are companions of that atom, not manifests.
CONFIG_COMPANION = re.compile(r"\.config\.(schema|example)\.json$")
# A slot in a meta-skill's profile or templates: `{name}`, `{identity.core_values}`,
# `{directives.code_review.philosophy}`. JSON in a template (`{"a": 1}`) never matches.
SLOT = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)\}")
# Board roles (card://JAVA-327): the roles that work a card on a board, each in exactly one phase.
# A phase has ONE palette, so a role's color says which phase it works in; the text passes WCAG AA
# on the background and on the hover.
BOARD_PHASES = {
    "refine": {"background": "B9A3E6", "text": "1A1A1A", "accents": "4B2F96", "hover": "A88FDB"},
    "action": {"background": "7CC9A6", "text": "1A1A1A", "accents": "1B5E44", "hover": "69B994"},
    "ready": {"background": "F0C467", "text": "1A1A1A", "accents": "7A4E00", "hover": "E2B24F"},
    "review": {"background": "8FB9EA", "text": "1A1A1A", "accents": "1C4880", "hover": "7BA7DC"},
    "deploy": {"background": "EE9A8C", "text": "1A1A1A", "accents": "8C2418", "hover": "E3857A"},
}
# A role's toolTier, narrowest first: what a session that works the role may do with its tools.
TOOL_TIERS = ["read", "comment", "write"]
# The most a board role may be given in each phase (card://JAVA-1445): a session that only reads
# and checks never writes the tree. Refine, ready and review sessions read and comment; a build or a
# release writes.
BOARD_TOOL_CEILING = {"refine": "comment", "ready": "comment", "review": "comment", "action": "write",
                      "deploy": "write"}
# The phase contract leads (it is what the role is on the board for); the references sit next to
# the quality standards they justify; Boundaries close, as in every other role.
BOARD_SECTIONS = ["Phase Contract", "Expertise", "Decision-Making Principles", "Quality Standards",
                  "Reference Baseline", "Interaction Style", "Boundaries"]
BOARD_LABELS = {"Phase Contract": ["Phase", "Mission", "Must achieve", "Must not"],
                "Interaction Style": ["Before acting", "Deliverable shape", "Pushback", "Voice"]}
BOARD_MAX_WORDS = 900


# ─── JSON Schema (the subset the repository's schemas use) ──────────────────────────────────────

class SchemaStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.cache: dict[str, dict] = {}

    def load(self, name: str) -> dict:
        if name not in self.cache:
            self.cache[name] = json.loads((self.directory / name).read_text(encoding="utf-8"))
        return self.cache[name]

    def resolve(self, ref: str, current: str) -> tuple[dict, str]:
        doc, _, pointer = ref.partition("#")
        doc = doc or current
        node = self.load(doc)
        for part in [p for p in pointer.split("/") if p]:
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node, doc

    def validate(self, instance, schema_name: str) -> list[str]:
        errors: list[str] = []
        self._check(instance, self.load(schema_name), schema_name, "$", errors)
        return errors

    def _check(self, value, schema: dict, doc: str, path: str, errors: list[str]) -> None:
        if "$ref" in schema:
            target, target_doc = self.resolve(schema["$ref"], doc)
            self._check(value, target, target_doc, path, errors)
        for sub in schema.get("allOf", []):
            self._check(value, sub, doc, path, errors)
        if "const" in schema and value != schema["const"]:
            errors.append(f"{path}: must be {json.dumps(schema['const'])}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: {json.dumps(value)} is not one of {schema['enum']}")
        expected = schema.get("type")
        if expected and not _is_type(value, expected):
            errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
            return
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(f"{path}: shorter than {schema['minLength']} characters")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(f"{path}: longer than {schema['maxLength']} characters")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errors.append(f"{path}: {json.dumps(value)} does not match {schema['pattern']}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: below the minimum {schema['minimum']}")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errors.append(f"{path}: allows at most {schema['maxItems']} item(s)")
            if schema.get("uniqueItems"):
                seen = [json.dumps(v, sort_keys=True) for v in value]
                if len(seen) != len(set(seen)):
                    errors.append(f"{path}: items must be unique")
            if "items" in schema:
                for i, item in enumerate(value):
                    self._check(item, schema["items"], doc, f"{path}[{i}]", errors)
        if isinstance(value, dict):
            if "minProperties" in schema and len(value) < schema["minProperties"]:
                errors.append(f"{path}: needs at least {schema['minProperties']} key(s)")
            for key in schema.get("required", []):
                if key not in value:
                    errors.append(f"{path}: missing required key {key!r}")
            props = schema.get("properties", {})
            patterns = schema.get("patternProperties", {})
            for key, item in value.items():
                matched = [sub for pattern, sub in patterns.items() if re.search(pattern, key)]
                for sub in matched:
                    self._check(item, sub, doc, f"{path}.{key}", errors)
                if key in props:
                    self._check(item, props[key], doc, f"{path}.{key}", errors)
                elif matched:
                    continue
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{path}: unknown key {key!r}")
                elif isinstance(schema.get("additionalProperties"), dict):
                    self._check(item, schema["additionalProperties"], doc, f"{path}.{key}", errors)


# What SchemaStore checks, plus annotations it may ignore. A config schema that uses anything else
# (anyOf, format, maxItems...) would be enforced by a full validator and silently skipped here.
SCHEMA_KEYWORDS = {"type", "enum", "const", "pattern", "required", "properties", "patternProperties",
                   "additionalProperties", "items", "minItems", "maxItems", "minProperties", "uniqueItems", "minLength", "maxLength",
                   "minimum", "$ref", "allOf", "$defs"}
SCHEMA_ANNOTATIONS = {"$schema", "$id", "$comment", "title", "description", "default", "examples",
                      "deprecated", "readOnly", "writeOnly"}
JSON_TYPES = {"object", "array", "string", "boolean", "integer", "number", "null"}


def unsupported_keywords(schema, path: str = "$") -> list[str]:
    """Keywords outside the subset, as `path: keyword` strings."""
    found: list[str] = []
    if not isinstance(schema, dict):
        return found if isinstance(schema, bool) else [f"{path}: a schema must be an object or a boolean"]
    for key, value in schema.items():
        if key not in SCHEMA_KEYWORDS and key not in SCHEMA_ANNOTATIONS:
            found.append(f"{path}: unsupported keyword {key!r}")
        for pattern in ([value] if key == "pattern" else list(value) if key == "patternProperties" else []):
            try:
                re.compile(pattern)
            except (re.error, TypeError) as exc:
                found.append(f"{path}.{key}: invalid regular expression {pattern!r} ({exc})")
        if key == "type":
            for name in value if isinstance(value, list) else [value]:
                if name not in JSON_TYPES:
                    found.append(f"{path}.type: unknown type {name!r}")
        if key in ("properties", "patternProperties", "$defs") and isinstance(value, dict):
            for name, sub in value.items():
                found += unsupported_keywords(sub, f"{path}.{key}.{name}")
        elif key in ("items", "additionalProperties"):
            found += unsupported_keywords(value, f"{path}.{key}")
        elif key == "allOf" and isinstance(value, list):
            for i, sub in enumerate(value):
                found += unsupported_keywords(sub, f"{path}.allOf[{i}]")
    return found


def _is_type(value, expected) -> bool:
    kinds = expected if isinstance(expected, list) else [expected]
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "null": lambda v: v is None,
    }
    return any(checks[k](value) for k in kinds)


# ─── The catalog ────────────────────────────────────────────────────────────────────────────────

class Atom:
    def __init__(self, kind: str, manifest_path: Path, manifest: dict):
        self.kind = kind
        self.manifest_path = manifest_path
        self.manifest = manifest
        self.id = manifest.get("id", "")
        self.version = manifest.get("version", "")

    @property
    def expected_id(self) -> str:
        if self.kind == "skill":
            return self.manifest_path.parent.name
        if self.kind == "engine":
            return self.id  # market/engine.json names its engine in the manifest
        return self.manifest_path.stem

    @property
    def content_path(self) -> Path | None:
        if self.kind in MARKET_KINDS or self.kind == "hook":
            return self.manifest_path.with_suffix(".md")
        if self.kind == "skill":
            return self.manifest_path.parent / "SKILL.md"
        return None

    def rel(self, path: Path) -> str:
        return path.relative_to(ROOT).as_posix()


def tracked_files() -> set[str] | None:
    """Git-tracked files (plus untracked, not ignored ones), so stray local files never ship."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return {p for p in out.stdout.decode("utf-8").split("\0") if p and (ROOT / p).is_file()}


def git_executables() -> set[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=ROOT, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return set()
    result = set()
    for entry in out.stdout.decode("utf-8").split("\0"):
        if entry.startswith("100755 "):
            result.add(entry.split("\t", 1)[1])
    return result


def is_executable(rel: str, git_exec: set[str]) -> bool:
    """The git index decides for tracked files: filesystems mounted from Windows report every file
    as executable. Untracked files fall back to the filesystem, except on Windows."""
    if rel in _tracked_cache():
        return rel in git_exec
    return os.name != "nt" and os.access(ROOT / rel, os.X_OK)


_TRACKED: set[str] | None = None


def _tracked_cache() -> set[str]:
    global _TRACKED
    if _TRACKED is None:
        try:
            out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
            _TRACKED = {p for p in out.stdout.decode("utf-8").split("\0") if p}
        except (OSError, subprocess.CalledProcessError):
            _TRACKED = set()
    return _TRACKED


def load_catalog() -> tuple[list[Atom], list[str]]:
    atoms: list[Atom] = []
    errors: list[str] = []

    def read(kind: str, path: Path) -> None:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT).as_posix()}: unreadable manifest ({exc})")
            return
        atoms.append(Atom(kind, path, manifest))

    for kind, folder in MARKET_KINDS.items():
        for path in sorted((MARKET / folder).glob("*.json")):
            if not CONFIG_COMPANION.search(path.name):
                read(kind, path)
    for path in sorted(HOOKS.glob("*.json")):
        read("hook", path)
    for path in sorted(PRESETS.glob("*.json")):
        read("preset", path)
    for folder in (SKILLS, META_SKILLS):
        for path in sorted(folder.glob("*/skill.json")):
            read("skill", path)
    engine = MARKET / "engine.json"
    if engine.is_file():
        read("engine", engine)
    return atoms, errors


def glob_regex(pattern: str) -> re.Pattern:
    """Gitignore-style globs: `**/` spans any number of directories, `*` stays within one."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(f"^{out}$")


def glob_match(path: str, patterns: list[str]) -> bool:
    return any(glob_regex(p).match(path) for p in patterns)


def excluded(rel_in_atom: str, patterns: list[str]) -> bool:
    return glob_match(rel_in_atom, patterns)


def atom_files(atom: Atom, tracked: set[str] | None) -> list[tuple[str, str]]:
    """(repository path, install path relative to the harness directory), sorted."""
    pairs: list[tuple[str, str]] = []
    if atom.kind in MARKET_KINDS:
        md = atom.content_path
        if md and md.is_file():
            pairs.append((atom.rel(md), f"market/{MARKET_KINDS[atom.kind]}/{atom.id}.md"))
        config = atom.manifest.get("config")
        for key in ("schema", "example"):
            name = config.get(key) if isinstance(config, dict) else None
            path = atom.manifest_path.parent / name if isinstance(name, str) and name else None
            if path and path.is_file() and "/" not in name and "\\" not in name:
                pairs.append((atom.rel(path), f"market/{MARKET_KINDS[atom.kind]}/{name}"))
    elif atom.kind == "hook":
        for suffix in ("md", *HOOK_SCRIPTS):
            path = atom.manifest_path.with_suffix(f".{suffix}")
            if path.is_file():
                pairs.append((atom.rel(path), f"market/hooks/{path.name}"))
    elif atom.kind == "engine":
        for rel in atom.manifest.get("files", []):
            pairs.append((rel, f"market/{PurePosixPath(rel).name}"))
    elif atom.kind == "skill":
        folder = atom.manifest_path.parent
        patterns = ALWAYS_EXCLUDED + atom.manifest.get("install", {}).get("exclude", [])
        candidates = sorted(tracked) if tracked is not None else sorted(
            p.relative_to(ROOT).as_posix() for p in folder.rglob("*") if p.is_file())
        prefix = atom.rel(folder) + "/"
        for rel in candidates:
            if not rel.startswith(prefix):
                continue
            inner = rel[len(prefix):]
            if inner == "skill.json" or excluded(inner, patterns):
                continue
            pairs.append((rel, f"skills/{atom.id}/{inner}"))
    return sorted(pairs, key=lambda p: p[1])


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_manifest(manifest: dict) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "$schema"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_content(rel: str) -> bytes:
    """A file's bytes as git stores them. `.gitattributes` makes every text file LF in the
    repository, but a checkout (or an editor on Windows) can leave CRLF in the working tree; hashing
    those bytes would give the same content a different hash on another machine. Text is detected
    the way git's `text=auto` does it: no NUL byte in the first 8000 bytes."""
    data = (ROOT / rel).read_bytes()
    if b"\0" not in data[:8000]:
        data = data.replace(b"\r\n", b"\n")
    return data


def describe_files(atom: Atom, tracked, git_exec) -> list[dict]:
    files = []
    for rel, install in atom_files(atom, tracked):
        data = read_content(rel)
        files.append({"path": install, "source": rel, "sha256": sha256_bytes(data), "size": len(data),
                      "executable": is_executable(rel, git_exec)})
    return files


def atom_hash(atom: Atom, files: list[dict]) -> str:
    lines = [f"manifest {sha256_bytes(canonical_manifest(atom.manifest))}"]
    lines += [f"{f['path']} {f['sha256']} {'x' if f['executable'] else '-'}" for f in files]
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


# ─── Front matter ───────────────────────────────────────────────────────────────────────────────

def front_matter(text: str) -> dict[str, str]:
    """The `key: value` pairs of a SKILL.md header, including folded (`>-`, `>`, `|`) values."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        i += 1
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value in (">", ">-", "|", "|-"):
            block = []
            while i < len(lines) and lines[i].strip() != "---" and (lines[i].startswith(" ") or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if value.startswith("|") else " "
            value = joiner.join(b for b in block if b)
        result[key] = value.strip().strip('"').strip("'")
    return result


# ─── Projection for Fluxor ──────────────────────────────────────────────────────────────────────

def fluxor_inventory(atoms: list[Atom]) -> dict:
    inventory = {"flows": [], "roles": [], "mods": [], "steps": []}
    for atom in sorted(atoms, key=lambda a: a.id):
        if atom.kind not in MARKET_KINDS:
            continue
        card = {"name": atom.id}
        for key in FLUXOR_KEYS[atom.kind]:
            if key in atom.manifest:
                card[key] = atom.manifest[key]
        if atom.kind == "flow" and isinstance(card.get("steps"), list):
            card["steps"] = [{k: step[k] for k in FLUXOR_FLOW_STEP_KEYS if k in step}
                             for step in card["steps"] if isinstance(step, dict)]
        inventory[MARKET_KINDS[atom.kind]].append(card)
    return inventory


def write_lf(path: Path, text: str) -> None:
    """Write UTF-8 with LF line endings (Path.write_text gained `newline` only in Python 3.10)."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def dump_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ─── Validation ─────────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def config_findings(atom: Atom) -> list[str]:
    """The per-project config an atom declares: its schema is a JSON object schema that stays within
    what SchemaStore checks, and its example validates against it. A skill's paths are relative to
    its folder; a market atom's are `<id>.config.schema.json` / `<id>.config.example.json` next to
    its manifest, which is where they install."""
    config = atom.manifest.get("config")
    if not isinstance(config, dict):
        return []
    where = atom.rel(atom.manifest_path)
    errors: list[str] = []
    loaded: dict[str, tuple[Path, object]] = {}
    for key in ("schema", "example"):
        rel = config.get(key)
        if not isinstance(rel, str) or not rel:
            continue
        if atom.kind in MARKET_KINDS and rel != f"{atom.id}.config.{key}.json":
            errors.append(f"{where}: config.{key} must be {atom.id}.config.{key}.json, next to the manifest")
            continue
        path = atom.manifest_path.parent / rel
        if not path.is_file():
            errors.append(f"{where}: config.{key} {rel!r} does not exist")
            continue
        try:
            loaded[key] = (path, json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            errors.append(f"{atom.rel(path)}: not valid JSON ({exc})")
    if "schema" not in loaded:
        return errors
    schema_path, schema = loaded["schema"]
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return errors + [f"{atom.rel(schema_path)}: a config schema needs a top-level \"type\": \"object\""]
    unsupported = unsupported_keywords(schema)
    if unsupported:
        return errors + [f"{atom.rel(schema_path)} {u}" for u in unsupported]
    if "example" in loaded:
        example_path, example = loaded["example"]
        store = SchemaStore(schema_path.parent)
        store.cache[schema_path.name] = schema
        try:
            errors += [f"{atom.rel(example_path)} {e}" for e in store.validate(example, schema_path.name)]
        except (KeyError, TypeError, OSError, ValueError) as exc:
            errors.append(f"{atom.rel(schema_path)}: cannot be applied ({exc!r})")
    return errors


def form_findings(atom: Atom, store: SchemaStore | None = None) -> list[str]:
    """A meta-skill's form: `packaging: meta` and a `form` block go together, a meta-skill lives in
    `meta-skills/`, the files the form names exist inside the skill folder, the form is a
    `form.json` valid against `schemas/form.schema.json` with its Markdown rendering up to date, and
    every template uses only slots its profile declares, so a rendered pack can never keep a slot
    nobody was asked to fill. With a profile, the form's coverage is checked too (tools/forms.py):
    every slot fed by a question, every question feeding a slot, every slot rendered or marked
    profile-only."""
    manifest = atom.manifest
    where = atom.rel(atom.manifest_path)
    form = manifest.get("form")
    if manifest.get("packaging") != "meta":
        return [f"{where}: a form block needs packaging 'meta'"] if form is not None else []
    errors: list[str] = []
    folder = atom.manifest_path.parent
    if folder.parent != META_SKILLS:
        errors.append(f"{where}: a meta-skill lives in meta-skills/")
    if not isinstance(form, dict):
        return errors + [f"{where}: packaging 'meta' needs a form block"]
    paths: dict[str, Path] = {}
    for key in ("questions", "profile", "templates"):
        rel = form.get(key)
        if not isinstance(rel, str) or not rel:
            continue
        if ".." in PurePosixPath(rel).parts or PurePosixPath(rel).is_absolute():
            errors.append(f"{where}: form.{key} {rel!r} must stay inside the skill folder")
            continue
        paths[key] = folder / rel
    data = None
    if "questions" in paths:
        qpath = paths["questions"]
        if not qpath.is_file():
            errors.append(f"{where}: form.questions {form['questions']!r} does not exist")
        elif qpath.suffix != ".json":
            errors.append(f"{where}: form.questions must be a form.json (schemas/form.schema.json)")
        else:
            data, load_errors = forms.load(qpath)
            errors += [f"{atom.rel(qpath)}: {e}" for e in load_errors]
    if data is not None:
        qpath = paths["questions"]
        store = store or SchemaStore(SCHEMAS)
        schema_errors = store.validate(data, "form.schema.json")
        errors += [f"{atom.rel(qpath)} {e}" for e in schema_errors]
        errors += [f"{atom.rel(qpath)}: {e}" for e in forms.structure_findings(data, atom.id)]
        markdown = qpath.with_name("questions.md")
        if not schema_errors:
            current = markdown.read_text(encoding="utf-8") if markdown.is_file() else ""
            if current.replace("\r\n", "\n") != forms.render_markdown(data):
                errors.append(f"{atom.rel(markdown)} is out of date: run `tools/marketplace.py forms`")
    if ("profile" in form) != ("templates" in form):
        return errors + [f"{where}: form.profile and form.templates go together"]
    if "profile" not in paths or "templates" not in paths:
        return errors
    profile, templates = paths["profile"], paths["templates"]
    if not profile.is_file():
        return errors + [f"{where}: form.profile {form['profile']!r} does not exist"]
    if not templates.is_dir():
        return errors + [f"{where}: form.templates {form['templates']!r} is not a folder"]
    try:
        declared = set(SLOT.findall(profile.read_text(encoding="utf-8")))
    except UnicodeDecodeError:
        return errors + [f"{atom.rel(profile)}: not UTF-8"]
    if not declared:
        errors.append(f"{atom.rel(profile)}: declares no {{slot}} for the answers to fill")
    rendered: set[str] = set()
    for path in sorted(p for p in templates.rglob("*") if p.is_file() and p != profile):
        raw = path.read_bytes()
        if b"\0" in raw[:8000]:
            continue  # binary (an image, a font): no slots, rendered as is
        try:
            used = set(SLOT.findall(raw.decode("utf-8")))
        except UnicodeDecodeError:
            errors.append(f"{atom.rel(path)}: not UTF-8")
            continue
        rendered |= used
        for slot in sorted(used - declared):
            errors.append(f"{atom.rel(path)}: uses {{{slot}}}, which {form['profile']} does not declare")
    if data is not None:
        qpath = paths["questions"]
        errors += [f"{atom.rel(qpath)}: {e}" for e in forms.coverage_findings(data, declared, rendered)]
    return errors


def board_role_findings(atom: Atom) -> list[str]:
    """A role tagged `board` follows the board-role template (.harness/rules/projects/
    fluxor-market-atoms.md § Board roles): one phase tag, the phase's palette, no model hint, the
    seven prompt sections in order with their labels, and a word ceiling."""
    m = atom.manifest
    where = atom.rel(atom.manifest_path)
    tags = m.get("tags", [])
    phases = [t for t in tags if t.startswith("phase-")]
    if "board" not in tags:
        return [f"{where}: tag {t!r} is only for board roles (tag 'board')" for t in phases]
    if atom.kind != "role":
        return [f"{where}: only a role can be a board role"]
    errors = []
    names = [p[len("phase-"):] for p in phases]
    if len(names) != 1 or names[0] not in BOARD_PHASES:
        errors.append(f"{where}: a board role carries exactly one of "
                      f"{', '.join('phase-' + p for p in BOARD_PHASES)}")
    else:
        palette = BOARD_PHASES[names[0]]
        got = {k: str(v).upper() for k, v in (m.get("palette") or {}).items()}
        if got != palette or str(m.get("color", "")).upper() != palette["background"]:
            errors.append(f"{where}: a board role in phase {names[0]} uses color {palette['background']} and palette "
                          f"{json.dumps(palette)}")
        ceiling = BOARD_TOOL_CEILING[names[0]]
        tier = m.get("toolTier")
        if tier in TOOL_TIERS and TOOL_TIERS.index(tier) > TOOL_TIERS.index(ceiling):
            errors.append(f"{where}: a board role in phase {names[0]} has toolTier {tier!r}; the ceiling is {ceiling}")
    if "betterOn" in m:
        errors.append(f"{where}: a board role has no betterOn; the board's runner picks the model")
    md = atom.content_path
    text = md.read_text(encoding="utf-8") if md and md.is_file() else ""
    if not text:
        return errors
    headings = re.findall(r"^## (.+?)\s*$", text, re.M)
    if headings != BOARD_SECTIONS:
        errors.append(f"{atom.rel(md)}: sections must be {BOARD_SECTIONS}, in that order; found {headings}")
    for section, labels in BOARD_LABELS.items():
        body = re.search(rf"^## {re.escape(section)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        missing = [label for label in labels if not body or f"**{label}:**" not in body.group(1)]
        if missing:
            errors.append(f"{atom.rel(md)}: ## {section} needs the bullets {', '.join(f'**{x}:**' for x in missing)}")
    # A lost newline turns the next list item into the tail of the one before, which shifts the
    # numbering a prompt cites ("Principle 2") without breaking any section (card://JAVA-310).
    for number, line in enumerate(text.splitlines(), 1):
        if re.search(r"[.!?)](?:-|\d+\.) \*\*", line):
            errors.append(f"{atom.rel(md)}:{number}: a list item is glued to the sentence before it; start it on its own line")
    words = len(text.split())
    if words > BOARD_MAX_WORDS:
        errors.append(f"{atom.rel(md)}: {words} words; a board role's prompt stays under {BOARD_MAX_WORDS}")
    return errors


def hook_findings(atom: Atom) -> list[str]:
    """What the schema cannot say about a hook: an event fluxor-sync can wire, at least one script,
    and `tools`/`notifications` only on the events that read them, so nothing is silently ignored."""
    m = atom.manifest
    where = atom.rel(atom.manifest_path)
    errors = []
    event = m.get("event")
    if event not in HOOK_EVENTS:
        errors.append(f"{where}: event {event!r} is not one of {HOOK_EVENTS}")
    if not any(atom.manifest_path.with_suffix(f".{s}").is_file() for s in HOOK_SCRIPTS):
        errors.append(f"{where}: needs a script, {atom.id}.sh or {atom.id}.ps1, next to the manifest")
    if "tools" in m and event not in ("preTool", "postTool", "postToolFailure"):
        errors.append(f"{where}: tools only apply to preTool, postTool and postToolFailure, not {event!r}")
    if "notifications" in m and event != "notification":
        errors.append(f"{where}: notifications only apply to the notification event, not {event!r}")
    return errors


def preset_findings(atom: Atom, by_id: dict[str, Atom]) -> list[str]:
    """What the schema cannot say about a preset: each item is a skill or a hook of this market, by
    its id (the catalog key, so no alias), not a meta-skill, and listed once."""
    where = atom.rel(atom.manifest_path)
    errors, seen = [], set()
    for item in atom.manifest.get("items", []):
        key = item.get("key") if isinstance(item, dict) else None
        if not isinstance(key, str):
            continue  # the schema already reports it
        target = by_id.get(key)
        if key in seen:
            errors.append(f"{where}: item {key!r} is listed twice")
        elif target is None:
            errors.append(f"{where}: item {key!r} is not an atom of this market")
        elif target.kind not in PRESET_ITEM_KINDS:
            errors.append(f"{where}: item {key!r} is a {target.kind}; a preset lists skills and hooks")
        elif target.manifest.get("packaging") == "meta":
            errors.append(f"{where}: item {key!r} is a meta-skill, which needs a person's interview first")
        seen.add(key)
    errors += template_findings(where, atom.manifest.get("precedenceTemplates"))
    return errors


# A precedence template's placeholder (ADR 0032, JAVA-1692): the Java fill reads the same grammar, and
# tests/precedence-template-tokens.json holds the cases both must agree on.
TOKEN = re.compile(r"\{\{([^{}]*)\}\}")
TOKEN_NAME = re.compile(r"[A-Z][A-Z0-9_]{0,31}")
TOKEN_FACETS = ("epics", "tags")
FACET_VALUES = {
    "categories": {"epic", "feature", "userStory", "enhancement", "bug", "hotfix", "regression", "refactor",
                   "technicalDebt", "infrastructure", "security", "spike", "testing", "routine", "documentation"},
    "signals": {"touches-auth-permissions-or-personal-data", "touches-ui", "touches-data-schema",
                "touches-infrastructure"},
}


def value_tokens(value: str) -> list[str] | None:
    """The placeholder names a value holds, in order; None when a brace is stray or a name is malformed."""
    names = [m.group(1) for m in TOKEN.finditer(value)]
    rest = TOKEN.sub("", value)
    if any(not TOKEN_NAME.fullmatch(n) for n in names) or "{" in rest or "}" in rest:
        return None
    return names


def template_findings(where: str, templates) -> list[str]:
    """What the schema cannot say about a preset's precedence templates: unique ids, tokens only in the
    epics and tags values, every token declared and every declaration used, and the closed facet values."""
    errors: list[str] = []
    ids: set[str] = set()
    for template in templates if isinstance(templates, list) else []:
        tid = template.get("id")
        here = f"{where}: precedence template {tid!r}"
        if tid in ids:
            errors.append(f"{here} is listed twice")
        ids.add(tid)
        declared = [p.get("key") for p in template.get("placeholders", [])]
        if len(set(declared)) != len(declared):
            errors.append(f"{here} declares a placeholder twice")
        used: set[str] = set()
        for index, rule in enumerate(template.get("rules", [])):
            for facet, values in rule.get("match", {}).items():
                for value in values:
                    names = value_tokens(value)
                    if names is None:
                        errors.append(f"{here} rule {index} {facet}: {value!r} has a malformed placeholder")
                    elif names and facet not in TOKEN_FACETS:
                        errors.append(f"{here} rule {index} {facet}: a placeholder may stand only in epics or tags")
                    used.update(names or [])
                    if facet in FACET_VALUES and value not in FACET_VALUES[facet]:
                        errors.append(f"{here} rule {index} {facet}: unknown value {value!r}")
        for name in sorted(used - set(declared)):
            errors.append(f"{here} uses {{{{{name}}}}} but does not declare it")
        for name in sorted(set(declared) - used):
            errors.append(f"{here} declares {name} but no rule uses it")
    return errors


def meta_forms(atoms: list[Atom]) -> list[tuple[Atom, Path, dict]]:
    """Every meta-skill whose form is a readable form.json, with its path and data."""
    found = []
    for atom in atoms:
        form = atom.manifest.get("form")
        rel = form.get("questions") if isinstance(form, dict) else None
        if atom.manifest.get("packaging") != "meta" or not isinstance(rel, str) or not rel.endswith(".json"):
            continue
        path = atom.manifest_path.parent / rel
        if path.is_file():
            data, errors = forms.load(path)
            if data is not None:
                found.append((atom, path, data))
    return found


def note_findings(where: str, flow: dict) -> list[str]:
    # A step's noteBindings name note types the flow declares, each bound once (card://JAVA-1636).
    errors: list[str] = []
    declared: list[str] = []
    for note in flow.get("noteTypes", []):
        if note["id"] in declared:
            errors.append(f"{where}: duplicate noteTypes id {note['id']!r}")
        declared.append(note["id"])
    for step in flow.get("steps", []):
        bound: list[str] = []
        for binding in step.get("noteBindings", []):
            if binding["type"] not in declared:
                errors.append(f"{where} step {step.get('id')}: noteBindings type {binding['type']!r} "
                              "is not one of the flow's noteTypes")
            if binding["type"] in bound:
                errors.append(f"{where} step {step.get('id')}: note type {binding['type']!r} is bound twice")
            bound.append(binding["type"])
    return errors


def validate(check_language: bool = True) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    store = SchemaStore(SCHEMAS)
    try:
        config = load_config()
        errors += [f"marketplace.json {e}" for e in store.validate(config, "marketplace.schema.json")]
    except (OSError, json.JSONDecodeError) as exc:
        return [f"marketplace.json: {exc}"], warnings

    atoms, load_errors = load_catalog()
    errors += load_errors
    by_id: dict[str, Atom] = {}
    tracked = tracked_files()
    git_exec = git_executables()

    for atom in atoms:
        where = atom.rel(atom.manifest_path)
        for e in store.validate(atom.manifest, f"{atom.kind}.schema.json"):
            errors.append(f"{where} {e}")
        if atom.id != atom.expected_id:
            errors.append(f"{where}: id {atom.id!r} must equal {atom.expected_id!r}")
        if atom.manifest.get("kind") != atom.kind:
            errors.append(f"{where}: kind must be {atom.kind!r}")
        if atom.id in by_id:
            errors.append(f"{where}: id {atom.id!r} is already used by {by_id[atom.id].rel(by_id[atom.id].manifest_path)}")
        by_id[atom.id] = atom
    aliases = {}
    for atom in atoms:
        for alias in atom.manifest.get("aliases", []):
            if alias in by_id or alias in aliases:
                errors.append(f"{atom.rel(atom.manifest_path)}: alias {alias!r} collides with another id or alias")
            aliases[alias] = atom.id

    def ref_id(ref: str) -> str:
        return ref.split("@", 1)[0]

    def must_exist(where: str, ref: str, kinds: tuple[str, ...]) -> None:
        target = by_id.get(ref_id(ref)) or by_id.get(aliases.get(ref_id(ref), ""))
        if target is None:
            errors.append(f"{where}: unknown atom {ref!r}")
        elif target.kind not in kinds:
            errors.append(f"{where}: {ref!r} is a {target.kind}, expected {' or '.join(kinds)}")
        elif "@" in ref and not version_satisfies(target.version, ref.split("@", 1)[1]):
            errors.append(f"{where}: {ref!r} does not match {target.id} {target.version}")

    for atom in atoms:
        m = atom.manifest
        where = atom.rel(atom.manifest_path)
        folder = atom.manifest_path.parent
        for ref in m.get("requires", {}).get("atoms", []):
            must_exist(where, ref, ("role", "mod", "step", "flow", "skill", "engine"))
        errors += config_findings(atom)
        errors += board_role_findings(atom)

        if atom.kind in MARKET_KINDS or atom.kind == "hook":
            md = atom.content_path
            if not md.is_file() or not md.read_text(encoding="utf-8").strip():
                errors.append(f"{where}: missing or empty {atom.rel(md)}")

        if atom.kind == "hook":
            errors += hook_findings(atom)

        if atom.kind == "preset":
            errors += preset_findings(atom, by_id)

        if atom.kind == "mod":
            for other in m.get("incompatibleWith", []):
                if other == atom.id:
                    errors.append(f"{where}: a mod cannot be incompatible with itself")
                else:
                    must_exist(where, other, ("mod",))
            has_runtime = bool(m.get("runtime"))
            if m.get("enforcement") == "runtime" and not has_runtime:
                errors.append(f"{where}: enforcement 'runtime' needs a runtime block")
            if has_runtime and m.get("enforcement") == "prompt":
                errors.append(f"{where}: has a runtime block, so enforcement cannot be 'prompt'")

        if atom.kind == "flow":
            seen: list[str] = []
            for step in m.get("steps", []):
                sid = step.get("id")
                if sid in seen:
                    errors.append(f"{where}: duplicate step id {sid!r}")
                if "stepRef" in step:
                    must_exist(f"{where} step {sid}", step["stepRef"], ("step",))
                if "roleId" in step:
                    must_exist(f"{where} step {sid}", step["roleId"], ("role",))
                for mod in step.get("modIds", []):
                    must_exist(f"{where} step {sid}", mod, ("mod",))
                for prev in step.get("prevStepIds", []):
                    if prev not in seen:
                        errors.append(f"{where} step {sid}: prevStepIds {prev!r} is not an earlier step")
                loop = step.get("loopBackTo")
                if loop and loop.get("stepId") not in seen + [sid]:
                    errors.append(f"{where} step {sid}: loopBackTo {loop.get('stepId')!r} is not this or an earlier step")
                seen.append(sid)
            errors += note_findings(where, m)
            if m.get("cost") == "infinite" and not any("loopBackTo" in s for s in m.get("steps", [])):
                warnings.append(f"{where}: cost 'infinite' but no step loops back")

        if atom.kind == "skill":
            skill_md = folder / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"{where}: missing SKILL.md")
            else:
                fm = front_matter(skill_md.read_text(encoding="utf-8"))
                if fm.get("name") != atom.id:
                    errors.append(f"{atom.rel(skill_md)}: front matter name {fm.get('name')!r} must be {atom.id!r}")
                description = fm.get("description", "")
                if not description:
                    errors.append(f"{atom.rel(skill_md)}: front matter needs a description")
                elif len(description) > 1024:
                    errors.append(f"{atom.rel(skill_md)}: description is {len(description)} characters (limit 1024)")
                elif len(description) > 950:
                    warnings.append(f"{atom.rel(skill_md)}: description is {len(description)} characters; leave room under 1024")
            for hook in m.get("hooks", []):
                path = folder / hook["command"]
                rel = atom.rel(path) if path.exists() else hook["command"]
                if not path.is_file():
                    errors.append(f"{where}: hook {hook['command']!r} does not exist")
                elif rel in _tracked_cache() and rel not in git_exec:
                    errors.append(f"{where}: hook {rel} is not executable in git (git update-index --chmod=+x)")
            for tool in m.get("tools", []):
                scripts = [a for a in tool["command"] if "/" in a or a.endswith((".py", ".sh", ".cjs", ".mjs", ".js"))]
                for script in scripts:
                    if not (folder / script).is_file():
                        errors.append(f"{where}: tool {tool['name']!r} runs {script!r}, which does not exist")
            for kind, ids in m.get("provides", {}).items():
                for ref in ids:
                    must_exist(where, ref, (kind.rstrip("s"),))
            if m.get("packaging") == "bundle" and not m.get("provides"):
                errors.append(f"{where}: packaging 'bundle' needs a provides block")
            errors += form_findings(atom, store)

        if atom.kind == "engine":
            for rel in m.get("files", []):
                if not (ROOT / rel).is_file():
                    errors.append(f"{where}: file {rel!r} does not exist")

    for a, b in compatibility.one_sided([atom.manifest for atom in atoms]):
        warnings.append(f"market/mods/{a}.json: incompatible with {b!r}, but {b} does not declare it back")

    # Orphan prompts: an .md without a manifest is invisible to every consumer. So is a hook script.
    for path in sorted(HOOKS.glob("*")):
        orphan = not path.with_suffix(".json").is_file() and path.name not in AUTHORING_DOCS
        if orphan and path.suffix.lstrip(".") in ("md", *HOOK_SCRIPTS):
            errors.append(f"{path.relative_to(ROOT).as_posix()}: no manifest next to it")
    for kind, folder in MARKET_KINDS.items():
        for md in sorted((MARKET / folder).glob("*.md")):
            if md.name not in AUTHORING_DOCS and not md.with_suffix(".json").is_file():
                errors.append(f"{md.relative_to(ROOT).as_posix()}: no manifest next to it")
        # Orphan config companions: shipped by nobody, so no harness ever receives them.
        for path in sorted((MARKET / folder).glob("*.json")):
            match = CONFIG_COMPANION.search(path.name)
            if not match:
                continue
            owner = by_id.get(path.name[:match.start()])
            owner_config = owner.manifest.get("config") if owner else None
            declared = owner_config.get(match.group(1)) if isinstance(owner_config, dict) else None
            if owner is None or owner.kind != kind or declared != path.name:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: no manifest declares it as "
                              f"config.{match.group(1)}")

    if not errors:
        expected = dump_json(fluxor_inventory(atoms))
        current = INVENTORY.read_text(encoding="utf-8") if INVENTORY.is_file() else ""
        if current != expected:
            errors.append("market/inventory.json is out of date: run `tools/marketplace.py inventory`")
        errors += check_lock(atoms, tracked, git_exec)
    if check_language:
        warnings_or_errors = language_findings(config, tracked)
        errors += warnings_or_errors
    return errors, warnings


def version_key(version: str) -> tuple:
    m = SEMVER.match(version)
    if not m:
        return (0, 0, 0, "")
    major, minor, patch, pre = m.groups()
    # A pre-release sorts before its release.
    return (int(major), int(minor), int(patch), pre is None, pre or "")


def version_satisfies(version: str, spec: str) -> bool:
    """Whether `version` is in the range of an atomRef suffix: `1` and `1.2` fix the components
    they name, `1.2.3` is exact, `~1.2` allows patches, `^1.2` allows minors (npm semantics, so
    `^0.2` allows only patches)."""
    m = SEMVER.match(version)
    if not m:
        return False
    have = tuple(int(x) for x in m.groups()[:3])
    op = spec[0] if spec[:1] in ("^", "~") else ""
    parts = [int(p) for p in spec.lstrip("^~").split(".")]
    base = tuple(parts + [0] * (3 - len(parts)))
    if op == "":
        keep = len(parts)
    elif have < base:
        return False
    elif op == "~":
        keep = min(len(parts), 2)
    else:
        keep = next((i + 1 for i, p in enumerate(parts) if p), len(parts))
    return have[:keep] == base[:keep]


def read_lock() -> dict:
    if not LOCK.is_file():
        return {"schemaVersion": 1, "atoms": {}}
    return json.loads(LOCK.read_text(encoding="utf-8"))


def current_state(atoms, tracked, git_exec) -> dict[str, dict]:
    state = {}
    for atom in atoms:
        files = describe_files(atom, tracked, git_exec)
        state[atom.id] = {"kind": atom.kind, "version": atom.version, "hash": atom_hash(atom, files)}
    return state


def check_lock(atoms, tracked, git_exec) -> list[str]:
    errors = []
    locked = read_lock().get("atoms", {})
    for aid, now in sorted(current_state(atoms, tracked, git_exec).items()):
        before = locked.get(aid)
        if before is None:
            errors.append(f"{aid}: new atom, not in marketplace.lock.json: run `tools/marketplace.py lock`")
        elif before["hash"] != now["hash"] and before["version"] == now["version"]:
            errors.append(f"{aid}: content changed but version is still {now['version']}: bump it, then run `lock`")
        elif version_key(now["version"]) < version_key(before["version"]):
            errors.append(f"{aid}: version went backwards ({before['version']} -> {now['version']})")
        elif before["hash"] != now["hash"] or before["version"] != now["version"]:
            errors.append(f"{aid}: {before['version']} -> {now['version']} is not recorded: run `tools/marketplace.py lock`")
    present = {a.id for a in atoms}
    for aid in sorted(set(locked) - present):
        errors.append(f"{aid}: in the lock but gone; published atoms are deprecated, not deleted "
                      "(run `lock --allow-removal` if this one was never published)")
    return errors


def language_findings(config: dict, tracked) -> list[str]:
    allowed = config.get("language", {}).get("functionalData", [])
    files = sorted(tracked) if tracked is not None else []
    findings = []
    for rel in files:
        if PurePosixPath(rel).suffix not in TEXT_SUFFIXES or rel.startswith("tools/english.py"):
            continue
        if glob_match(rel, allowed):
            continue
        try:
            lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, 1):
            if english.is_spanish(line):
                findings.append(f"{rel}:{number}: not American English: {line.strip()[:100]}")
    return findings


# ─── Commands ───────────────────────────────────────────────────────────────────────────────────

def cmd_validate(args) -> int:
    errors, warnings = validate(check_language=not args.no_language)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    atoms, _ = load_catalog()
    if errors:
        print(f"\n{len(errors)} error(s) in {len(atoms)} atom(s)")
        return 1
    print(f"ok: {len(atoms)} atoms valid, lock and inventory up to date"
          + (f" ({len(warnings)} warning(s))" if warnings else ""))
    return 0


def cmd_list(args) -> int:
    atoms, errors = load_catalog()
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    for atom in sorted(atoms, key=lambda a: (a.kind, a.id)):
        if args.kind and atom.kind != args.kind:
            continue
        flag = "" if atom.manifest.get("stability", "stable") == "stable" else f" [{atom.manifest['stability']}]"
        print(f"{atom.kind:6}  {atom.id:32} {atom.version:9}{flag}  {atom.manifest.get('description', '')[:90]}")
    return 0


def cmd_inventory(args) -> int:
    atoms, errors = load_catalog()
    if errors:
        for e in errors:
            print(f"error: {e}")
        return 1
    expected = dump_json(fluxor_inventory(atoms))
    if args.check:
        current = INVENTORY.read_text(encoding="utf-8") if INVENTORY.is_file() else ""
        if current != expected:
            print("market/inventory.json is out of date: run `tools/marketplace.py inventory`")
            return 1
        print("market/inventory.json is up to date")
        return 0
    write_lf(INVENTORY, expected)
    print(f"wrote market/inventory.json ({sum(1 for a in atoms if a.kind in MARKET_KINDS)} cards)")
    return 0


def cmd_forms(args) -> int:
    """Render every meta-skill's form.json to the questions.md next to it (or check they match)."""
    atoms, errors = load_catalog()
    for e in errors:
        print(f"error: {e}")
    stale = 0
    store = SchemaStore(SCHEMAS)
    for atom, path, data in meta_forms(atoms):
        problems = store.validate(data, "form.schema.json")
        if problems:
            print(f"error: {atom.rel(path)} is not a valid form; fix it first: {problems[0]}")
            stale += 1
            continue
        target = path.with_name("questions.md")
        expected = forms.render_markdown(data)
        current = target.read_text(encoding="utf-8").replace("\r\n", "\n") if target.is_file() else ""
        if current == expected:
            continue
        stale += 1
        if args.check:
            print(f"{atom.rel(target)} is out of date")
        else:
            write_lf(target, expected)
            print(f"wrote {atom.rel(target)}")
    if args.check and stale:
        print("run `tools/marketplace.py forms`")
        return 1
    return 1 if errors else 0


def cmd_lock(args) -> int:
    only = {i for part in args.only or [] for i in part.split(",") if i}
    errors, _ = validate(check_language=False)
    blocking = [e for e in errors if "marketplace.lock.json" not in e and "run `lock`" not in e
                and "run `tools/marketplace.py lock`" not in e and "in the lock but gone" not in e]
    if only:
        # Another atom's error (with a card of its own) must not stop recording these: only an
        # error naming one of them blocks, and the rest of the lock stays as it was.
        blocking = [e for e in blocking if any(re.search(rf"(^|[/\s']){re.escape(i)}([/\s'@:]|$)", e) for i in only)]
    if blocking:
        for e in blocking:
            print(f"error: {e}")
        print("fix these before locking")
        return 1
    atoms, _ = load_catalog()
    locked = read_lock().get("atoms", {})
    unknown = sorted(only - {a.id for a in atoms})
    if unknown:
        print(f"error: no atom called {', '.join(unknown)}")
        return 1
    state = current_state([a for a in atoms if not only or a.id in only], tracked_files(), git_executables())
    if only:
        state = {**locked, **state}
    problems = []
    for aid, now in state.items():
        before = locked.get(aid)
        if before and before["hash"] != now["hash"] and version_key(now["version"]) <= version_key(before["version"]):
            problems.append(f"{aid}: content changed; bump its version above {before['version']} first")
    removed = sorted(set(locked) - set(state))
    if removed and not args.allow_removal:
        problems += [f"{aid}: removed; deprecate it instead, or pass --allow-removal" for aid in removed]
    if problems:
        for p in problems:
            print(f"error: {p}")
        return 1
    write_lf(LOCK, dump_json({"schemaVersion": 1, "atoms": dict(sorted(state.items()))}))
    changed = [a for a in state if locked.get(a) != state[a]]
    print(f"wrote marketplace.lock.json ({len(state)} atoms, {len(changed)} changed)")
    return 0


def git_head() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def cmd_build(args) -> int:
    errors, _ = validate(check_language=False)
    if errors and not args.force:
        for e in errors:
            print(f"error: {e}")
        print("refusing to build an invalid catalog (use --force only for local experiments)")
        return 1
    config = load_config()
    atoms, _ = load_catalog()
    tracked = tracked_files()
    git_exec = git_executables()
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    blobs = out / "blobs"
    blobs.mkdir(parents=True)
    entries = []
    for atom in sorted(atoms, key=lambda a: (a.kind, a.id)):
        files = describe_files(atom, tracked, git_exec)
        for f in files:
            target = blobs / f["sha256"]
            if not target.exists():
                target.write_bytes(read_content(f["source"]))
        manifest = {k: v for k, v in atom.manifest.items() if k != "$schema"}
        entries.append({
            "ref": f"{config['namespace']}/{atom.id}@{atom.version}",
            "id": atom.id,
            "kind": atom.kind,
            "version": atom.version,
            "stability": manifest.get("stability", "stable"),
            "hash": atom_hash(atom, files),
            "manifest": manifest,
            "files": [{k: f[k] for k in ("path", "sha256", "size", "executable")} for f in files],
        })
    index = {
        "schemaVersion": 1,
        "namespace": config["namespace"],
        "publisher": config["publisher"],
        "source": {"repository": config["source"], "commit": git_head()},
        "atoms": entries,
    }
    write_lf(out / "index.json", dump_json(index))
    write_lf(out / "inventory.json", dump_json(fluxor_inventory(atoms)))
    write_lf(out / "compatibility.json", dump_json(compatibility.compute([a.manifest for a in atoms])))
    shutil.copytree(SCHEMAS, out / "schemas")
    size = sum(p.stat().st_size for p in blobs.iterdir())
    print(f"built {len(entries)} atoms, {sum(1 for _ in blobs.iterdir())} blobs ({size // 1024} KiB) into {out}")
    return 0


def cmd_install(args) -> int:
    import installer
    harness = installer.harness_dir(args.harness)
    me = sys.modules[__name__]
    return installer.check(me, harness) if args.check else installer.install(me, harness, force=args.force)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate", help="validate the whole catalog")
    p.add_argument("--no-language", action="store_true", help="skip the American English check")
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("list", help="list the catalog")
    p.add_argument("kind", nargs="?", choices=["role", "mod", "step", "flow", "hook", "preset", "skill", "engine"])
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("inventory", help="write market/inventory.json (the Fluxor projection)")
    p.add_argument("--check", action="store_true", help="only check that it is up to date")
    p.set_defaults(func=cmd_inventory)
    p = sub.add_parser("forms", help="render each meta-skill's form.json to its questions.md")
    p.add_argument("--check", action="store_true", help="only check that they are up to date")
    p.set_defaults(func=cmd_forms)
    p = sub.add_parser("lock", help="record versions and content hashes in marketplace.lock.json")
    p.add_argument("--allow-removal", action="store_true", help="drop atoms that no longer exist")
    p.add_argument("--only", action="append", metavar="ID[,ID]",
                   help="record only these atoms, when an unrelated atom's error blocks a full lock")
    p.set_defaults(func=cmd_lock)
    p = sub.add_parser("build", help="write the publishable bundle")
    p.add_argument("--out", required=True, help="output directory (replaced)")
    p.add_argument("--force", action="store_true", help="build even if validation fails")
    p.set_defaults(func=cmd_build)
    p = sub.add_parser("install", help="install a project's selection into its harness, or check it")
    p.add_argument("--harness", help="the harness directory (default: $HARNESS_DIR, else <project>/.harness)")
    p.add_argument("--check", action="store_true", help="only check the installed copies; exit 1 on drift")
    p.add_argument("--force", action="store_true", help="overwrite managed files that were edited by hand")
    p.set_defaults(func=cmd_install)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
