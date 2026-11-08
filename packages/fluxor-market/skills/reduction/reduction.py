#!/usr/bin/env python3
"""reduction.py: the state of a code-reduction campaign, derived from its analysis folder.

The protocol lives in SKILL.md; this is its executable half. It exists for the three things
that go wrong in a campaign that spans many sessions, none of which prose prevents:

  1. Two analysis files for the same technique, written months apart, disagreeing. P0 says
     "if the file exists, update it, never duplicate it": `new` enforces it, `check` catches it.
  2. A verdict written as free text ("looks good", "maybe partial"), which cannot be counted and
     so cannot be reported. The enum is APPLY | PARTIAL | DISCARD and nothing else.
  3. Phase 2 running and nobody ever going back to write down what the real saving was. An
     estimate never checked against reality produces better and better estimates of nothing.

    reduction.py list              # the 21 techniques and their state
    reduction.py new J1 [--force]  # analysis skeleton with the right frontmatter
    reduction.py check             # 0 if every analysis file is well-formed, 1 if not
    reduction.py config            # resolved project facts: roots, analysis dir, UI package
    reduction.py surface REGEX [--lang java|react|all] [--tests]
                                   # files, occurrences and LOC for phase 1's "Surface" line
    reduction.py route [ARGS...]   # delegates to the `topology` skill when it is installed

Project root: $CLAUDE_PROJECT_DIR, else `git rev-parse --show-toplevel`, else the current
directory. Harness: $HARNESS_DIR, else <root>/.harness. Project facts come from
<harness>/config/reduction.json, with autodetection for every key that is missing.

It writes ONLY inside the analysis directory. It never touches source code: applying a
technique is the agent's job, under the approval gate, and a script that could do it on its own
would be a way around that gate.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import json
import os
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent
TOPOLOGY = SKILL_DIR.parent / "topology" / "topology.py"

VERDICTS = ("APPLY", "PARTIAL", "DISCARD")
FIELDS = ("technique", "scope", "date", "verdict")
REAL_LOC = "Real LOC:"
LINE_CEILING = 60

# id -> (scope, name, slug)
TECHNIQUES = {
    "J1": ("java", "records + sealed interfaces", "records-sealed"),
    "J2": ("java", "single-implementation interfaces", "single-impl-interfaces"),
    "J3": ("java", "generic repository/service/resource", "generic-persistence"),
    "J4": ("java", "central exception mapping", "central-exception-mapping"),
    "J5": ("java", "declarative validation", "declarative-validation"),
    "J6": ("java", "strategy registry", "strategy-registry"),
    "J7": ("java", "mapping layer", "mapping-layer"),
    "J8": ("java", "cross-cutting via interceptors", "interceptors"),
    "J9": ("java", "parametrized tests + test data factory", "parametrized-tests"),
    "J10": ("java", "home-grown utilities vs framework", "home-grown-utilities"),
    "R1": ("react", "generated API client and types", "generated-api-client"),
    "R2": ("react", "schema-driven forms", "schema-driven-forms"),
    "R3": ("react", "shared design system across apps", "shared-design-system"),
    "R4": ("react", "variants instead of cloned components", "variants-over-clones"),
    "R5": ("react", "declarative tables", "declarative-tables"),
    "R6": ("react", "one data-fetching layer", "single-fetching-layer"),
    "T1": ("transversal", "one schema-first contract", "schema-first-contract"),
    "T2": ("transversal", "dead code deletion", "dead-code"),
    "T3": ("transversal", "predictable location", "predictable-location"),
    "T4": ("transversal", "conventions enforced by tooling", "enforced-conventions"),
    "T5": ("transversal", "domain modularization", "domain-modularization"),
}

EXTENSIONS = {
    "java": (".java",),
    "react": (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"),
}

DEFAULT_EXCLUDE = [
    "**/node_modules/**", "**/target/**", "**/build/**", "**/dist/**", "**/out/**",
    "**/.next/**", "**/.nuxt/**", "**/.turbo/**", "**/.gradle/**", "**/coverage/**",
    "**/generated/**", "**/generated-sources/**", "**/__generated__/**",
    "**/vendor/**", "**/third_party/**", "**/.git/**", "**/.harness/**", "**/.claude/**",
    "**/*.min.js", "**/*.d.ts",
]
DEFAULT_TESTS = [
    "**/src/test/**", "**/src/testFixtures/**", "**/src/it/**", "**/__tests__/**",
    "**/test/**", "**/tests/**", "**/e2e/**",
    "**/*.test.*", "**/*.spec.*", "**/*Test.java", "**/*Tests.java", "**/*IT.java",
]
CONFIG_KEYS = ("analysisDir", "sources", "uiPackage", "exclude", "tests", "decided", "verify")
UI_NAME = re.compile(r"(^|/)(ui|design-system|components)$")
REACTISH = ("react", "next", "typescript", "react-dom", "@types/react")


# ---------------------------------------------------------------------------------------------
# Locating the project (.harness/contracts/harness-convention.md in Fluxor's market, rule 1)

def project_root() -> pathlib.Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and pathlib.Path(env).is_dir():
        return pathlib.Path(env).resolve()
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, timeout=10)
        if top.returncode == 0 and top.stdout.strip():
            return pathlib.Path(top.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return pathlib.Path.cwd().resolve()


def harness_dir(root: pathlib.Path) -> pathlib.Path:
    env = os.environ.get("HARNESS_DIR")
    return pathlib.Path(env).resolve() if env else root / ".harness"


def show(path: pathlib.Path, root: pathlib.Path) -> str:
    """A path relative to the project root when it lives inside it, absolute otherwise."""
    try:
        return path.relative_to(root).as_posix() or "."
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------------------------
# Configuration, with autodetection for every missing key (rule 2)

class Config:
    def __init__(self) -> None:
        self.root = project_root()
        self.harness = harness_dir(self.root)
        self.path = self.harness / "config" / "reduction.json"
        self.problems: list[str] = []
        self.notes: list[str] = []
        raw = self._load()
        self.origin: dict[str, str] = {}

        self.exclude = self._list(raw, "exclude", DEFAULT_EXCLUDE)
        self.tests = self._list(raw, "tests", DEFAULT_TESTS)

        if "analysisDir" in raw and isinstance(raw["analysisDir"], str):
            self.analysis = (self.root / raw["analysisDir"]).resolve()
            self.origin["analysisDir"] = "config"
        else:
            if "analysisDir" in raw:
                self.problems.append("'analysisDir' must be a path string; using the default")
            self.analysis = self.harness / "analysis"
            self.origin["analysisDir"] = "default"
            if not self.harness.is_dir():
                self.notes.append(
                    f"no harness at {show(self.harness, self.root)}: analyses will go to "
                    f"{show(self.analysis, self.root)} (created by `new`). Set `analysisDir` in "
                    f"{show(self.path, self.root)} to put them elsewhere.")

        self._walk_cache: list[pathlib.Path] | None = None
        self.sources = self._sources(raw)
        self.ui_package = self._ui_package(raw)
        self.decided = self._decided(raw)
        self.verify = self._verify(raw)

    # -- loading ---------------------------------------------------------------------------

    def _load(self) -> dict:
        if not self.path.is_file():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.problems.append(f"{show(self.path, self.root)} is not valid JSON ({exc}); "
                                 f"using defaults")
            return {}
        if not isinstance(data, dict):
            self.problems.append(f"{show(self.path, self.root)} must hold a JSON object; "
                                 f"using defaults")
            return {}
        for key in data:
            if key not in CONFIG_KEYS and not key.startswith("$"):
                self.problems.append(f"unknown key '{key}' in {show(self.path, self.root)} "
                                     f"(valid: {', '.join(CONFIG_KEYS)})")
        return data

    def _list(self, raw: dict, key: str, default: list[str]) -> list[str]:
        value = raw.get(key)
        if value is None:
            self.origin[key] = "default"
            return list(default)
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            self.origin[key] = "config"
            return value
        self.problems.append(f"'{key}' must be a list of glob strings; using the default")
        self.origin[key] = "default"
        return list(default)

    # -- file walking ----------------------------------------------------------------------

    def excluded(self, rel: str, is_dir: bool = False) -> bool:
        probe = "./" + rel + ("/" if is_dir else "")
        return any(fnmatch.fnmatch(probe, pat) for pat in self.exclude)

    def is_test(self, rel: str) -> bool:
        probe = "./" + rel
        return any(fnmatch.fnmatch(probe, pat) for pat in self.tests)

    def walk(self, base: pathlib.Path):
        """Every file under `base` that the exclusions let through, pruning excluded dirs."""
        for dirpath, dirnames, filenames in os.walk(base):
            here = pathlib.Path(dirpath)
            keep = []
            for d in dirnames:
                if d.startswith("."):  # VCS, IDE, tool caches, the harness itself
                    continue
                if not self.excluded(show(here / d, self.root), is_dir=True):
                    keep.append(d)
            dirnames[:] = sorted(keep)
            for f in sorted(filenames):
                path = here / f
                if not self.excluded(show(path, self.root)):
                    yield path

    def _manifests(self) -> list[pathlib.Path]:
        if self._walk_cache is None:
            names = {"pom.xml", "build.gradle", "build.gradle.kts", "package.json"}
            self._walk_cache = [p for p in self.walk(self.root) if p.name in names]
        return self._walk_cache

    # -- sources -----------------------------------------------------------------------------

    def _sources(self, raw: dict) -> dict[str, list[pathlib.Path]]:
        configured = raw.get("sources") if isinstance(raw.get("sources"), dict) else {}
        if "sources" in raw and not isinstance(raw.get("sources"), dict):
            self.problems.append("'sources' must be an object {\"java\": [...], \"react\": [...]}")
        out: dict[str, list[pathlib.Path]] = {}
        for lang in EXTENSIONS:
            value = configured.get(lang)
            if isinstance(value, list) and all(isinstance(v, str) for v in value):
                roots = [(self.root / v).resolve() for v in value]
                missing = [show(r, self.root) for r in roots if not r.is_dir()]
                if missing:
                    self.problems.append(f"sources.{lang}: not a directory: {', '.join(missing)}")
                out[lang] = [r for r in roots if r.is_dir()]
                self.origin[f"sources.{lang}"] = "config"
            else:
                if value is not None:
                    self.problems.append(f"sources.{lang} must be a list of paths; autodetecting")
                out[lang] = self._detect_java() if lang == "java" else self._detect_react()
                self.origin[f"sources.{lang}"] = "autodetected"
        return out

    def _detect_java(self) -> list[pathlib.Path]:
        """Maven and Gradle modules that carry Java sources."""
        found = set()
        for manifest in self._manifests():
            if manifest.name == "package.json":
                continue
            module = manifest.parent
            if (module / "src" / "main" / "java").is_dir():
                found.add(module)
        return sorted(found)

    def _detect_react(self) -> list[pathlib.Path]:
        """package.json projects that use React or TypeScript; workspace roots are skipped
        because their members are detected on their own."""
        found = set()
        for manifest in self._manifests():
            if manifest.name != "package.json":
                continue
            data = _read_json(manifest)
            if data is None:
                continue
            project = manifest.parent
            if "workspaces" in data or (project / "pnpm-workspace.yaml").exists() \
                    or (project / "lerna.json").exists():
                continue
            deps = {}
            for key in ("dependencies", "devDependencies", "peerDependencies"):
                if isinstance(data.get(key), dict):
                    deps.update(data[key])
            if any(d in deps for d in REACTISH) or (project / "tsconfig.json").exists():
                found.add(project)
        return sorted(found)

    def files(self, lang: str, tests: bool) -> list[pathlib.Path]:
        langs = list(EXTENSIONS) if lang == "all" else [lang]
        seen: set[pathlib.Path] = set()
        out = []
        for lg in langs:
            exts = EXTENSIONS[lg]
            for base in self.sources[lg]:
                for path in self.walk(base):
                    if path in seen or not path.name.endswith(exts):
                        continue
                    if not tests and self.is_test(show(path, self.root)):
                        continue
                    seen.add(path)
                    out.append(path)
        return out

    # -- the other keys ----------------------------------------------------------------------

    def _ui_package(self, raw: dict) -> str | None:
        if "uiPackage" in raw:
            self.origin["uiPackage"] = "config"
            value = raw["uiPackage"]
            return value if isinstance(value, str) and value else None
        names = []
        for project in self.sources["react"]:
            data = _read_json(project / "package.json") or {}
            name = data.get("name")
            if isinstance(name, str) and UI_NAME.search(name):
                names.append(name)
        if len(names) == 1:
            self.origin["uiPackage"] = "autodetected"
            return names[0]
        self.origin["uiPackage"] = "none" if not names else \
            f"ambiguous ({', '.join(names)}): set it in the config"
        return None

    def _decided(self, raw: dict) -> dict[str, str]:
        value = raw.get("decided", {})
        if not isinstance(value, dict):
            self.problems.append("'decided' must map technique ids to a reason")
            return {}
        out = {}
        for tid, reason in value.items():
            if tid.upper() not in TECHNIQUES:
                self.problems.append(f"decided: '{tid}' is not a known technique id")
            elif not isinstance(reason, str) or not reason.strip():
                self.problems.append(f"decided.{tid}: the reason must be a non-empty string")
            else:
                out[tid.upper()] = reason.strip()
        self.origin["decided"] = "config" if value else "default"
        return out

    def _verify(self, raw: dict) -> dict[str, str]:
        value = raw.get("verify")
        if isinstance(value, dict) and all(isinstance(v, str) for v in value.values()):
            self.origin["verify"] = "config"
            return dict(value)
        if value is not None:
            self.problems.append("'verify' must map a name to a command string; autodetecting")
        self.origin["verify"] = "autodetected"
        out = {}
        if (self.root / "mvnw").exists() or (self.root / "pom.xml").exists():
            mvn = "./mvnw" if (self.root / "mvnw").exists() else "mvn"
            out["java"] = f"{mvn} -q -pl <module> -am test"
        elif (self.root / "gradlew").exists():
            out["java"] = "./gradlew :<module>:test"
        pkg = _read_json(self.root / "package.json") or {}
        if isinstance(pkg.get("scripts"), dict) and "test" in pkg["scripts"]:
            runner = "pnpm" if (self.root / "pnpm-lock.yaml").exists() else \
                "yarn" if (self.root / "yarn.lock").exists() else "npm"
            out["react"] = f"{runner} test"
        return out


def _read_json(path: pathlib.Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------------------------
# Analysis files

def _frontmatter(text: str) -> dict[str, str]:
    """The frontmatter as a dict, or {} if the file has none. Deliberately tolerant: a
    malformed file is reported by `check`, not crashed on here."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    out = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def _analysis_files(cfg: Config) -> list[pathlib.Path]:
    if not cfg.analysis.is_dir():
        return []
    return [p for p in sorted(cfg.analysis.glob("*.md")) if p.name != "README.md"]


