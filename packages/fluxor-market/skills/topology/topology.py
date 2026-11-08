#!/usr/bin/env python3
"""topology.py -- the REAL topology of a workspace, derived from the code.

Architecture rules usually live in prose (a README, an ADR, a rules file), and a document is not
evidence. A README can say "the host mounts apps in an iframe" while someone has just imported an
app's component inside the host: it compiles, it runs, it looks fine, and nothing gives it away.

This reads no document. It builds the package graph from two sources that cannot lie -- the
workspace's `package.json` files and the imports that really exist in the code -- and checks the
invariants against it. The generic ones (no cycles, no phantom dependencies) always run; the
project's layering rules are DATA in `.harness/config/topology.json` (see SKILL.md).

    python3 topology.py map            # the package graph, compact
    python3 topology.py verify         # exit 0 if clean, 1 if there are violations
    python3 topology.py graph          # the package graph as JSON, for other programs
    python3 topology.py route [term]   # domain vocabulary per bounded context / where a concept lives

Project root: $CLAUDE_PROJECT_DIR, else `git rev-parse --show-toplevel`, else the current directory.
Config: $HARNESS_DIR/config/topology.json, else <root>/.harness/config/topology.json (optional).

**It writes nothing.** No cache, no index, no file anywhere. A stale index is worse than no index,
because the agent believes it; this one cannot go stale because it does not exist between calls.
Standard library only; Python 3.9+.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Defaults ───────────────────────────────────────────────────────────────────────────────────

DEFAULT_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"]

# Suffixes that name a PATTERN, not domain vocabulary: when a context's vocabulary is ordered they
# go last, because what routes is `Wallet`, not `WalletRepository`.
DEFAULT_PATTERN_SUFFIXES = ["Repository", "Service", "Resource", "Mapper", "Client", "Scheduler",
                            "Job", "Exception", "Port", "Validator", "Factory", "Config",
                            "Controller", "Handler", "Adapter", "Dto", "Props"]

# Directories never walked when git is unavailable (with git, `.gitignore` already hides them).
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "coverage", ".turbo",
             "target", ".venv", "__pycache__", ".cache", ".output", ".svelte-kit"}

NODE_BUILTINS = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console", "constants",
    "crypto", "dgram", "diagnostics_channel", "dns", "domain", "events", "fs", "http", "http2",
    "https", "inspector", "module", "net", "os", "path", "perf_hooks", "process", "punycode",
    "querystring", "readline", "repl", "stream", "string_decoder", "sys", "timers", "tls",
    "trace_events", "tty", "url", "util", "v8", "vm", "wasi", "worker_threads", "zlib",
}

CONFIG_KEYS = {
    "": {"$schema", "workspaces", "extensions", "exclude", "phantoms", "groups", "forbidden",
         "exceptions", "route"},
    "phantoms": {"scope", "rootDependencies", "ignore"},
    "group": {"packages", "isolated", "leaf", "mayDependOn", "reason"},
    "route": {"maven", "packages", "patternSuffixes", "note"},
    "maven": {"root", "contexts", "domainSuffix", "expectedLayers", "excludeTypePaths"},
}

# A real import, not any string: the specifier has to come right after `from`, `import`,
# `import(`, `require(`, `require.resolve(` or a test runner's `.mock(`-style call. The lookbehind
# keeps `Buffer.from('abc')` and `path.resolve('x')` out.
IMPORT_RE = re.compile(
    r"""(?:(?<![\w$.])from|(?<![\w$.])import\s*\(?|(?<![\w$.])require(?:\.resolve)?\s*\("""
    r"""|\.(?:mock|doMock|unmock|requireActual|importActual|requireMock|importMock)\s*\()"""
    r"""\s*(['"])([^'"\s]+)\1""")
GREP_PREFILTER = r"""(from|import|require|mock|Mock|Actual)[[:space:]]*\(?[[:space:]]*['"]"""
TYPE_ONLY_RE = re.compile(r"^\s*(?:import|export)\s+type\b")
NAME_RE = re.compile(r"^(?:@[a-z0-9-][a-z0-9._~-]*/)?[a-z0-9-][a-z0-9._~-]*$")
SCHEME_RE = re.compile(r"^[A-Za-z][\w+.-]*:")
EXPORT_TYPE_RE = re.compile(
    r"^\s*export\s+(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?"
    r"(?:class|interface|type|enum|const\s+enum)\s+([A-Z][A-Za-z0-9_]*)")


# ── Locating the project and its config ─────────────────────────────────────────────────────────

def git(base: Path, args: list[str], ok=(0,)) -> str | None:
    """stdout of a git command, or None when git is missing or fails (the caller degrades)."""
    try:
        proc = subprocess.run(["git"] + args, cwd=str(base), capture_output=True,
                              encoding="utf-8", errors="replace")
    except Exception:
        return None
    return proc.stdout if proc.returncode in ok else None


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    out = git(Path.cwd(), ["rev-parse", "--show-toplevel"])
    return Path(out.strip()) if out and out.strip() else Path.cwd()


def config_path(root: Path) -> Path:
    harness = os.environ.get("HARNESS_DIR")
    return (Path(harness) if harness else root / ".harness") / "config" / "topology.json"


def load_config(root: Path) -> tuple[dict, list[str], Path]:
    """The config and the problems found in it. A typo that silently disables a rule is worse
    than a loud error, so unknown keys and malformed entries are reported as violations."""
    path = config_path(root)
    if not path.is_file():
        return {}, [], path
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [f"CONFIG: {path} is not valid JSON ({exc})."], path
    if not isinstance(cfg, dict):
        return {}, [f"CONFIG: {path} must hold a JSON object."], path
    problems: list[str] = []

    def unknown(obj, kind: str, where: str) -> None:
        if isinstance(obj, dict):
            for key in sorted(set(obj) - CONFIG_KEYS[kind]):
                problems.append(f"CONFIG: unknown key '{key}' in {where}. Known keys: "
                                f"{', '.join(sorted(CONFIG_KEYS[kind]))}.")

    unknown(cfg, "", "the top level")
    unknown(cfg.get("phantoms"), "phantoms", "'phantoms'")
    route = cfg.get("route") or {}
    unknown(route, "route", "'route'")
    unknown(route.get("maven") if isinstance(route, dict) else None, "maven", "'route.maven'")
    groups = cfg.get("groups") or {}
    if not isinstance(groups, dict):
        problems.append("CONFIG: 'groups' must be an object of {name: {packages: [...]}}.")
        cfg["groups"] = {}
    else:
        for name, g in groups.items():
            if not isinstance(g, dict) or not isinstance(g.get("packages"), list):
                problems.append(f"CONFIG: group '{name}' needs a 'packages' list of globs.")
                groups[name] = {"packages": []}
            unknown(g, "group", f"group '{name}'")
            for other in (g.get("mayDependOn") or []) if isinstance(g, dict) else []:
                if other not in groups:
                    problems.append(f"CONFIG: group '{name}' mayDependOn unknown group '{other}'.")
    for i, rule in enumerate(cfg.get("forbidden") or []):
        if not isinstance(rule, dict) or rule.get("from") not in groups or rule.get("to") not in groups:
            problems.append(f"CONFIG: forbidden[{i}] must be {{\"from\": <group>, \"to\": <group>, "
                            f"\"reason\": ...}} naming groups that exist; got {json.dumps(rule)}.")
    for key in ("phantoms", "route"):
        if key in cfg and not isinstance(cfg[key], dict):
            problems.append(f"CONFIG: '{key}' must be an object; it is ignored.")
            cfg[key] = {}
    scope = (cfg.get("phantoms") or {}).get("scope", "all")
    if scope not in ("all", "workspace", "off"):
        problems.append(f"CONFIG: phantoms.scope must be 'all', 'workspace' or 'off'; got '{scope}'.")
    return cfg, problems, path


# ── Globs ──────────────────────────────────────────────────────────────────────────────────────

_GLOB_CACHE: dict[str, re.Pattern] = {}


def glob_re(pattern: str) -> re.Pattern:
    """A path glob as a regex: `*` stays inside one segment, `**` crosses segments."""
    if pattern in _GLOB_CACHE:
        return _GLOB_CACHE[pattern]
    p = pattern.strip()
    if p.startswith("./"):
        p = p[2:]
    p = p.rstrip("/")
    out, i = [], 0
    while i < len(p):
        if p.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif p.startswith("**", i):
            out.append(".*")
            i += 2
        elif p[i] == "*":
            out.append("[^/]*")
            i += 1
        elif p[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(p[i]))
            i += 1
    rx = re.compile("^" + "".join(out) + "$")
    _GLOB_CACHE[pattern] = rx
    return rx


def matches_any(value: str, patterns) -> bool:
    return any(glob_re(p).match(value) for p in patterns or [])


def expand_dirs(root: Path, patterns: list[str]) -> list[str]:
    """Directories (relative, posix) matching workspace-style globs; `!pattern` removes."""
    include = [p for p in patterns if not p.startswith("!")]
    exclude = [p[1:] for p in patterns if p.startswith("!")]
    found: set[str] = set()
    for pattern in include:
        p = pattern.strip()
        p = p[2:] if p.startswith("./") else p
        segs = [s for s in p.rstrip("/").split("/") if s and s != "."]
        static = []
        for s in segs:
            if any(ch in s for ch in "*?["):
                break
            static.append(s)
        start = root.joinpath(*static) if static else root
        if len(static) == len(segs):
            if start.is_dir():
                found.add("/".join(static) or ".")
            continue
        deep = any("**" in s for s in segs)
        max_depth = len(segs) - len(static)
        rx = glob_re("/".join(segs))
        for dirpath, dirnames, _ in os.walk(start):
            here = Path(dirpath)
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            if not deep and len(here.relative_to(start).parts) >= max_depth:
                dirnames[:] = []
            rel = here.relative_to(root).as_posix()
            if rel != "." and rx.match(rel):
                found.add(rel)
    return sorted(d for d in found if not matches_any(d, exclude))


# ── The workspace ──────────────────────────────────────────────────────────────────────────────

def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def pnpm_patterns(path: Path) -> list[str]:
    """The `packages:` list of `pnpm-workspace.yaml`, without a YAML parser."""
    patterns, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^packages:\s*\[(.*)\]\s*$", line)
        if m:
            return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
        if re.match(r"^packages:\s*(#.*)?$", line):
            inside = True
            continue
        if inside:
            m = re.match(r"^\s+-\s+[\"']?([^\"'#\s]+)[\"']?\s*(#.*)?$", line)
            if m:
                patterns.append(m.group(1))
            elif re.match(r"^\S", line):  # another top-level key: the list is over
                break
    return patterns


def workspace_patterns(root: Path, cfg: dict) -> tuple[list[str], str]:
    if cfg.get("workspaces"):
        return list(cfg["workspaces"]), "config 'workspaces'"
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file():
        return pnpm_patterns(pnpm), "pnpm-workspace.yaml"
    pkg = read_json(root / "package.json") or {}
    ws = pkg.get("workspaces")
    if isinstance(ws, dict):
        ws = ws.get("packages")
    if isinstance(ws, list) and ws:
        return ws, "package.json 'workspaces'"
    return [], ""


def package_manager(root: Path) -> str:
    declared = str((read_json(root / "package.json") or {}).get("packageManager") or "")
    for pm in ("pnpm", "yarn", "bun", "npm"):
        if declared.startswith(pm):
            return pm
    if (root / "pnpm-workspace.yaml").is_file() or (root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (root / "yarn.lock").is_file():
        return "yarn"
    if (root / "bun.lockb").is_file() or (root / "bun.lock").is_file():
        return "bun"
    return "npm"


def declared_of(data: dict) -> set[str]:
    out: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        if isinstance(data.get(key), dict):
            out.update(data[key])
    return out


def load_workspace(root: Path, cfg: dict) -> dict:
    """{packages: name -> {dir, declared, deps}, root_declared, source, notes}."""
    patterns, source = workspace_patterns(root, cfg)
    notes: list[str] = []
    dirs = expand_dirs(root, patterns) if patterns else []
    root_pkg = read_json(root / "package.json")
    if not dirs and isinstance(root_pkg, dict) and root_pkg.get("name"):
        # No workspace: a single-package repository is still worth checking for phantoms.
        dirs, source = ["."], "the root package.json (single package, no workspace)"
    pkgs: dict[str, dict] = {}
    for d in dirs:
        data = read_json(root / d / "package.json")
        if not isinstance(data, dict) or not data.get("name"):
            continue
        name = data["name"]
        if name in pkgs:
            notes.append(f"Two packages are named '{name}' ({pkgs[name]['dir']} and {d}); "
                         f"the second is ignored.")
            continue
        pkgs[name] = {"dir": d, "declared": declared_of(data)}
    for p in pkgs.values():
        p["deps"] = sorted(n for n in p["declared"] if n in pkgs)
    root_declared = declared_of(root_pkg) if isinstance(root_pkg, dict) and "." not in dirs else set()
    return {"packages": pkgs, "root_declared": root_declared, "source": source, "notes": notes}


def owner_index(pkgs: dict[str, dict]):
    """A function path -> owning package (longest directory wins: `a/b` beats `a`)."""
    by_dir = sorted(((p["dir"], n) for n, p in pkgs.items()), key=lambda x: -len(x[0]))

    def owner(path: str) -> str | None:
        for d, n in by_dir:
            if d == "." or path == d or path.startswith(d + "/"):
                return n
        return None
    return owner


# ── Imports ────────────────────────────────────────────────────────────────────────────────────

def source_lines(root: Path, pattern: str, exts: list[str], dirs: list[str]):
    """(path, line) for every line of a versioned or untracked-not-ignored source file under
    `dirs` matching the ERE `pattern`. One `git grep`; without git, a plain walk of those
    directories that skips build output."""
    unique = set(dirs)
    tops = sorted(d for d in unique
                  if not any(o != d and (o == "." or d.startswith(o + "/")) for o in unique))
    specs = ["*" + e for e in exts] + [":(exclude,glob)**/node_modules/**"]
    out = git(root, ["grep", "--untracked", "-I", "-z", "-E", pattern, "--"] + specs, ok=(0, 1))
    if out is not None:
        for line in out.splitlines():
            path, sep, text = line.partition("\0")
            if sep:
                yield path, text
        return
    rx = re.compile(pattern.replace("[[:space:]]", r"\s"))
    walks = [os.walk(root / d) for d in tops]
    for dirpath, dirnames, filenames in (entry for w in walks for entry in w):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if not fname.endswith(tuple(exts)):
                continue
            full = Path(dirpath) / fname
            rel = full.relative_to(root).as_posix()
            try:
                text = full.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line in text.splitlines():
                if rx.search(line):
                    yield rel, line


def scan_imports(root: Path, pkgs: dict[str, dict], cfg: dict) -> list[tuple[str, str, str, bool]]:
    """(owner package, file, specifier, type-only) for every import in the workspace's code."""
    owner = owner_index(pkgs)
    exts = cfg.get("extensions") or DEFAULT_EXTENSIONS
    exclude = cfg.get("exclude") or []
    records = []
    dirs = [p["dir"] for p in pkgs.values()]
    for path, text in source_lines(root, GREP_PREFILTER, exts, dirs):
        if text.lstrip().startswith(("//", "*", "/*")):
            continue  # a mention inside a comment is not an import
        n = owner(path)
        if n is None or (exclude and matches_any(path, exclude)):
            continue
        type_only = bool(TYPE_ONLY_RE.match(text))
        for _, spec in IMPORT_RE.findall(text):
            records.append((n, path, spec, type_only))
    return records


def package_of(spec: str, pkgs: dict[str, dict]) -> str | None:
    """`@scope/ui/fonts` -> `@scope/ui`; `lodash/fp` -> `lodash`; None if not a package name."""
    parts = spec.split("/")
    name = "/".join(parts[:2]) if spec.startswith("@") and len(parts) > 1 else parts[0]
    if name in pkgs:
        return name
    return name if NAME_RE.match(name) else None


# ── Path aliases (tsconfig/jsconfig `paths` and `baseUrl`) ──────────────────────────────────────

def strip_jsonc(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def resolve_extends(spec: str, here: Path, root: Path, pkgs: dict[str, dict]) -> Path | None:
    candidates = []
    if spec.startswith("."):
        candidates.append(here / spec)
    else:
        for name, p in pkgs.items():
            if spec == name or spec.startswith(name + "/"):
                candidates.append(root / p["dir"] / (spec[len(name) + 1:] or "tsconfig.json"))
        candidates += [here / "node_modules" / spec, root / "node_modules" / spec]
    for c in candidates:
        for option in (c, Path(str(c) + ".json"), c / "tsconfig.json"):
            if option.is_file():
                return option
    return None


def tsconfig_options(path: Path, root: Path, pkgs: dict[str, dict], seen: set) -> dict:
    """{'paths': keys, 'baseUrl': dir}, following `extends` the way tsc does (child wins)."""
    if path in seen:
        return {}
    seen.add(path)
    try:
        data = json.loads(strip_jsonc(path.read_text(encoding="utf-8")))
    except Exception:
        return {}
    opts: dict = {}
    ext = data.get("extends")
    for e in ([ext] if isinstance(ext, str) else ext if isinstance(ext, list) else []):
        parent = resolve_extends(e, path.parent, root, pkgs)
        if parent:
            opts.update(tsconfig_options(parent, root, pkgs, seen))
    co = data.get("compilerOptions") or {}
    if isinstance(co.get("baseUrl"), str):
        opts["baseUrl"] = Path(os.path.normpath(str(path.parent / co["baseUrl"])))
    if isinstance(co.get("paths"), dict):
        opts["paths"] = list(co["paths"])
    return opts


def alias_matchers(root: Path, pkgs: dict[str, dict]) -> dict[str, tuple[list, list]]:
    """name -> (alias regexes, baseUrl dirs), from every tsconfig*/jsconfig at the package root
    plus the ones at the project root (tsc falls back to the nearest config up the tree)."""
    def configs(d: Path) -> list[Path]:
        try:
            return sorted(p for p in d.iterdir() if p.is_file() and
                          re.match(r"^(tsconfig.*|jsconfig)\.json$", p.name))
        except Exception:
            return []

    shared = [tsconfig_options(c, root, pkgs, set()) for c in configs(root)]
    result = {}
    for name, p in pkgs.items():
        opts = shared + ([tsconfig_options(c, root, pkgs, set()) for c in configs(root / p["dir"])]
                         if p["dir"] != "." else [])
        regexes = [re.compile("^" + re.escape(k).replace(r"\*", ".*") + "$")
                   for o in opts for k in o.get("paths", [])]
        bases = [o["baseUrl"] for o in opts if "baseUrl" in o]
        result[name] = (regexes, bases)
    return result


def is_local(spec: str, bases: list[Path], cache: dict) -> bool:
    """With `baseUrl`, `components/Button` can be a folder of the package, not a package."""
    first = spec.split("/")[0]
    for b in bases:
        key = (b, first)
        if key not in cache:
            cache[key] = (b / first).exists() or any((b / (first + e)).exists()
                                                     for e in DEFAULT_EXTENSIONS)
        if cache[key]:
            return True
    return False


# ── The checks ─────────────────────────────────────────────────────────────────────────────────

def add_hint(pm: str, owner: str, owner_dir: str, dep: str, workspace: bool) -> str:
    if pm == "pnpm":
        return f"pnpm --filter {owner} add {dep}" + ("@workspace:*" if workspace else "")
    if pm == "yarn":
        return f"yarn workspace {owner} add {dep}"
    if pm == "bun":
        return f"(cd {owner_dir} && bun add {dep})"
    return f"npm install {dep} -w {owner}"


def analyze(root: Path, cfg: dict, ws: dict) -> dict:
    """The graph (declared + imported) and the phantom findings."""
    pkgs = ws["packages"]
    records = scan_imports(root, pkgs, cfg) if pkgs else []
    used: dict[str, set[str]] = {n: set() for n in pkgs}
    ph_cfg = cfg.get("phantoms") or {}
    scope = ph_cfg.get("scope", "all")
    allow_root = ph_cfg.get("rootDependencies", True)
    ignores = ph_cfg.get("ignore") or []
    ignore_used = [False] * len(ignores)
    aliases = alias_matchers(root, pkgs) if scope == "all" else {}
    local_cache: dict = {}
    phantoms: dict[tuple[str, str], str] = {}

    for owner, path, spec, type_only in records:
        if spec.startswith((".", "/", "#", "~")) or SCHEME_RE.match(spec):
            continue  # relative, absolute, subpath import, home alias, or `node:`/`virtual:`...
        dep = package_of(spec, pkgs)
        if dep is None or dep == owner:
            continue  # not a package name, or a self-import
        workspace = dep in pkgs
        if workspace:
            used[owner].add(dep)
        if scope == "off" or (scope == "workspace" and not workspace):
            continue
        if not workspace:
            if dep in NODE_BUILTINS:
                continue
            regexes, bases = aliases.get(owner, ([], []))
            if any(r.match(spec) for r in regexes) or is_local(spec, bases, local_cache):
                continue
        declared = pkgs[owner]["declared"]
        if dep in declared or (allow_root and not workspace and dep in ws["root_declared"]):
            continue
        if type_only and types_package(dep) in declared:
            continue
        hit = False
        for i, ig in enumerate(ignores):
            if isinstance(ig, dict) and (matches_any(dep, [ig.get("import", "")]) or
                                         matches_any(spec, [ig.get("import", "")])) and \
                    (not ig.get("in") or matches_any(owner, [ig["in"]]) or
                     matches_any(pkgs[owner]["dir"], [ig["in"]])):
                if str(ig.get("reason") or "").strip():
                    ignore_used[i] = True
                    hit = True
                    break
        if not hit:
            phantoms.setdefault((owner, dep), path)

    graph = {n: set(p["deps"]) | used[n] for n, p in pkgs.items()}
    return {"graph": graph, "used": used, "phantoms": phantoms, "scope": scope,
            "ignores": ignores, "ignore_used": ignore_used}


def types_package(dep: str) -> str:
    return "@types/" + (dep[1:].replace("/", "__") if dep.startswith("@") else dep)


def group_members(cfg: dict, pkgs: dict[str, dict]) -> dict[str, set[str]]:
    out = {}
    for g, spec in (cfg.get("groups") or {}).items():
        pats = spec.get("packages") or []
        out[g] = {n for n, p in pkgs.items() if matches_any(n, pats) or matches_any(p["dir"], pats)}
    return out


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def dfs(n: str) -> None:
        state[n] = 1
        stack.append(n)
        for m in sorted(graph.get(n, ())):
            if state.get(m, 0) == 0:
                dfs(m)
            elif state.get(m) == 1:
                cyc = stack[stack.index(m):]
                k = cyc.index(min(cyc))
                key = tuple(cyc[k:] + cyc[:k])
                if key not in seen:
                    seen.add(key)
                    cycles.append(list(key) + [key[0]])
        stack.pop()
        state[n] = 2

    sys.setrecursionlimit(max(1000, 4 * len(graph) + 100))
    for n in sorted(graph):
        if state.get(n, 0) == 0:
            dfs(n)
    return cycles


def check(root: Path, cfg: dict, ws: dict, res: dict) -> tuple[list[str], list[str], int]:
    """(violations, notes, number of group rules checked)."""
    pkgs, graph = ws["packages"], res["graph"]
    failures: list[str] = []
    notes: list[str] = []
    pm = package_manager(root)

    # 1. No cycles. The one check that depends on no decision of the project: a cycle breaks a
    #    cold build and makes it impossible to extract a piece.
    for cyc in find_cycles(graph):
        failures.append("CYCLE between workspace packages: " + " -> ".join(cyc))

    # 2. No phantom dependency: imported in the code and not declared in the importer's
    #    package.json. It works through hoisting and breaks the day the package is installed on
    #    its own -- and it turns the declared graph into a lie.
    for (owner, dep), path in sorted(res["phantoms"].items()):
        failures.append(
            f"PHANTOM DEPENDENCY: {owner} imports {dep} (e.g. {path}) and does not declare it "
            f"in its package.json.\n    Fix: "
            + add_hint(pm, owner, pkgs[owner]["dir"], dep, dep in pkgs))
    for ig, used in zip(res["ignores"], res["ignore_used"]):
        if not isinstance(ig, dict) or not str(ig.get("reason") or "").strip():
            failures.append(f"PHANTOM IGNORE WITHOUT A REASON: {json.dumps(ig)}.\n"
                            "    An ignore with no reason written down is not a decision; it does "
                            "not apply until it has one.")
        elif not used:
            notes.append(f"phantoms.ignore {json.dumps(ig.get('import'))} matched nothing: "
                         "it can probably be removed.")

    # 3. The project's layering rules, all from config. Each rule is a list of offending edges.
    groups = cfg.get("groups") or {}
    members = group_members(cfg, pkgs)
    exceptions = cfg.get("exceptions") or []
    exc_used = [False] * len(exceptions)
    valid_exc = []
    for i, e in enumerate(exceptions):
        if not isinstance(e, dict) or not e.get("from") or not e.get("to"):
            failures.append(f"CONFIG: exceptions[{i}] needs 'from', 'to' and 'reason'; "
                            f"got {json.dumps(e)}.")
        elif not str(e.get("reason") or "").strip():
            failures.append(f"EXCEPTION WITHOUT A REASON: {e['from']} -> {e['to']}.\n"
                            "    With no reason written down the exception is wrong, and it "
                            "does not apply until it has one.")
        else:
            valid_exc.append(i)

    def excepted(a: str, b: str) -> bool:
        for i in valid_exc:
            e = exceptions[i]
            if (matches_any(a, [e["from"]]) or matches_any(pkgs[a]["dir"], [e["from"]])) and \
                    (matches_any(b, [e["to"]]) or matches_any(pkgs[b]["dir"], [e["to"]])):
                exc_used[i] = True
                return True
        return False

    def because(reason) -> str:
        return f"\n    Why: {reason}" if reason else ""

    edges = sorted((a, b) for a, bs in graph.items() for b in bs if a != b)
    rules = 0
    for rule in cfg.get("forbidden") or []:
        if not isinstance(rule, dict) or rule.get("from") not in members or rule.get("to") not in members:
            continue
        rules += 1
        src, dst = members[rule["from"]], members[rule["to"]]
        for a, b in edges:
            if a in src and b in dst and not excepted(a, b):
                failures.append(f"FORBIDDEN EDGE ({rule['from']} -> {rule['to']}): {a} -> {b} "
                                f"({pkgs[a]['dir']} -> {pkgs[b]['dir']})." + because(rule.get("reason")))
    for g, spec in groups.items():
        if spec.get("isolated"):
            rules += 1
            for a, b in edges:
                if a in members[g] and b in members[g] and not excepted(a, b):
                    failures.append(f"ISOLATED GROUP '{g}': {a} -> {b}. Members of this group must "
                                    "not depend on each other." + because(spec.get("reason")))
        if spec.get("leaf"):
            rules += 1
            allowed = set(members[g])
            for other in spec.get("mayDependOn") or []:
                allowed |= members.get(other, set())
            for a, b in edges:
                if a in members[g] and b not in allowed and not excepted(a, b):
                    failures.append(f"LEAF GROUP '{g}' depends on a consumer: {a} -> {b}. A leaf may "
                                    "only depend on its own group"
                                    + (" and " + ", ".join(spec["mayDependOn"])
                                       if spec.get("mayDependOn") else "")
                                    + "." + because(spec.get("reason")))
        if not members[g]:
            notes.append(f"group '{g}' matches no package: check its 'packages' globs.")
    for i in valid_exc:
        if not exc_used[i]:
            e = exceptions[i]
            notes.append(f"exception {e['from']} -> {e['to']} excuses no edge that a rule forbids: "
                         "it is stale or the rule it was written for is gone.")
    return failures, notes, rules


# ── Output ─────────────────────────────────────────────────────────────────────────────────────

def short_names(names: set[str]) -> dict[str, str]:
    """`@scope/ui` -> `ui`, unless two packages would share the short name."""
    short = {n: n.split("/")[-1] for n in names}
    clash = {s for s in short.values() if list(short.values()).count(s) > 1}
    return {n: (n if s in clash else s) for n, s in short.items()}


def render_map(cfg: dict, ws: dict, res: dict) -> str:
    pkgs, graph = ws["packages"], res["graph"]
    members = group_members(cfg, pkgs)
    short = short_names(set(pkgs))
    lines = [f"Real workspace topology (from package.json + imports in the code; "
             f"packages from {ws['source']}):", ""]
    width = min(40, max(len(n) for n in pkgs) + 2)
    for n in sorted(pkgs, key=lambda n: (pkgs[n]["dir"].count("/"), pkgs[n]["dir"])):
        tags = [g for g in members if n in members[g]]
        lines.append(f"  {n:<{width}} {pkgs[n]['dir']}" + (f"  [{', '.join(tags)}]" if tags else ""))
        if graph[n]:
            lines.append(f"  {'':<{width}} -> {', '.join(short[d] for d in sorted(graph[n]))}")
    lines += ["", f"  {len(pkgs)} packages, {sum(len(v) for v in graph.values())} edges."]
    return "\n".join(lines)


# ── route: domain vocabulary per bounded context ────────────────────────────────────────────────
# `map` and `verify` check. `route` ROUTES, which attacks a different problem: an agent is slow
# not for lack of capability but because it rediscovers the architecture on every task. A senior
# developer knows "this goes in billing" before opening the editor; this prints that knowledge,
# derived on the fly from the module tree and the type names that really exist.

def pom_modules(pom_dir: Path, seen: set) -> list[Path]:
    """The reactor: this module and every `<module>` below it, recursively."""
    key = os.path.normcase(os.path.normpath(str(pom_dir)))
    if key in seen or not (pom_dir / "pom.xml").is_file():
        return []
    seen.add(key)
    text = re.sub(r"<!--.*?-->", "", (pom_dir / "pom.xml").read_text(encoding="utf-8", errors="replace"),
                  flags=re.S)
    out = [pom_dir]
    for m in re.findall(r"<module>\s*([^<\s]+)\s*</module>", text):
        child = pom_dir / m
        if child.name == "pom.xml" or child.suffix == ".xml":
            child = child.parent
        out += pom_modules(Path(os.path.normpath(str(child))), seen)
    return out


def maven_roots(root: Path, mcfg: dict) -> list[Path]:
    configured = mcfg.get("root")
    if configured:
        return [root / r for r in ([configured] if isinstance(configured, str) else configured)]
    if (root / "pom.xml").is_file():
        return [root]
    listed = git(root, ["ls-files", "-co", "--exclude-standard", "--", "pom.xml", "*/pom.xml"])
    if listed is not None:
        poms = [p for p in listed.splitlines() if p.strip()]
    else:  # no git: walk, but stop descending at the first pom.xml (that is a reactor root)
        poms = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            if "pom.xml" in filenames:
                poms.append((Path(dirpath) / "pom.xml").relative_to(root).as_posix())
                dirnames[:] = []
    dirs = sorted({Path(p).parent.as_posix() for p in poms}, key=lambda d: d.count("/"))
    tops: list[str] = []
    for d in dirs:
        if not any(d == t or d.startswith(t + "/") for t in tops):
            tops.append(d)
    return [root / t for t in tops]


def module_types(module: Path, root: Path, excluded: list[str]) -> list[str]:
    types = []
    for sub in ("src/main/java", "src/main/kotlin"):
        base = module / sub
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.suffix not in (".java", ".kt") or f.stem in ("package-info", "module-info"):
                continue
            if excluded and matches_any(f.relative_to(root).as_posix(), excluded):
                continue
            types.append(f.stem)
    return types


def maven_contexts(root: Path, rcfg: dict) -> dict[str, dict]:
    mcfg = rcfg.get("maven", {})
    if mcfg is False:
        return {}  # explicitly switched off
    mcfg = mcfg if isinstance(mcfg, dict) else {}
    suffix = mcfg.get("domainSuffix", "-domain")
    excluded = mcfg.get("excludeTypePaths") or []
    expected = set(mcfg.get("expectedLayers") or [])
    seen: set = set()
    modules: list[Path] = []
    for r in maven_roots(root, mcfg):
        modules += pom_modules(r, seen)
    rel = {m: Path(os.path.relpath(str(m), str(root))).as_posix() for m in modules}
    ctxs: dict[str, dict] = {}

    def add(ctx: str, label: str, domain: list[Path], others: list[Path], layers: set[str]) -> None:
        key = ctx if ctx not in ctxs else label
        ctxs[key] = {
            "name": ctx, "dir": label, "layers": layers,
            "types": [t for m in domain for t in module_types(m, root, excluded)],
            "others": [t for m in others for t in module_types(m, root, excluded)],
            "missing": sorted(expected - layers) if expected else [],
            "domain_module": bool(domain) and bool(suffix) and domain[0].name.endswith(suffix),
        }

    contexts_glob = mcfg.get("contexts")
    if contexts_glob:
        pats = [contexts_glob] if isinstance(contexts_glob, str) else list(contexts_glob)
        for d in expand_dirs(root, pats):
            inside = [m for m in modules if rel[m] == d or rel[m].startswith(d + "/")]
            ctx = d.split("/")[-1]
            domain = [m for m in inside if m.name.endswith(suffix)]
            others = [m for m in inside if m not in domain]
            layers = {m.name[len(ctx) + 1:] if m.name.startswith(ctx + "-") else m.name
                      for m in inside if rel[m] != d}
            add(ctx, d, domain or others, others if domain else [], layers)
        return ctxs

    for m in modules:
        if not suffix or not m.name.endswith(suffix) or m.name == suffix:
            continue
        ctx = m.name[: -len(suffix)].rstrip("-_.")
        siblings = [s for s in modules if s.parent == m.parent and s.name.startswith(ctx + "-")]
        parent = Path(os.path.relpath(str(m.parent), str(root))).as_posix()
        label = parent if m.parent.name == ctx else f"{parent}/{ctx}-*".lstrip("./")
        add(ctx, label, [m], [s for s in siblings if s != m],
            {s.name[len(ctx) + 1:] for s in siblings})
    return ctxs


def ts_contexts(root: Path, cfg: dict, rcfg: dict) -> dict[str, dict]:
    pats = rcfg.get("packages") or []
    if not pats:
        return {}
    ws = load_workspace(root, cfg)
    pkgs = {n: p for n, p in ws["packages"].items()
            if matches_any(n, pats) or matches_any(p["dir"], pats)}
    if not pkgs:
        return {}
    owner = owner_index(pkgs)
    ctxs = {n: {"name": n, "dir": p["dir"], "types": [], "others": [], "layers": set(),
                "missing": [], "domain_module": True} for n, p in pkgs.items()}
    test_rx = re.compile(r"(\.(test|spec|stories)\.|/__tests__/|/__mocks__/)")
    exclude = cfg.get("exclude") or []
    exts = [".ts", ".tsx", ".mts", ".cts"]
    dirs = [p["dir"] for p in pkgs.values()]
    for path, text in source_lines(root, r"^[[:space:]]*export[[:space:]]", exts, dirs):
        n = owner(path)
        if n is None or test_rx.search(path) or (exclude and matches_any(path, exclude)):
            continue
        m = EXPORT_TYPE_RE.match(text)
        if m:
            ctxs[n]["types"].append(m.group(1))
    return ctxs


def vocabulary(types: list[str], suffixes: tuple, limit: int = 9) -> list[str]:
    """Routing names first: a heuristic, stated as one. The aggregate usually has a short name
    with no pattern suffix (`Wallet`); the noise usually carries one (`JdbcWalletRepository`)."""
    def weight(t: str):
        return (1 if t.endswith(suffixes) else 0, len(t), t)
    return sorted(dict.fromkeys(types), key=weight)[:limit]


def route(root: Path, cfg: dict, cfg_path: Path, term: str | None) -> str:
    rcfg = cfg.get("route") or {}
    suffixes = tuple(rcfg.get("patternSuffixes") or DEFAULT_PATTERN_SUFFIXES)
    sources = [("Maven contexts (from the reactor modules and their type names)",
                maven_contexts(root, rcfg)),
               ("TypeScript packages (from their exported type names)",
                ts_contexts(root, cfg, rcfg))]
    sources = [(label, c) for label, c in sources if c]
    note = rcfg.get("note")
    if not sources:
        mcfg = rcfg.get("maven")
        suffix = mcfg.get("domainSuffix", "-domain") if isinstance(mcfg, dict) else "-domain"
        return (f"Nothing to route: no Maven module whose directory ends in '{suffix}' was found, "
                "and no TypeScript packages are configured.\n"
                f"To enable it, add a 'route' section to {cfg_path}, for example:\n"
                '  {"route": {"maven": {"contexts": "backend/contexts/*", "domainSuffix": "-domain"}}}\n'
                '  {"route": {"packages": ["packages/*"]}}\n'
                "Every key is documented in the skill's SKILL.md (section 'Configuration').")

    if term:
        # WORD BY WORD, not the whole phrase: no type is named after a sentence, so matching
        # the full string would make every multi-word query fail -- and "it does not exist"
        # is worse than no answer, because it invites building what already exists.
        words = [w for w in re.split(r"[^a-z0-9]+", term.lower()) if len(w) > 2] or [term.lower()]
        lines = []
        for label, ctxs in sources:
            hits = {k: [t for t in dict.fromkeys(c["types"]) if any(w in t.lower() for w in words)]
                    for k, c in ctxs.items()}
            hits = {k: v for k, v in hits.items() if v}
            if not hits:
                # Second hop, only when the domain has no answer: a concept can be an OPERATION
                # with no type of its own (an `...UnsubscribeService` in the application layer).
                hits = {k: [t for t in dict.fromkeys(c["others"]) if any(w in t.lower() for w in words)]
                        for k, c in ctxs.items()}
                hits = {k: v for k, v in hits.items() if v}
            for k, types in sorted(hits.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                plural = "type" if len(types) == 1 else "types"
                lines.append(f"  {ctxs[k]['dir']}   ({len(types)} {plural})")
                lines.append(f"      {', '.join(vocabulary(types, suffixes, 8))}")
        if not lines:
            return (f"'{term}' does not appear in any context's vocabulary.\n"
                    "That does not mean it does not exist: it may be a concept with no type of its "
                    "own yet.\nType names are in the language of the code and this does not "
                    "translate: if you searched in another language, try the code's term before "
                    "concluding it does not exist.\nIf you are going to create it, pick a context "
                    "from the map (`topology.py route`) and flag the doubt if it is ambiguous.")
        return "\n".join([f"'{term}' lives in:", ""] + lines + ([f"\n{note}"] if note else []))

    lines = []
    for label, ctxs in sources:
        width = min(28, max(len(c["name"]) for c in ctxs.values()) + 2)
        lines += [f"{label}:", "",
                  f"  {'context':<{width}} domain vocabulary"]
        for k, c in sorted(ctxs.items()):
            flag = ""
            if c["missing"]:
                flag = f"  [missing layer: {', '.join(c['missing'])}]"
            elif not c["domain_module"]:
                flag = "  [no domain module: all its types]"
            vocab = ", ".join(vocabulary(c["types"], suffixes)) or "(no domain types)"
            lines.append(f"  {c['name']:<{width}} {vocab}{flag}")
        lines += ["", f"  {len(ctxs)} contexts.", ""]
    lines.append("For a specific concept: `topology.py route <term>`.")
    if note:
        lines.append(note)
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "verify"
    if command in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if command not in ("map", "verify", "graph", "route"):
        print(f"Unknown command '{command}'. Use: map | verify | graph | route [term].")
        return 2
    root = project_root()
    cfg, problems, cfg_path = load_config(root)

    if command == "route":
        for p in problems:
            print(f"warning: {p}")
        print(route(root, cfg, cfg_path, " ".join(argv[2:]) or None))
        return 0

    ws = load_workspace(root, cfg)
    pkgs = ws["packages"]
    if not pkgs:
        msg = ("No JS/TS workspace found (no pnpm-workspace.yaml, no 'workspaces' in package.json, "
               "no root package.json with a name). Set 'workspaces' in "
               f"{cfg_path} if the packages live elsewhere; `route` may still work.")
        if command == "graph":
            print("{}")
        elif command == "verify" and problems:
            print("\n".join(f"  - {p}" for p in problems))
            return 1
        else:
            print(msg)
        return 0
    res = analyze(root, cfg, ws)

    if command == "map":
        for p in problems + ws["notes"]:
            print(f"warning: {p}")
        print(render_map(cfg, ws, res))
        return 0

    if command == "graph":
        members = group_members(cfg, pkgs)
        print(json.dumps({n: dict({"dir": p["dir"], "deps": sorted(res["graph"][n])},
                                  **({"groups": sorted(g for g in members if n in members[g])}
                                     if members else {}))
                          for n, p in sorted(pkgs.items())}, indent=2))
        return 0

    failures, notes, rules = check(root, cfg, ws, res)
    failures = problems + failures
    notes = ws["notes"] + notes
    checked = f"cycles, phantoms (scope: {res['scope']}), {rules} layering rule(s)"
    if not cfg_path.is_file():
        checked += f" -- no config at {cfg_path}, so only the generic checks ran"
    for n in notes:
        print(f"note: {n}")
    if not failures:
        print(f"Clean topology: {len(pkgs)} packages checked ({checked}).")
        return 0
    print(f"Topology with {len(failures)} violation(s) ({len(pkgs)} packages; {checked}):\n")
    for f in failures:
        print(f"  - {f}")
    print("\nThis does not read the architecture documents: it checks the rules in "
          f"{cfg_path.name} against the real graph.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
