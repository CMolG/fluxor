#!/usr/bin/env python3
"""The checks of a CEET pack that are not judgment calls, as an executable (plan item 2.4).

A pack's `hooks/*.md` are judgment calls: an agent reads them at a git event. What can be checked
mechanically is in `hooks/checks.json`, rendered from the person's stated rules:

- `secrets`: no credential in an added line (built-in patterns);
- `commitMessage`: the first line of a commit message matches the person's pattern;
- `forbidden`: a pattern the person bans never appears in an added line of the files a glob selects.

  ceet_check.py bench --pack <pack>             every check against its cases and the current tree:
                                                only a check that starts GREEN may be wired in
  ceet_check.py pre-commit --pack <pack>        git pre-commit hook: staged added lines
  ceet_check.py commit-msg --pack <pack> FILE   git commit-msg hook
  ceet_check.py claude-code --pack <pack>       Claude Code PreToolUse hook (reads the payload on
                                                stdin; exit 2 blocks a `git commit` that fails)

Every mode fails open: a missing git, an unreadable config or an unexpected payload lets the work
through with a note on stderr, because a broken guardrail must never block every session. The
render copies this file into the pack's `bin/`, so the pack is self-contained. Standard library only
(Python 3.9+).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

# Built-in credential patterns. The bench builds its samples at run time so no literal secret-like
# string sits in the repository.
SECRET_PATTERNS = {
    "aws-access-key": r"\bAKIA[0-9A-Z]{16}\b",
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY",
    "github-token": r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
    "slack-token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
    "google-api-key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "stripe-live-key": r"\b[sr]k_live_[0-9A-Za-z]{24,}\b",
    "anthropic-key": r"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "assigned-secret": r"(?i)\b(api[_-]?key|secret|passw(or)?d|token)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]",
}
SKIP_MESSAGE = re.compile(r"^(Merge |Revert |fixup! |squash! |amend! )")


def note(message: str) -> None:
    print(f"ceet_check: {message}", file=sys.stderr)


def load_checks(pack: Path) -> dict:
    return json.loads((pack / "hooks" / "checks.json").read_text(encoding="utf-8"))


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def staged_added_lines(cwd: Path | None = None) -> list[tuple[str, str]]:
    """(path, line) for every added line in the staged diff."""
    out = git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff", cwd=cwd)
    found, current = [], None
    for line in out.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and not line.startswith("+++") and current:
            found.append((current, line[1:]))
    return found


def secret_hits(lines: list[tuple[str, str]]) -> list[str]:
    hits = []
    for path, line in lines:
        for name, pattern in SECRET_PATTERNS.items():
            if re.search(pattern, line):
                hits.append(f"{path}: looks like a credential ({name})")
    return hits


def path_selected(path: str, globs: list[str]) -> bool:
    return not globs or any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(Path(path).name, g) for g in globs)


def forbidden_hits(lines: list[tuple[str, str]], rules: list[dict]) -> list[str]:
    hits = []
    for rule in rules:
        pattern = re.compile(rule["pattern"])
        for path, line in lines:
            if path_selected(path, rule.get("paths", [])) and pattern.search(line):
                hits.append(f"{path}: {rule['message']} [{rule.get('source', '')}]")
    return hits


def message_problem(message: str, rule: dict | None) -> str | None:
    if not rule:
        return None
    lines = [l for l in message.splitlines() if not l.startswith("#")]
    first = next((l for l in lines if l.strip()), "")
    if SKIP_MESSAGE.match(first):
        return None
    if not re.search(rule["pattern"], first):
        example = f" Example: {rule['example']}" if rule.get("example") else ""
        return f"commit message {first!r} does not match the format [{rule.get('source', '')}].{example}"
    return None


def run_line_checks(checks: dict, lines: list[tuple[str, str]]) -> list[str]:
    problems = []
    if checks.get("secrets"):
        problems += secret_hits(lines)
    problems += forbidden_hits(lines, checks.get("forbidden", []))
    return problems


# ─── The bench ──────────────────────────────────────────────────────────────────────────────────

def secret_samples() -> tuple[list[str], list[str]]:
    blocks = [
        "aws_key = " + "AKIA" + "IOSFODNN7" + "EXAMPLE",
        "-----BEGIN " + "RSA PRIVATE KEY-----",
        "token: " + "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8",
        'API_KEY = "' + "s3cr3t" + "Value0123456789" + '"',
    ]
    passes = [
        "const retries = 3;",
        "api_key = os.environ['API_KEY']",
        "# the token is read from the vault at start-up",
        "password_hash = argon2.hash(password)",
    ]
    return blocks, passes


def tracked_lines(cwd: Path | None = None) -> list[tuple[str, str]]:
    """Every line of every tracked text file, to tell whether a check starts red on this tree."""
    lines = []
    for path in git("ls-files", cwd=cwd).splitlines():
        full = (cwd or Path.cwd()) / path
        try:
            data = full.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000] or len(data) > 2_000_000:
            continue
        for line in data.decode("utf-8", errors="replace").splitlines():
            lines.append((path, line))
    return lines


def bench(checks: dict, repo: Path | None) -> dict:
    report: dict[str, dict] = {}
    current = None
    if repo is not None:
        try:
            current = tracked_lines(repo)
        except (OSError, subprocess.CalledProcessError):
            current = None
    if checks.get("secrets"):
        blocks, passes = secret_samples()
        missed = [b for b in blocks if not secret_hits([("sample", b)])]
        false = [p for p in passes if secret_hits([("sample", p)])]
        existing = secret_hits(current) if current is not None else []
        report["secrets"] = {"green": not missed and not false and not existing,
                             "missed": len(missed), "falsePositives": false, "redOnTree": existing[:10]}
    rule = checks.get("commitMessage")
    if rule:
        problems = []
        try:
            re.compile(rule["pattern"])
        except re.error as exc:
            problems.append(f"invalid pattern: {exc}")
        else:
            if rule.get("example") and message_problem(rule["example"], rule):
                problems.append("the person's own example does not match the pattern")
            if not message_problem("x", rule):
                problems.append("the pattern accepts a one-letter message: too loose to be a check")
        report["commitMessage"] = {"green": not problems, "problems": problems}
    for item in checks.get("forbidden", []):
        problems = []
        try:
            re.compile(item["pattern"])
        except re.error as exc:
            problems.append(f"invalid pattern: {exc}")
        else:
            sample_path = (item.get("paths") or ["sample.txt"])[0].replace("**/", "").replace("*", "sample")
            if not item.get("blocks") or not forbidden_hits([(sample_path, item["blocks"])], [item]):
                problems.append("needs a `blocks` line that the pattern catches")
            if not item.get("passes") or forbidden_hits([(sample_path, item["passes"])], [item]):
                problems.append("needs a `passes` line that the pattern lets through")
            if current is not None:
                red = forbidden_hits(current, [item])
                if red:
                    problems.append(f"red on the current tree ({len(red)} hit(s), e.g. {red[0]}): open a work item "
                                    "instead of wiring it")
        report[f"forbidden:{item.get('id')}"] = {"green": not problems, "problems": problems}
    return report


# ─── Modes ──────────────────────────────────────────────────────────────────────────────────────

def cmd_bench(args) -> int:
    checks = load_checks(args.pack)
    report = bench(checks, None if args.no_tree else Path.cwd())
    print(json.dumps(report, indent=2))
    return 0 if all(entry["green"] for entry in report.values()) else 1


def cmd_pre_commit(args) -> int:
    try:
        checks = load_checks(args.pack)
        problems = run_line_checks(checks, staged_added_lines())
    except Exception as exc:  # fail open
        note(f"skipped ({exc})")
        return 0
    for p in problems:
        print(f"blocked: {p}", file=sys.stderr)
    return 1 if problems else 0


def cmd_commit_msg(args) -> int:
    try:
        checks = load_checks(args.pack)
        problem = message_problem(Path(args.file).read_text(encoding="utf-8"), checks.get("commitMessage"))
    except Exception as exc:  # fail open
        note(f"skipped ({exc})")
        return 0
    if problem:
        print(f"blocked: {problem}", file=sys.stderr)
        return 1
    return 0


def commit_messages(command: str) -> list[str]:
    """The -m/--message values of a `git commit` command line, when it has any."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return []
    messages = []
    for i, token in enumerate(tokens):
        if token in ("-m", "--message") and i + 1 < len(tokens):
            messages.append(tokens[i + 1])
        elif token.startswith("--message="):
            messages.append(token.split("=", 1)[1])
        elif token.startswith("-m") and len(token) > 2 and not token.startswith("--"):
            messages.append(token[2:])
    return messages


def cmd_claude_code(args) -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "") if payload.get("tool_name") == "Bash" else ""
        if not re.search(r"\bgit\b[^|;&]*\bcommit\b", command):
            return 0
        checks = load_checks(args.pack)
        problems = run_line_checks(checks, staged_added_lines())
        messages = commit_messages(command)
        if messages:
            problem = message_problem("\n\n".join(messages), checks.get("commitMessage"))
            if problem:
                problems.append(problem)
    except Exception as exc:  # fail open
        note(f"skipped ({exc})")
        return 0
    if problems:
        print("The pack's checks block this commit:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 2
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("bench", cmd_bench), ("pre-commit", cmd_pre_commit),
                       ("commit-msg", cmd_commit_msg), ("claude-code", cmd_claude_code)):
        p = sub.add_parser(name)
        p.add_argument("--pack", required=True, type=Path)
        if name == "commit-msg":
            p.add_argument("file")
        if name == "bench":
            p.add_argument("--no-tree", action="store_true", help="skip scanning the current tree")
        p.set_defaults(func=func)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