def _existing(cfg: Config) -> dict[str, pathlib.Path]:
    """Analysis files found on disk, keyed by technique id. A technique with two files is a
    duplicate and shows up in `check`; here the first one wins so `list` still prints."""
    found: dict[str, pathlib.Path] = {}
    for path in _analysis_files(cfg):
        found.setdefault(path.name.split("-", 1)[0].upper(), path)
    return found


def _warn(cfg: Config) -> None:
    for problem in cfg.problems:
        print(f"warning: {problem}", file=sys.stderr)
    for note in cfg.notes:
        print(f"note: {note}", file=sys.stderr)


# ---------------------------------------------------------------------------------------------
# Commands

def cmd_list(cfg: Config) -> int:
    _warn(cfg)
    found = _existing(cfg)
    scope = None
    for tid, (sc, name, _slug) in TECHNIQUES.items():
        if sc != scope:
            scope = sc
            print(f"\n{scope.upper()}")
        path = found.get(tid)
        if path:
            front = _frontmatter(path.read_text(encoding="utf-8"))
            state = f"{front.get('verdict', '?'):9s} {front.get('date', '?')}"
        else:
            state = "-         not analyzed"
        print(f"  {tid:4s} {state}  {name}")
        if tid in cfg.decided:
            print(f"       ^ already decided by the project: {cfg.decided[tid]}")
    known = sum(1 for tid in found if tid in TECHNIQUES)
    print(f"\n{known}/{len(TECHNIQUES)} analyzed, in {show(cfg.analysis, cfg.root)}. "
          f"Phase 2 needs the user's explicit approval, per technique.")
    return 0


