#!/usr/bin/env python3
"""Heuristic friction scanner for the ux-psychology skill.

Flags CANDIDATES for manual review in HTML/JSX/TSX/Vue/Svelte/Astro. It hands down no verdicts:
it looks for hints with regular expressions and prefers a false positive to a false negative.
Nothing it reports replaces the invariant sweep done by hand.

UI copy is matched in both English and Spanish, so interfaces in either language get scanned.

Usage:
    python3 scan_friction.py PATH [PATH...] [--json] [--only IDS] [--fail-on LEVEL]

No external dependencies: standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

EXTENSIONS = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
IGNORED_DIRS = {"node_modules", "dist", "build", ".git", ".next", ".nuxt", "vendor",
                "coverage", "__pycache__", ".venv", "out", "target"}
LEVELS = ["low", "medium", "high", "blocking"]


@dataclass
class Finding:
    check: str
    invariant: str
    severity: str
    file: str
    line: int
    message: str
    excerpt: str
    where_to_look: str


# The detection patterns below match UI copy (button labels, banners, error messages) in BOTH
# English and Spanish. The Spanish alternatives are functional data, not untranslated text: they
# keep Spanish-language interfaces covered. Each pattern lists the Spanish copy first and the
# English copy second; code tokens (autoplay, confirm(), disabled...) are language-neutral.

# --- Per-line rules ---------------------------------------------------------
# (id, invariant, severity, regex, message, reference)
LINE_RULES = [
    ("C01", "INV-10", "high",
     r"(?i)("
     # Spanish UI copy
     r"cuenta\s*atr[áa]s|expira\s+en|caduca\s+en|"
     r"[úu]ltim[oa]s?\s+\d+\s+(unidades|plazas|art[íi]culos)|solo\s+quedan|s[óo]lo\s+quedan|"
     r"date\s+prisa|\d+\s+personas\s+(est[áa]n\s+)?viendo|"
     # English UI copy
     r"countdown|time\s*left|timeleft|expires\s+in|\bends\s+in|offer\s+ends|last\s+chance|"
     r"only\s+\d+\s+(\w+\s+)?left|almost\s+gone|selling\s+fast|limited\s+time|hurry|"
     r"\d+\s+people\s+(are\s+)?(viewing|looking)|"
     # Code identifiers
     r"urgency|scarcity)",
     "Urgency or scarcity: verify that the data is real and that the user can check it.",
     "regulation-and-ethics.md §1"),

    ("C02", "INV-11", "high",
     r"(?i)("
     # Spanish UI copy
     r">\s*no,?\s+(gracias,?\s+)?(prefiero|no\s+quiero|paso\s+de|me\s+da\s+igual|"
     r"seguir[ée]|renuncio)|"
     # English UI copy
     r">\s*no,?\s+(thanks|thank\s+you),?\s+i|"
     r">\s*no,?\s+i('?d|\s+would)\s+rather|>\s*no,?\s+i\s+(prefer|like|enjoy|love|don'?t)|"
     r"i\s+don'?t\s+want\s+to\s+(save|improve|grow|learn|succeed)|"
     r"i('?ll|\s+will)\s+(pay\s+full\s+price|stay\s+uninformed|miss\s+out))",
     "Possible confirmshaming: the decline option must be neutral and symmetrical.",
     "component-catalog.md § Consent and permissions"),

    ("C03", "INV-03", "medium",
     r"(?i)(autoplay|<marquee|animation-iteration-count\s*:\s*infinite|"
     r"setInterval\s*\([^)]*(modal|popup|banner|toast|dialog))",
     "Element that can hijack attention without the user asking for it.",
     "cognitive-frameworks.md §5"),

    ("C04", "INV-05", "high",
     r"(?i)("
     # Spanish UI copy
     r"algo\s+(ha\s+)?(sali(do|[óo])|fue|fall[óo])\s+mal|algo\s+no\s+(ha\s+)?funcion|"
     r"ha\s+ocurrido\s+un\s+error|error\s+inesperado|error\s+desconocido|"
     # English UI copy
     r"something\s+went\s+wrong|unexpected\s+error|unknown\s+error|"
     r"an\s+error\s+(has\s+)?occurred|oops[!,.])",
     "Generic error message: it lacks the cause and a way out.",
     "component-catalog.md § States: loading, empty and error"),

    ("C05", "INV-12", "medium",
     r"(?i)\b(window\.)?confirm\s*\(",
     "Native confirm(): a weak microboundary that becomes automatic within a few weeks. "
     "Use undo if the action is reversible, or typed confirmation if it's serious.",
     "cognitive-frameworks.md §9"),

    ("C06", "INV-05", "low",
     r"(?i)<button[^>]*\bdisabled\b(?![^>]*(title=|aria-describedby=|aria-label=))",
     "Disabled control with no visible reason: it opens a gulf of execution.",
     "component-catalog.md § States: loading, empty and error"),

    ("C07", "INV-02", "medium",
     r"(?i)<input(?![^>]*type\s*=\s*[\"']?(hidden|checkbox|radio|submit|button|range|file|color))"
     r"(?![^>]*autocomplete)",
     "Field without autocomplete: it forces users to retype data the system or the browser "
     "already has.",
     "regulation-and-ethics.md §2 (WCAG 1.3.5 / 3.3.7)"),

    ("C08", "INV-02", "medium",
     r"(?i)<input(?=[^>]*placeholder)(?![^>]*aria-label)(?![^>]*\bid\s*=)",
     "Placeholder with no associated label: the instruction disappears as the user types "
     "and they have to remember it.",
     "component-catalog.md § Forms and sign-up"),

    ("C09", "INV-10", "medium",
     # "acepto" is Spanish UI copy ("I accept"); "accept"/"agree" are the English equivalents.
     r"(?i)(checked\s*=\s*[\"']?(true|checked)|defaultChecked)"
     r"(?![^>]*(required|terms|acepto|accept|agree))",
     "Pre-checked box: make sure it isn't an optional purpose accepted by default.",
     "regulation-and-ethics.md §1"),
]

# --- Per-file rules ---------------------------------------------------------
# Identifiers and copy in both languages (borrar/eliminar = delete/remove, Cuenta = Account,
# Proyecto = Project, Todo = All; deshacer = undo; "escribe el nombre" = "type the name";
# "estás seguro" = "are you sure"; consentimiento/rgpd/privacidad = consent/GDPR/privacy;
# aceptar todo = accept all; rechazar/denegar = reject/deny; solo necesarias = only necessary).
RE_DESTRUCTIVE = re.compile(
    r"(?i)\b(handle|on)?(delete|remove|destroy|wipe|purge|erase|borrar|eliminar)"
    r"(Account|Project|User|Repo|Item|All|Workspace|Cuenta|Proyecto|Todo)?\s*[=(:]")
RE_SAFEGUARD = re.compile(
    r"(?i)(confirm|undo|type\s+the\s+name|typeToConfirm|are\s+you\s+sure|"
    r"deshacer|escrib[ei]\s+el\s+nombre|est[áa]s\s+seguro|"
    r"dialog|alertdialog|modal)")
RE_CONSENT = re.compile(
    r"(?i)(cookie|consent|gdpr|privacy|tracking|consentimiento|rgpd|privacidad)")
RE_STRONG_ACCEPT = re.compile(
    r"(?i)<button[^>]*(primary|cta|btn-accept|accept-all|allow-all|aceptar[-_]?tod)")
RE_WEAK_REJECT = re.compile(
    r"(?i)<(a|span|button)[^>]*(link|ghost|text-only|secondary|underline|muted|tertiary)[^>]*>"
    r"[^<]*(reject|decline|deny|refuse|only\s+necessary|necessary\s+only|essential\s+only|"
    r"rechazar|denegar|solo\s+necesari)")
RE_FORM = re.compile(r"(?i)(<form|onSubmit|handleSubmit|type\s*=\s*[\"']?submit)")
RE_FEEDBACK = re.compile(r"(?i)(aria-live|role\s*=\s*[\"']?(status|alert)|toast|snackbar|"
                         r"aria-invalid|aria-errormessage)")
RE_INTERACTIVE = re.compile(r"(?i)<(button|a\s|input|select|textarea)|role\s*=\s*[\"']?button")

DENSITY_THRESHOLD = 30


def files_to_scan(paths: list[str]) -> list[str]:
    found: list[str] = []
    for path in paths:
        if os.path.isfile(path):
            found.append(path)
            continue
        for base, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            for filename in filenames:
                if os.path.splitext(filename)[1].lower() in EXTENSIONS:
                    found.append(os.path.join(base, filename))
    return sorted(found)


def truncate(text: str, limit: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def scan_lines(path: str, lines: list[str]) -> list[Finding]:
    findings = []
    for number, line in enumerate(lines, start=1):
        for check, inv, sev, pattern, message, reference in LINE_RULES:
            if re.search(pattern, line):
                findings.append(Finding(check, inv, sev, path, number, message,
                                        truncate(line), reference))
    return findings


def scan_file(path: str, content: str, lines: list[str]) -> list[Finding]:
    findings = []

    destructive = RE_DESTRUCTIVE.search(content)
    if destructive and not RE_SAFEGUARD.search(content):
        line = content[: destructive.start()].count("\n") + 1
        findings.append(Finding(
            "C10", "INV-12", "blocking", path, line,
            "Destructive action with no detectable microboundary or undo in the file.",
            truncate(lines[line - 1] if line <= len(lines) else ""),
            "component-catalog.md § Destructive and irreversible actions"))

    if RE_CONSENT.search(content):
        strong = RE_STRONG_ACCEPT.search(content)
        if strong and RE_WEAK_REJECT.search(content):
            line = content[: strong.start()].count("\n") + 1
            findings.append(Finding(
                "C11", "INV-09", "blocking", path, line,
                "Asymmetric consent: accept as the primary button and reject as a link "
                "or secondary control.",
                truncate(lines[line - 1] if line <= len(lines) else ""),
                "regulation-and-ethics.md §1"))

    if RE_FORM.search(content) and not RE_FEEDBACK.search(content):
        findings.append(Finding(
            "C12", "INV-05", "high", path, 1,
            "Form with no accessible feedback region (aria-live / role=status / "
            "aria-invalid): a gulf of evaluation after submitting.",
            "", "component-catalog.md § States: loading, empty and error"))

    interactive = len(RE_INTERACTIVE.findall(content))
    if interactive > DENSITY_THRESHOLD:
        findings.append(Finding(
            "C13", "INV-01", "medium", path, 1,
            f"High interactive density ({interactive} controls): check whether each one "
            f"supports a real step of the task or whether progressive disclosure is called for.",
            "", "cognitive-frameworks.md §1"))

    return findings


def scan(paths: list[str], only: set[str] | None) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    files = files_to_scan(paths)
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue
        lines = content.splitlines()
        findings.extend(scan_lines(path, lines))
        findings.extend(scan_file(path, content, lines))

    if only:
        findings = [f for f in findings if f.check in only or f.invariant in only]

    findings.sort(key=lambda f: (-LEVELS.index(f.severity), f.file, f.line))
    return findings, len(files)


def report(findings: list[Finding], total_files: int) -> str:
    out = ["ux-psychology · friction scan",
           f"files scanned: {total_files} · candidates: {len(findings)}", ""]
    if not findings:
        out.append("No candidates. Remember: an absence of hints doesn't validate the design;")
        out.append("the sweep of the 14 invariants is done by hand.")
        return "\n".join(out)

    for f in findings:
        out.append(f"[{f.severity.upper():<9}] {f.check} · {f.invariant} · "
                   f"{f.file}:{f.line}")
        out.append(f"    {f.message}")
        if f.excerpt:
            out.append(f"    › {f.excerpt}")
        out.append(f"    → {f.where_to_look}")
        out.append("")

    summary = {level: sum(1 for f in findings if f.severity == level) for level in LEVELS}
    out.append("Summary: " + " · ".join(f"{n}: {summary[n]}" for n in reversed(LEVELS)))
    out.append("These are heuristic candidates, not verdicts. Confirm each one by reading the code.")
    return "\n".join(out)


def main() -> int:
    # The report uses non-ASCII symbols (·, ›, →) and echoes UI copy from the scanned files;
    # force UTF-8 so printing it on a legacy Windows code page (cp1252) doesn't crash.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Detects candidates for undue friction, dark patterns and gulfs of "
                    "evaluation in interface code (UI copy in English and Spanish).")
    parser.add_argument("paths", nargs="+", help="files or directories to scan")
    parser.add_argument("--json", action="store_true", help="JSON output for CI")
    parser.add_argument("--only", help="filter by check ids or invariants, comma-separated")
    parser.add_argument("--fail-on", choices=LEVELS,
                        help="exit with code 1 if there are findings at this level or higher")
    args = parser.parse_args()

    only = {s.strip().upper() for s in args.only.split(",")} if args.only else None
    findings, total = scan(args.paths, only)

    if args.json:
        print(json.dumps({"files": total, "findings": [asdict(f) for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print(report(findings, total))

    if args.fail_on:
        minimum = LEVELS.index(args.fail_on)
        if any(LEVELS.index(f.severity) >= minimum for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
