#!/usr/bin/env python3
"""Checks that a project's .harness/ is still wired. See SKILL.md for why each check exists.

Usage:  review.py [--root DIR] [--quiet]

Project root: --root, else $CLAUDE_PROJECT_DIR, else `git rev-parse --show-toplevel`, else the
current directory. Harness: $HARNESS_DIR, else <root>/.harness. Settings: the optional
<harness>/config/review-harness.json (every key is documented in SKILL.md).

Read-only: it never writes, never runs a hook, never touches the network.
Exit 0 when nothing is broken (warnings allowed), 1 when at least one check FAILS.
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Directories that hold generated or third-party copies. A pointer or a doc inside them is the
# same file packaged up, not something anyone reads (a real case: an AGENTS.md kept under a
# resources folder ended up inside the built jar and looked like a second pointer).
GENERATED_DIRS = {
    ".git", "node_modules", "target", ".next", "dist", "build", "out", ".venv", "venv",
    "__pycache__", ".turbo", ".gradle", "coverage", "vendor", ".cache",
}
# Files that describe one piece and are read when opening it: they stay next to the code.
HUMAN_DOCS = {
    "README.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "LICENSE.md", "SECURITY.md",
}
KNOWN_PROVIDERS = ("claude", "codex")
# The convention's layout folders. `.harness/plans/` written with its trailing slash names the
# place where plans go, which is legitimate before the first plan exists.
LAYOUT_DIRS = {
    "rules", "rules/projects", "contracts", "adr", "plans", "reports", "audits", "analysis",
    "references", "market", "skills", "hooks", "config",
}


def default_config(hrel):
    return {
        "providers": None,  # None = autodetect
        "requiredHooks": [],
        "requireHookSplit": False,
        "pointerMaxLines": 12,
        "ignore": [],
        "links": {
            "exclude": [f"{hrel}/plans/**", f"{hrel}/reports/**", f"{hrel}/audits/**"],
            "allowMissing": [],
            "placeholders": ["XX", "000X", "..."],
        },
        "strayDocs": {
            "patterns": ["**/plans/**", "**/specs/**", "**/adr/**", "**/superpowers/**",
                         "**/.tech_proposals/**"],
            "subprojectDocs": False,
            "allow": [],
            "fail": False,
        },
        "hookBench": {
            "casePatterns": ["{stem}.cases*.tsv"],
            "testPatterns": [],
            "runner": "test-hooks.sh",
            "require": "blocking",
            "exempt": [],
        },
        "codex": {"skillsDir": ".agents/skills", "hooksFile": ".codex/hooks.json"},
        "frictionLog": None,
        "installCheck": None,
    }


# --------------------------------------------------------------------------------------------
# Reporting


class Report:
    def __init__(self, quiet):
        self.quiet = quiet
        self.failures = 0
        self.warnings = 0
        self.pending = None  # in quiet mode a header prints only when its section has findings

    def section(self, title):
        if self.quiet:
            self.pending = title
        else:
            print(f"\n{title}")

    def emit(self, line):
        if self.pending:
            print(f"\n{self.pending}")
            self.pending = None
        print(line)

    def ok(self, msg):
        if not self.quiet:
            print(f"  ok     {msg}")

    def info(self, msg):
        if not self.quiet:
            print(f"  info   {msg}")

    def warn(self, msg):
        self.warnings += 1
        self.emit(f"  WARN   {msg}")

    def fail(self, msg):
        self.failures += 1
        self.emit(f"  FAILS  {msg}")

    def issue(self, is_failure, msg):
        (self.fail if is_failure else self.warn)(msg)


# --------------------------------------------------------------------------------------------
# Helpers


def run(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        return p.returncode, p.stdout
    except OSError:
        return 127, ""


def find_root(arg):
    if arg:
        return Path(arg).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    rc, out = run(["git", "rev-parse", "--show-toplevel"], os.getcwd())
    if rc == 0 and out.strip():
        return Path(out.strip()).resolve()
    return Path.cwd().resolve()


def rel(path, root):
    try:
        return Path(os.path.relpath(path, root)).as_posix()
    except ValueError:
        return Path(path).as_posix()


def matches(path, pattern):
    """Glob match on a root-relative POSIX path. `*` and `**` both cross `/`; a leading `**/`
    also matches at the root; a trailing `/**` also matches the directory itself."""
    pattern = pattern.strip()
    if not pattern:
        return False
    candidates = [pattern]
    if pattern.startswith("**/"):
        candidates.append(pattern[3:])
    for pat in candidates:
        if fnmatch.fnmatchcase(path, pat):
            return True
        if pat.endswith("/**") and fnmatch.fnmatchcase(path, pat[:-3]):
            return True
    return False


def matches_any(path, patterns):
    return any(matches(path, p) for p in patterns)


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


IMPORT_RE = re.compile(r"^\s*@(\S+)")


def imports_of(path):
    """`@path` lines outside code fences, the form every agent runtime expands."""
    out, fence = [], False
    for line in read(path).splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            m = IMPORT_RE.match(line)
            if m:
                out.append(m.group(1))
    return out


LOAD_RE = re.compile(r"^load:\s*(\S+)\s*$", re.M)


def rule_load(path):
    """How a rule reaches a session: `always` (imported), or the `load:` its front matter declares
    (`scoped`: loaded by its `paths:` from the provider's rules folder; `on-demand`: read when the
    index says)."""
    text = read(path)
    if not text.startswith("---\n"):
        return "always"
    end = text.find("\n---\n", 4)
    m = LOAD_RE.search(text[4:end]) if end > 0 else None
    return m.group(1) if m else "always"


def resolve_import(importer, target):
    """An import resolves relative to the directory of the file that holds it."""
    target = os.path.expanduser(target)
    if os.path.isabs(target):
        return os.path.normpath(target)
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(importer)), target))


def same(a, b):
    try:
        return os.path.realpath(a) == os.path.realpath(b)
    except OSError:
        return False


def nonblank_lines(path):
    return sum(1 for line in read(path).splitlines() if line.strip())


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            fm[key] = "" if val in (">", "|", ">-", "|-", ">+", "|+") else val.strip("\"'")
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return None


def symlink_as_text(path):
    """A checkout with core.symlinks=false turns a symlink into a one-line text file holding the
    target. It looks present and is broken for every agent."""
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    text = read(path).strip()
    if text and "\n" not in text and len(text) < 200 and not text.startswith("@") \
            and re.fullmatch(r"[A-Za-z0-9_./-]+", text):
        return text
    return None


# --------------------------------------------------------------------------------------------
# The review


class Review:
    def __init__(self, root, harness, report):
        self.root = root
        self.harness = harness
        self.hrel = rel(harness, root)
        self.r = report
        self.in_git = run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                          str(root))[0] == 0
        self.cfg = default_config(self.hrel)
        self.config_path = harness / "config" / "review-harness.json"
        self.wired = {}  # hook file name -> set of events, across providers
        self._files = None

    # -- config -------------------------------------------------------------------------------

    def load_config(self):
        r = self.r
        r.section("0. Configuration")
        if not self.config_path.is_file():
            r.ok(f"no {rel(self.config_path, self.root)}: defaults and autodetection")
            return
        try:
            data = json.loads(read(self.config_path))
            if not isinstance(data, dict):
                raise ValueError("the top level must be an object")
        except ValueError as exc:
            r.fail(f"{rel(self.config_path, self.root)} is not valid JSON ({exc}); defaults used")
            return
        for key, val in data.items():
            if key.startswith("$"):
                continue
            if key not in self.cfg:
                r.warn(f"unknown key `{key}` in review-harness.json (typo?) — ignored")
                continue
            if isinstance(self.cfg[key], dict) and isinstance(val, dict):
                for sub in val:
                    if sub not in self.cfg[key] and not sub.startswith("$"):
                        r.warn(f"unknown key `{key}.{sub}` in review-harness.json — ignored")
                self.cfg[key].update({k: v for k, v in val.items() if k in self.cfg[key]})
            else:
                self.cfg[key] = val
        r.ok(f"read {rel(self.config_path, self.root)}")

    # -- file inventory -------------------------------------------------------------------------

    def files(self):
        """Root-relative POSIX paths: tracked plus untracked-not-ignored when in git (a new file
        not committed yet still counts), else a walk that skips generated directories."""
        if self._files is not None:
            return self._files
        out = []
        if self.in_git:
            rc, stdout = run(["git", "-C", str(self.root), "ls-files", "-co", "--exclude-standard",
                              "-z"], str(self.root))
            if rc == 0:
                out = [p for p in stdout.split("\0") if p]
        if not out:
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in GENERATED_DIRS]
                for f in filenames:
                    out.append(rel(os.path.join(dirpath, f), self.root))
        ignore = self.cfg["ignore"]
        self._files = sorted({
            p for p in out
            if not (set(p.split("/")[:-1]) & GENERATED_DIRS) and not matches_any(p, ignore)
        })
        return self._files

    def in_harness(self, p):
        return p == self.hrel or p.startswith(self.hrel + "/")

    def git_mode(self, path):
        if not self.in_git:
            return None
        rc, out = run(["git", "-C", str(self.root), "ls-files", "-s", "--", rel(path, self.root)],
                      str(self.root))
        return out.split()[0] if rc == 0 and out.strip() else None

    # -- 1. bridge ----------------------------------------------------------------------------

    def providers(self):
        conf = self.cfg["providers"]
        if conf:
            chosen = [p for p in conf if p in KNOWN_PROVIDERS]
            for p in conf:
                if p not in KNOWN_PROVIDERS:
                    self.r.warn(f"provider `{p}` is not known (known: {', '.join(KNOWN_PROVIDERS)})")
            return chosen, True
        found = []
        if (self.root / ".claude").is_dir() or os.path.lexists(self.root / "CLAUDE.md"):
            found.append("claude")
        if (self.root / ".codex").is_dir() or (self.root / ".agents").is_dir():
            found.append("codex")
        return found, False

    def harness_skills(self):
        d = self.harness / "skills"
        if not d.is_dir():
            return []
        return sorted(e.name for e in d.iterdir() if not e.name.startswith(".")
                      and (e.is_dir() or e.is_symlink()))

    def check_skills_link(self, link_rel, required):
        link = self.root / link_rel
        target = self.harness / "skills"
        skills = self.harness_skills()
        if not skills:
            self.r.warn(f"{self.hrel}/skills is empty or missing: nothing to bridge to {link_rel}")
            return
        text = symlink_as_text(link)
        if text is not None:
            self.r.fail(f"{link_rel} is a text file holding `{text}`: the symlink was checked out "
                        f"with core.symlinks=false (enable symlinks and check it out again)")
        elif os.path.islink(link) and not os.path.exists(link):
            self.r.fail(f"{link_rel} is a broken symlink ({os.readlink(link)})")
        elif os.path.exists(link) and same(link, target):
            how = "symlink" if os.path.islink(link) else "junction/equivalent"
            self.r.ok(f"{link_rel} -> {self.hrel}/skills ({how})")
        elif link.is_dir():
            missing = [s for s in skills if not os.path.exists(link / s)]
            if missing:
                self.r.fail(f"{link_rel} is a directory, not a link to {self.hrel}/skills, and "
                            f"lacks: {', '.join(missing)} (those skills are invisible)")
            else:
                self.r.warn(f"{link_rel} is a directory, not a link to {self.hrel}/skills: every "
                            f"new skill must be added by hand (link the directory instead)")
        else:
            self.r.issue(required, f"{link_rel} does not exist: the runtime discovers none of the "
                                   f"{len(skills)} skill(s) in {self.hrel}/skills")

    def parse_hook_config(self, path, provider):
        """Returns {event: [command, ...]} from a hooks JSON document (Claude Code shape), or None
        when the file is not JSON; the caller then falls back to scanning the raw text."""
        try:
            data = json.loads(read(path))
        except ValueError:
            return None
        hooks = data.get("hooks") if isinstance(data, dict) else None
        events = {}
        if isinstance(hooks, dict):
            for event, groups in hooks.items():
                for group in groups if isinstance(groups, list) else []:
                    inner = group.get("hooks", []) if isinstance(group, dict) else []
                    for h in inner if isinstance(inner, list) else []:
                        if isinstance(h, dict) and isinstance(h.get("command"), str):
                            events.setdefault(event, []).append(h["command"])
        return events

    def check_hook_commands(self, source_rel, events, provider):
        # A hook is the project's own (`<harness>/hooks/<name>`) or installed from the catalog
        # (`<harness>/market/hooks/<name>`, which `marketplace.py install` writes and checks).
        hook_re = re.compile(re.escape(self.hrel) + r"/((?:market/)?hooks/[A-Za-z0-9_.\-/]+)")
        seen = set()
        for event, commands in sorted(events.items()):
            for cmd in commands:
                refs = hook_re.findall(cmd)
                if not refs:
                    self.r.warn(f"{source_rel} [{event}] runs `{cmd[:70]}`, which lives outside "
                                f"{self.hrel}/hooks and {self.hrel}/market/hooks (the bridge should "
                                f"carry wiring, not logic)")
                    continue
                if provider == "claude" and "CLAUDE_PROJECT_DIR" not in cmd:
                    if re.search(r"(?:^|[\s\"'=])(?:/|[A-Za-z]:[\\/])\S*" + re.escape(self.hrel),
                                 cmd):
                        self.r.warn(f"{source_rel} [{event}] uses one machine's absolute path; "
                                    f"write \"$CLAUDE_PROJECT_DIR\"/{self.hrel}/hooks/...")
                    else:
                        self.r.warn(f"{source_rel} [{event}] uses a relative path: it breaks when "
                                    f"the session's working directory moves; prefix "
                                    f"\"$CLAUDE_PROJECT_DIR\"/")
                for ref in refs:
                    # The project's own hooks keep their bare name: benches and requiredHooks use it.
                    name = ref[len("hooks/"):] if ref.startswith("hooks/") else ref
                    self.wired.setdefault(name, set()).add(event)
                    seen.add(name)
        for name in sorted(seen):
            where = name if name.startswith("market/") else f"hooks/{name}"
            path = self.harness / where
            mode = self.git_mode(path)
            if not path.is_file():
                self.r.fail(f"{source_rel} points at {self.hrel}/{where}, which does not exist")
            elif os.name != "nt" and not os.access(path, os.X_OK):
                self.r.fail(f"{self.hrel}/{where} is not executable (chmod +x): the runtime "
                            f"cannot run it and the guardrail is silently off")
            elif mode and mode not in ("100755", "120000"):
                self.r.fail(f"{self.hrel}/{where} is committed without the executable bit "
                            f"(git update-index --chmod=+x): a fresh clone cannot run it")
            else:
                self.r.ok(f"hook {name} ({', '.join(sorted(self.wired[name]))})")
        return seen

    def check_bridge(self):
        r = self.r
        r.section("1. Bridge (runtime -> harness)")
        providers, explicit = self.providers()
        self.active_providers = providers
        hook_scripts = [p for p in (self.harness / "hooks").glob("*")
                        if p.is_file() and not p.name.endswith(".tsv")] \
            if (self.harness / "hooks").is_dir() else []
        if not providers:
            if self.harness_skills() or hook_scripts:
                r.warn("no agent bridge detected (.claude/, CLAUDE.md, .codex/, .agents/): no "
                       "runtime discovers the harness skills or hooks; set `providers` in the config "
                       "if this is wrong")
            else:
                r.ok("no bridge and nothing to bridge (no skills, no hooks)")
            return
        r.info(f"providers: {', '.join(providers)} ({'configured' if explicit else 'autodetected'})")

        events_all = {}
        if "claude" in providers:
            self.check_skills_link(".claude/skills", True)
            settings = self.root / ".claude" / "settings.json"
            if not settings.is_file():
                r.issue(bool(hook_scripts), ".claude/settings.json does not exist: no hook is wired"
                        + ("" if hook_scripts else " (and the harness has no hooks yet)"))
            else:
                events = self.parse_hook_config(settings, "claude")
                if events is None:
                    r.fail(".claude/settings.json is not valid JSON: Claude Code ignores all of it")
                else:
                    r.ok(".claude/settings.json exists")
                    seen = self.check_hook_commands(".claude/settings.json", events, "claude")
                    if not seen and hook_scripts:
                        r.fail(f".claude/settings.json wires no hook from {self.hrel}/hooks")
                    for e, cmds in events.items():
                        events_all.setdefault(e, []).extend(cmds)

        if "codex" in providers:
            cx = self.cfg["codex"]
            self.check_skills_link(cx["skillsDir"], explicit)
            hooks_file = self.root / cx["hooksFile"]
            if hooks_file.is_file():
                events = self.parse_hook_config(hooks_file, "codex")
                if events is None:  # not JSON (e.g. TOML): scan the text for references
                    refs = re.findall(re.escape(self.hrel) + r"/(?:market/)?hooks/[A-Za-z0-9_.\-/]+",
                                      read(hooks_file))
                    events = {"(unparsed)": refs}
                self.check_hook_commands(cx["hooksFile"], events, "codex")
            elif hook_scripts:
                r.warn(f"{cx['hooksFile']} does not exist: Codex runs none of the harness hooks "
                       f"(AGENTS.md still carries the rules)")

        for name in self.cfg["requiredHooks"]:
            if name in self.wired:
                r.ok(f"required hook {name} is wired")
            else:
                r.fail(f"required hook {name} (review-harness.json) is not wired by any provider")

        # The split: prompt = preparation, pre = invariants, post/stop = closing cycles. Missing
        # half means the harness protects only part of what it claims to.
        if self.wired and "claude" in providers:
            evs = set(events_all)
            halves = [
                ("UserPromptSubmit", {"UserPromptSubmit"}, "the invariants do not arrive ahead of "
                                                           "the prompt"),
                ("PreToolUse", {"PreToolUse"}, "no invariant is checked before acting"),
                ("PostToolUse/Stop", {"PostToolUse", "Stop", "SubagentStop"},
                 "nobody closes the testing/cleanup/documentation cycle"),
            ]
            for label, names, why in halves:
                if evs & names:
                    r.ok(f"{label} wired")
                else:
                    r.issue(bool(self.cfg["requireHookSplit"]),
                            f"no {label} hook from the harness: {why}")

    # -- 2. versioned bridge ------------------------------------------------------------------

    def check_versioned(self):
        r = self.r
        r.section("2. Versioned bridge")
        if not self.in_git:
            r.warn("not a git repository: cannot tell whether the bridge travels to a fresh clone")
            return
        paths = ["AGENTS.md", f"{self.hrel}/INDEX.md"]
        providers = getattr(self, "active_providers", [])
        if "claude" in providers:
            paths += ["CLAUDE.md", ".claude/settings.json", ".claude/skills"]
        if "codex" in providers:
            paths += [self.cfg["codex"]["skillsDir"], self.cfg["codex"]["hooksFile"]]
        for p in paths:
            if not os.path.lexists(self.root / p):
                continue  # its absence is reported by the section that needs it
            rc, _ = run(["git", "-C", str(self.root), "ls-files", "--error-unmatch", "--", p],
                        str(self.root))
            if rc == 0:
                r.ok(f"{p} is versioned")
                continue
            ignored = run(["git", "-C", str(self.root), "check-ignore", "-q", "--", p],
                          str(self.root))[0] == 0
            if ignored:
                r.fail(f"{p} is ignored by .gitignore: a fresh clone arrives without it (add a "
                       f"negation, e.g. `!{p}`, and `!{p.split('/')[0]}/` if its directory is "
                       f"ignored)")
            else:
                r.warn(f"{p} is not committed yet")

    # -- 3. load chain ------------------------------------------------------------------------

    def check_load_chain(self):
        r = self.r
        r.section("3. Load chain")
        agents = self.root / "AGENTS.md"
        claude = self.root / "CLAUDE.md"
        index = self.harness / "INDEX.md"
        providers = getattr(self, "active_providers", [])

        if not agents.is_file():
            r.fail("AGENTS.md does not exist at the root: no agent reaches the harness")
        else:
            if any(same(resolve_import(agents, t), index) for t in imports_of(agents)):
                r.ok(f"AGENTS.md imports {self.hrel}/INDEX.md")
            else:
                r.fail(f"AGENTS.md does not import @{self.hrel}/INDEX.md (prose is not an import)")

        if "claude" in providers or os.path.lexists(claude):
            text = symlink_as_text(claude)
            if not os.path.lexists(claude):
                r.fail("CLAUDE.md does not exist: Claude Code reads CLAUDE.md, not AGENTS.md")
            elif text is not None:
                r.fail(f"CLAUDE.md is a text file holding `{text}`: a symlink checked out with "
                       f"core.symlinks=false")
            elif same(claude, agents):
                r.ok("CLAUDE.md -> AGENTS.md (symlink)")
            elif any(same(resolve_import(claude, t), agents) for t in imports_of(claude)):
                r.ok("CLAUDE.md imports AGENTS.md")
            else:
                r.fail("CLAUDE.md neither links nor imports AGENTS.md: Claude Code and the other "
                       "agents receive different rules")

        if not index.is_file():
            r.fail(f"{self.hrel}/INDEX.md does not exist")
            return
        idx_imports = [(t, resolve_import(index, t)) for t in imports_of(index)]
        for t, path in idx_imports:
            if not os.path.exists(path):
                r.fail(f"INDEX.md imports @{t}, which does not exist")

        rules_dir = self.harness / "rules"
        rules = sorted(rules_dir.glob("*.md")) if rules_dir.is_dir() else []
        if not rules:
            r.warn(f"{self.hrel}/rules/ has no rules: the index loads nothing always-on")
        index_text = read(index)
        for rule in rules:
            load = rule_load(rule)
            named = f"rules/{rule.name}" in index_text
            if any(same(path, rule) for _, path in idx_imports):
                r.ok(f"rule loaded: {rule.name}")
            elif load == "scoped":
                copy = self.root / ".claude" / "rules" / rule.name
                if "claude" in providers and not copy.is_file():
                    r.fail(f"scoped rule rules/{rule.name} has no .claude/rules/{rule.name} copy: "
                           f"Claude Code never loads it")
                elif not named:
                    r.fail(f"scoped rule rules/{rule.name} is not named in INDEX.md: an agent "
                           f"without a path trigger never learns it exists")
                else:
                    r.ok(f"rule loaded by path: {rule.name}")
            elif load == "on-demand":
                if named:
                    r.ok(f"rule on demand, named in INDEX.md: {rule.name}")
                else:
                    r.fail(f"on-demand rule rules/{rule.name} is not named in INDEX.md: nobody "
                           f"knows to read it")
            else:
                r.fail(f"rule NOT imported by INDEX.md: rules/{rule.name} (a rule nobody imports "
                       f"does not exist; or declare `load: scoped` / `load: on-demand`)")

        inv = self.harness / "INVARIANTS.md"
        if inv.is_file():
            if any(same(path, inv) for _, path in idx_imports):
                r.ok("INVARIANTS.md imported by INDEX.md")
            else:
                r.fail("INVARIANTS.md exists but INDEX.md does not import it with @ (only a "
                       "runtime that runs the preparation hook would see it)")
        else:
            r.warn(f"no {self.hrel}/INVARIANTS.md: the preparation hook has no commandments to "
                   f"put up front (optional)")

        # Context budget: anything else imported by the index rides in every session, forever.
        for t, path in idx_imports:
            if not os.path.exists(path):
                continue
            if same(path, inv) or any(same(path, rule) for rule in rules):
                continue
            r.warn(f"INDEX.md imports @{t}: the index should import only rules/*.md and "
                   f"INVARIANTS.md; link anything else as text")

        # Subproject rules nobody imports.
        proj_dir = rules_dir / "projects"
        if proj_dir.is_dir():
            importers = [self.root / p for p in self.files()
                         if Path(p).name in ("AGENTS.md", "CLAUDE.md") and not self.in_harness(p)]
            targets = [resolve_import(f, t) for f in importers for t in imports_of(f)]
            for rule in sorted(proj_dir.glob("*.md")):
                if any(same(t, rule) for t in targets):
                    r.ok(f"project rule loaded: projects/{rule.name}")
                else:
                    r.warn(f"rules/projects/{rule.name} is imported by no subproject AGENTS.md: "
                           f"it reaches no agent")

    # -- 4. pointers with no body ---------------------------------------------------------------

    def check_pointers(self):
        r = self.r
        limit = int(self.cfg["pointerMaxLines"])
        r.section(f"4. AGENTS.md / CLAUDE.md are pointers (at most {limit} non-blank lines)")
        providers = getattr(self, "active_providers", [])
        pointers = [p for p in self.files()
                    if Path(p).name in ("AGENTS.md", "CLAUDE.md") and not self.in_harness(p)]
        if not pointers:
            r.warn("no AGENTS.md or CLAUDE.md found")
        for p in pointers:
            path = self.root / p
            if os.path.islink(path):
                if not os.path.exists(path):
                    r.fail(f"{p} is a broken symlink")
                continue  # it is its target; the target is checked on its own
            if symlink_as_text(path) is not None:
                if p != "CLAUDE.md":  # the root one is reported by the load chain
                    r.fail(f"{p} is a text file holding `{read(path).strip()}`: a symlink checked "
                           f"out with core.symlinks=false")
                continue
            lines = nonblank_lines(path)
            imps = imports_of(path)
            broken = [t for t in imps if not os.path.exists(resolve_import(path, t))]
            for t in broken:
                r.fail(f"{p} imports @{t}, which does not exist")
            if lines > limit:
                r.fail(f"{p} has {lines} lines of content: the body belongs in {self.hrel}/rules/ "
                       f"(a copied rule goes stale in the copy nobody reads)")
            elif not imps:
                r.fail(f"{p} imports nothing with @ (prose is not a guarantee it gets read)")
            elif not broken:
                r.ok(f"{p} is a pointer ({lines} lines)")
            # Claude Code reads CLAUDE.md, not AGENTS.md, inside a subdirectory.
            if Path(p).name == "AGENTS.md" and p != "AGENTS.md" and "claude" in providers:
                sibling = path.parent / "CLAUDE.md"
                if not os.path.lexists(sibling):
                    r.fail(f"{p} has no sibling CLAUDE.md: Claude Code never loads this "
                           f"subproject's rules (add CLAUDE.md -> AGENTS.md)")
            if Path(p).name == "CLAUDE.md" and p != "CLAUDE.md":
                sibling = path.parent / "AGENTS.md"
                if sibling.is_file() and not any(same(resolve_import(path, t), sibling)
                                                 for t in imps):
                    r.fail(f"{p} does not import its sibling AGENTS.md: two pointers that can "
                           f"drift apart")

    # -- 5. links -------------------------------------------------------------------------------

    def check_links(self):
        r = self.r
        r.section(f"5. Backticked links into {self.hrel}/")
        lc = self.cfg["links"]
        token_re = re.compile(r"`(" + re.escape(self.hrel) + r"/[^`\s]*)`")
        placeholders = lc["placeholders"]
        allow = {a.rstrip("/") for a in lc["allowMissing"]}
        broken = {}
        sources = [p for p in self.files() if p.endswith(".md") and not matches_any(p, lc["exclude"])]
        for src in sources:
            for m in token_re.finditer(read(self.root / src)):
                raw = re.sub(r"(#.*|:\d+(-\d+)?)$", "", m.group(1))
                target = raw.rstrip("/.,;:)")
                if raw.endswith("/") and target[len(self.hrel) + 1:] in LAYOUT_DIRS:
                    continue  # names where a kind of file goes, even before the first one exists
                if re.search(r"[<>*{}\[\]$|]", target) or any(ph in target for ph in placeholders) \
                        or "…" in target:
                    continue  # a template or a pattern, not a path
                if target in allow or target == self.hrel:
                    continue
                if not os.path.lexists(self.root / target):
                    broken.setdefault(target, []).append(src)
        for target, srcs in sorted(broken.items()):
            where = ", ".join(sorted(set(srcs))[:2]) + (" ..." if len(set(srcs)) > 2 else "")
            r.fail(f"broken link: {target} (in {where})")
        if not broken:
            r.ok(f"no broken links in {len(sources)} Markdown file(s)")

    # -- 6. stray AI docs ---------------------------------------------------------------------

    def check_stray_docs(self):
        r = self.r
        sc = self.cfg["strayDocs"]
        r.section("6. AI documentation outside the harness")
        patterns = list(sc["patterns"])
        if sc["subprojectDocs"]:
            for p in self.files():
                if Path(p).name == "AGENTS.md" and "/" in p and not self.in_harness(p):
                    patterns.append(p.rsplit("/", 1)[0] + "/docs/**")
        stray = [p for p in self.files()
                 if p.endswith(".md") and not self.in_harness(p) and Path(p).name not in HUMAN_DOCS
                 and matches_any(p, patterns) and not matches_any(p, sc["allow"])]
        for p in stray:
            r.issue(bool(sc["fail"]), f"{p}: plans, specs and decisions that direct the work go in "
                                      f"{self.hrel}/ (a folder like this grows into an archive "
                                      f"nobody reads)")
        if not stray:
            r.ok(f"no Markdown matches {len(patterns)} stray-doc pattern(s)")

    # -- 7. hook benches ----------------------------------------------------------------------

    def check_benches(self):
        r = self.r
        hc = self.cfg["hookBench"]
        r.section("7. Hook test benches")
        hooks_dir = self.harness / "hooks"
        if not hooks_dir.is_dir():
            r.warn(f"no {self.hrel}/hooks/: the harness has no executable rules (optional)")
            return
        runner = hooks_dir / hc["runner"] if hc["runner"] else None
        runner_text = read(runner) if runner and runner.is_file() else ""

        def bench_for(name, tests=True):
            stem = name.rsplit(".", 1)[0]
            for pat in hc["casePatterns"]:
                found = sorted(hooks_dir.glob(pat.format(stem=stem, name=name)))
                if found:
                    return found[0].name
            if runner_text and re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(name), runner_text):
                return hc["runner"]
            # A hook whose behavior is a script rather than a decision (a heartbeat, a lock) is
            # tested by an ordinary test file, named after it, instead of a case file.
            for pat in hc["testPatterns"] if tests else []:
                found = sorted(self.root.glob(pat.format(stem=stem, name=name)))
                if found:
                    return rel(found[0], self.root)
            return None

        require = hc["require"]
        for name in sorted(self.wired):
            if not (hooks_dir / name).is_file():
                continue  # already reported as missing by the bridge check
            blocking = "PreToolUse" in self.wired[name]
            bench = bench_for(name)
            if bench:
                r.ok(f"{name}: bench {bench}")
            elif name in hc["exempt"]:
                r.ok(f"{name}: no bench (exempt in review-harness.json)")
            else:
                required = require == "all" or (require == "blocking" and blocking)
                kind = "blocking hook" if blocking else "non-blocking hook: test it by hand"
                r.issue(required, f"{name} has no test bench ({kind}); a hook without cases rots "
                                  f"at its first false positive")
        if runner and not runner.is_file() and self.wired:
            r.info(f"no {hc['runner']} runner in {self.hrel}/hooks/")
        # A bench whose hook nobody wires is a guardrail that looks alive and is not.
        for script in sorted(p for p in hooks_dir.iterdir() if p.is_file()):
            if script.name.endswith(".tsv") or script.name == hc["runner"] \
                    or script.name in self.wired:
                continue
            bench = bench_for(script.name, tests=False)
            if bench and bench != hc["runner"]:
                r.warn(f"{script.name} has cases ({bench}) but no provider wires it: a dead "
                       f"guardrail")

    # -- 8. skills ------------------------------------------------------------------------------

    def check_skills(self):
        r = self.r
        r.section("8. Skills")
        d = self.harness / "skills"
        if not d.is_dir():
            r.warn(f"no {self.hrel}/skills/ (optional)")
            return
        for name in self.harness_skills():
            entry = d / name
            if os.path.islink(entry) and not os.path.exists(entry):
                r.fail(f"skills/{name} is a broken symlink ({os.readlink(entry)})")
                continue
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                r.fail(f"skills/{name} has no SKILL.md: the runtime does not load it")
                continue
            fm = frontmatter(read(skill_md))
            if fm is None:
                r.fail(f"skills/{name}/SKILL.md has no YAML frontmatter (--- name/description ---)")
                continue
            problems = False
            if fm.get("name") != name:
                r.fail(f"skills/{name}/SKILL.md declares name `{fm.get('name')}`: it must match "
                       f"its folder")
                problems = True
            desc = fm.get("description", "")
            if not desc:
                r.fail(f"skills/{name}/SKILL.md has no description: it is the only thing the "
                       f"agent reads when deciding to use it")
                problems = True
            elif len(desc) > 1024:
                r.warn(f"skills/{name}: description is {len(desc)} characters (limit 1024)")
            if name and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
                r.warn(f"skills/{name}: names are lowercase letters, digits and hyphens")
            if not problems:
                r.ok(f"skills/{name}")

    # -- 9. market ------------------------------------------------------------------------------

    def check_market(self):
        r = self.r
        market = self.harness / "market"
        if not market.is_dir():
            return
        r.section("9. Market copy")
        # An atom is TWO things: its inventory entry and its .md. With only one, it does not
        # exist (the engine drops an entry with no file; nobody sees a file with no entry), and
        # nothing says so: that role is simply never chosen.
        try:
            inv = json.loads(read(market / "inventory.json"))
        except ValueError as exc:
            r.fail(f"market/inventory.json cannot be read ({exc})")
            return
        checked = 0
        for kind, entries in sorted(inv.items()) if isinstance(inv, dict) else []:
            if not isinstance(entries, list) or not (market / kind).is_dir():
                continue
            checked += 1
            names = {e.get("name") for e in entries if isinstance(e, dict) and e.get("name")}
            files = {p.stem for p in (market / kind).glob("*.md")} - {"AGENTS", "CLAUDE", "README"}
            for n in sorted(names - files):
                r.fail(f"market/{kind}/{n}: entry in inventory.json with no .md (the engine drops it)")
            for n in sorted(files - names):
                r.fail(f"market/{kind}/{n}.md: file with no entry in inventory.json (invisible)")
            if names == files:
                r.ok(f"{kind}: {len(names)} atoms, entries and files match")
        if not checked:
            r.warn("market/inventory.json lists no kind that has a folder next to it")
        lex = market / "lexicon.json"
        if not lex.is_file():
            r.warn("market/lexicon.json is missing: with no vocabulary, scoring barely reaches "
                   "any atom")
        else:
            try:
                json.loads(read(lex))
                r.ok("lexicon.json is valid")
            except ValueError as exc:
                r.fail(f"market/lexicon.json is not valid JSON ({exc})")

    # -- 9b. installed copies --------------------------------------------------------------------

    def check_install(self):
        """A harness installed from a catalog carries copies nobody may edit; the installer's own
        read-only check says whether they still match their source. Run as an argv, never a shell."""
        cmd = self.cfg["installCheck"]
        if not cmd:
            return
        r = self.r
        r.section("9b. Installed copies match their source")
        if not isinstance(cmd, list) or not all(isinstance(c, str) and c for c in cmd):
            r.fail("installCheck must be a non-empty list of strings (an argv, no shell)")
            return
        shown = " ".join(cmd)
        try:
            p = subprocess.run(cmd, cwd=str(self.root), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
        except FileNotFoundError:
            r.warn(f"installCheck: `{cmd[0]}` not found: the installed copies were NOT checked")
            return
        except subprocess.TimeoutExpired:
            r.warn(f"installCheck: `{shown}` took more than 120s: NOT checked")
            return
        if p.returncode == 0:
            r.ok(f"`{shown}`: installed copies match their source")
            return
        r.fail(f"`{shown}` exits {p.returncode}: an installed copy drifted from its source "
               "(fix the source and reinstall; never edit the copy)")
        lines = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]
        for ln in lines[:8]:
            print(f"           {ln}")
        if len(lines) > 8:
            print(f"           ... {len(lines) - 8} more line(s)")

    # -- 10. friction ---------------------------------------------------------------------------

    def check_friction(self):
        path = self.cfg["frictionLog"]
        if not path:
            return
        r = self.r
        r.section("10. Recorded friction (informational, never fails)")
        # `$TMPDIR` is often unset; expandvars would leave it literal and never find the log.
        os.environ.setdefault("TMPDIR", tempfile.gettempdir())
        path = Path(os.path.expandvars(os.path.expanduser(path)))
        if not path.is_file() or path.stat().st_size == 0:
            r.ok(f"no blocks recorded on this machine ({path})")
            return
        rows = [line.split("\t") for line in read(path).splitlines() if line.strip()]
        counts = {}
        for row in rows:
            if len(row) > 1:
                counts[row[1]] = counts.get(row[1], 0) + 1
        print(f"  info   {len(rows)} block(s) recorded since {rows[0][0]}, by hook:")
        for hook, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"           {n:4d}  {hook}")
        print("           (if one hook dominates, check whether those are false positives and add "
              "the case to its bench before touching the rule)")


def main():
    ap = argparse.ArgumentParser(description="Check that a project's .harness/ is still wired.")
    ap.add_argument("--root", help="project root (default: $CLAUDE_PROJECT_DIR, git top level, cwd)")
    ap.add_argument("-q", "--quiet", action="store_true", help="print only WARN and FAILS lines")
    args = ap.parse_args()

    root = find_root(args.root)
    env_h = os.environ.get("HARNESS_DIR")
    harness = (root / env_h).resolve() if env_h and not os.path.isabs(env_h) else \
        Path(env_h).resolve() if env_h else root / ".harness"

    report = Report(args.quiet)
    print(f"review-harness: {root}")
    if not harness.is_dir():
        report.fail(f"no harness at {harness}: nothing to review (see the harness convention)")
        print("\nHarness with 1 failure(s).")
        return 1

    rv = Review(root, harness, report)
    rv.load_config()
    rv.check_bridge()
    rv.check_versioned()
    rv.check_load_chain()
    rv.check_pointers()
    rv.check_links()
    rv.check_stray_docs()
    rv.check_benches()
    rv.check_skills()
    rv.check_market()
    rv.check_install()
    rv.check_friction()

    print()
    tail = f", {report.warnings} warning(s)" if report.warnings else ""
    if report.failures == 0:
        print(f"Harness wired: no failures{tail}.")
        return 0
    print(f"Harness with {report.failures} failure(s){tail}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