def cmd_new(cfg: Config, tid: str, force: bool) -> int:
    _warn(cfg)
    tid = tid.upper()
    if tid not in TECHNIQUES:
        print(f"unknown technique: {tid}. Valid: {', '.join(TECHNIQUES)}", file=sys.stderr)
        return 1
    scope, name, slug = TECHNIQUES[tid]
    if tid in cfg.decided and not force:
        print(f"{tid} already carries a decision from the project:\n  {cfg.decided[tid]}\n"
              f"Analyzing it again reopens a closed decision. If the user asked for it "
              f"explicitly, re-run with --force.", file=sys.stderr)
        return 1
    existing = _existing(cfg).get(tid)
    if existing:
        print(f"{show(existing, cfg.root)} already exists: update it, don't duplicate it.",
              file=sys.stderr)
        return 1
    path = cfg.analysis / f"{tid}-{slug}.md"
    cfg.analysis.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "---\n"
            f"technique: {tid} — {name}\n"
            f"scope: {scope}\n"
            f"date: {_dt.date.today().isoformat()}\n"
            "verdict: PENDING\n"
            "---\n"
            "Surface: <n files>, <n occurrences>, <n LOC>\n"
            "Estimated saving: <LOC before> -> <LOC after> (<%>)\n"
            "Context per unit: <n files before> -> <n files after>\n"
            "Self-description risk: low | medium | high — <one line>\n"
            "Migration cost: <batches>\n"
            "Top 10 files by impact:\n"
            "Blockers:\n"
            "Sources consulted:\n"
            f"\n{REAL_LOC} <filled in after phase 2, never before>\n"
        )
    print(f"created {show(path, cfg.root)}")
    print("Fill it from real commands. `verdict: PENDING` does not authorize phase 2.")
    return 0


def cmd_check(cfg: Config) -> int:
    bad = 0
    for problem in cfg.problems:
        print(f"  FAILS  config: {problem}")
        bad += 1
    for note in cfg.notes:
        print(f"  info   {note}")
    if not cfg.analysis.is_dir():
        print(f"  ok     no {show(cfg.analysis, cfg.root)} yet: nothing to check")
        return 1 if bad else 0
    seen: dict[str, pathlib.Path] = {}
    files = _analysis_files(cfg)
    for path in files:
        rel = show(path, cfg.root)
        text = path.read_text(encoding="utf-8")
        front = _frontmatter(text.replace("\r\n", "\n"))
        if not front:
            print(f"  FAILS  {rel}: no frontmatter; `new` writes it correctly")
            bad += 1
            continue
        tid = path.name.split("-", 1)[0].upper()
        if tid not in TECHNIQUES:
            print(f"  FAILS  {rel}: '{tid}' is not a known technique id")
            bad += 1
            continue
        if tid in seen:
            print(f"  FAILS  {rel}: duplicates {seen[tid].name}; one file per technique")
            bad += 1
            continue
        seen[tid] = path
        for field in FIELDS:
            if field not in front:
                print(f"  FAILS  {rel}: missing '{field}' in the frontmatter")
                bad += 1
        scope = front.get("scope")
        if scope and scope != TECHNIQUES[tid][0]:
            print(f"  FAILS  {rel}: scope '{scope}' but {tid} is {TECHNIQUES[tid][0]}")
            bad += 1
        verdict = front.get("verdict", "")
        if verdict == "PENDING":
            print(f"  info   {rel}: still PENDING; phase 1 is not closed")
        elif verdict not in VERDICTS:
            print(f"  FAILS  {rel}: verdict '{verdict}' is not one of {'|'.join(VERDICTS)}")
            bad += 1
        # The one that actually happens: applied, and nobody went back to write the real figure.
        if verdict in ("APPLY", "PARTIAL") and "<filled in after phase 2" in text:
            print(f"  info   {rel}: verdict {verdict} with no real LOC recorded yet; "
                  f"fill '{REAL_LOC}' when the batch lands")
        if verdict in VERDICTS and "<n files>" in text:
            print(f"  FAILS  {rel}: verdict {verdict} but the template placeholders are untouched")
            bad += 1
        lines = len([ln for ln in text.splitlines() if ln.strip()])
        if lines > LINE_CEILING:
            print(f"  FAILS  {rel}: {lines} non-blank lines, the ceiling is {LINE_CEILING}")
            bad += 1
    if not files:
        print(f"  ok     {show(cfg.analysis, cfg.root)} is empty: no analysis has been run yet")
    elif bad == 0:
        print(f"  ok     {len(files)} analysis file(s), all well-formed")
    return 1 if bad else 0


def cmd_config(cfg: Config) -> int:
    _warn(cfg)
    r = cfg.root
    print(f"project root   {r}")
    print(f"harness        {show(cfg.harness, r)}"
          f"{'' if cfg.harness.is_dir() else '  (missing)'}")
    print(f"config file    {show(cfg.path, r)}"
          f"{'' if cfg.path.is_file() else '  (absent: everything below is a default)'}")
    print(f"analysisDir    {show(cfg.analysis, r)}  [{cfg.origin['analysisDir']}]")
    for lang, roots in cfg.sources.items():
        print(f"sources.{lang:6s} [{cfg.origin[f'sources.{lang}']}] {len(roots)} root(s)")
        for root in roots:
            print(f"    {show(root, r)}")
    print(f"uiPackage      {cfg.ui_package or '-'}  [{cfg.origin['uiPackage']}]")
    print(f"exclude        [{cfg.origin['exclude']}] {len(cfg.exclude)} pattern(s)")
    print(f"tests          [{cfg.origin['tests']}] {len(cfg.tests)} pattern(s)")
    print(f"decided        {', '.join(sorted(cfg.decided)) or '-'}")
    print(f"verify         [{cfg.origin['verify']}]")
    for name, command in cfg.verify.items():
        print(f"    {name}: {command}")
    print(f"topology       {'available' if TOPOLOGY.is_file() else 'not installed'}"
          f"  ({TOPOLOGY})")
    return 0


def cmd_surface(cfg: Config, pattern: str, lang: str, tests: bool) -> int:
    _warn(cfg)
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        print(f"invalid regex: {exc}", file=sys.stderr)
        return 1
    langs = list(EXTENSIONS) if lang == "all" else [lang]
    if not any(cfg.sources[lg] for lg in langs):
        print(f"no {lang} source roots found; set `sources.{lang}` in "
              f"{show(cfg.path, cfg.root)}", file=sys.stderr)
        return 1
    scanned = 0
    hits: list[tuple[int, int, pathlib.Path]] = []
    for path in cfg.files(lang, tests):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        count = len(regex.findall(text))
        if count:
            loc = sum(1 for ln in text.splitlines() if ln.strip())
            hits.append((count, loc, path))
    hits.sort(key=lambda h: (-h[0], -h[1], str(h[2])))
    occurrences = sum(h[0] for h in hits)
    loc = sum(h[1] for h in hits)
    print(f"method: regex /{pattern}/ over {scanned} {lang} file(s)"
          f"{' including tests' if tests else ', tests excluded'}, non-blank LOC")
    print(f"Surface: {len(hits)} files, {occurrences} occurrences, {loc} LOC in those files")
    if hits:
        print("Top 10 files by impact:")
        for count, lines, path in hits[:10]:
            print(f"  {count:5d}  {lines:6d} LOC  {show(path, cfg.root)}")
    return 0


def cmd_route(cfg: Config, args: list[str]) -> int:
    if not TOPOLOGY.is_file():
        print("The `topology` skill is not installed next to this one, so there is no derived "
              "map to route with. Install it for a code-derived route; meanwhile, these are the "
              "source roots to search inside (from `reduction.py config`):")
        for lang, roots in cfg.sources.items():
            for root in roots:
                print(f"  {lang:6s} {show(root, cfg.root)}")
        return 0
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(cfg.root))
    return subprocess.call([sys.executable, str(TOPOLOGY)] + (args or ["map"]),
                           cwd=str(cfg.root), env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reduction.py", description="State of a code-reduction campaign (P0 protocol).")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="the 21 techniques and their state")
    p_new = sub.add_parser("new", help="write an analysis skeleton")
    p_new.add_argument("technique")
    p_new.add_argument("--force", action="store_true",
                       help="open a technique the project already decided (only if asked)")
    sub.add_parser("check", help="validate every analysis file and the config")
    sub.add_parser("config", help="print the resolved project facts")
    p_surf = sub.add_parser("surface", help="measure a pattern over the source roots")
    p_surf.add_argument("pattern", help="Python regular expression")
    p_surf.add_argument("--lang", choices=("java", "react", "all"), default="all")
    p_surf.add_argument("--tests", action="store_true", help="include test files")
    p_route = sub.add_parser("route", help="delegate to the topology skill, if installed")
    p_route.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)

    cfg = Config()
    command = ns.command or "list"
    if command == "list":
        return cmd_list(cfg)
    if command == "new":
        return cmd_new(cfg, ns.technique, ns.force)
    if command == "check":
        return cmd_check(cfg)
    if command == "config":
        return cmd_config(cfg)
    if command == "surface":
        return cmd_surface(cfg, ns.pattern, ns.lang, ns.tests)
    return cmd_route(cfg, ns.args)


if __name__ == "__main__":
    sys.exit(main())
