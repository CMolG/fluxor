#!/usr/bin/env python3
"""
atoms — inspect and reassemble the market's atom set.

It is a thin CLI: all the scoring logic lives in the market's `motor.py`, which is the very
module the preparation hook uses. If this had its own copy of the scoring, the skill would end
up lying about what the hook actually mounts.

The engine is looked up, first match wins:
  1. <harness>/market/motor.py of the current project (harness = $HARNESS_DIR, else
     <root>/.harness; root = $CLAUDE_PROJECT_DIR, else the git top-level, else the cwd);
  2. ../../market/motor.py relative to this file, which is `<harness>/market/` when the skill is
     installed at `<harness>/skills/atoms/`, and the top-level `market/` of the repository that
     publishes the market.

  atoms.py mount   "<intent>" [--cwd PATH] [--full] [--max-mods N]
  atoms.py why     "<intent>" [--cwd PATH]      scores and thresholds behind the choice
  atoms.py list    [roles|mods|steps] [--json]
  atoms.py show    <id>                         an atom's full text
  atoms.py current [--session ID]               what the hook has mounted
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=3)
        if out.returncode == 0 and out.stdout.strip() and Path(out.stdout.strip()).is_dir():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def find_engine():
    root = project_root()
    env = os.environ.get("HARNESS_DIR")
    harness = (Path(env) if Path(env).is_absolute() else root / env) if env else root / ".harness"
    for candidate in (harness / "market" / "motor.py",
                      Path(__file__).resolve().parents[2] / "market" / "motor.py"):
        if candidate.is_file():
            return candidate
    return None


def load_engine():
    engine = find_engine()
    if engine is None:
        print("error: no market engine found. Expected <harness>/market/motor.py in this project "
              "(harness = $HARNESS_DIR or .harness), or market/motor.py two levels above this "
              "skill. Copy the market into the harness to enable atoms.", file=sys.stderr)
        raise SystemExit(2)
    spec = importlib.util.spec_from_file_location("motor", engine)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd_mount(args, m):
    cwd = Path(args.cwd) if args.cwd else Path.cwd()
    r = m.resolve(args.intent, cwd, args.max_mods)
    if r is None:
        print("no catalog available")
        return 1
    if args.full:
        print(m.render(r, full=True))
        return 0
    print(f"role  : {r['role']['id']} — {r['role']['description']}")
    print(f"mods  : {', '.join(x['id'] for x in r['mods']) or '(none)'}")
    print(f"steps : {' → '.join(p['id'] for p in r['steps']) or '(none)'}")
    if r["evidence"]:
        print(f"signals: {', '.join(r['evidence'][:12])}")
    print(f"\nfiles: {m.MARKET_REL}/roles/{r['role']['id']}.md")
    for x in r["mods"]:
        print(f"       {m.MARKET_REL}/mods/{x['id']}.md")
    return 0


def cmd_why(args, m):
    cwd = Path(args.cwd) if args.cwd else Path.cwd()
    r = m.resolve(args.intent, cwd, args.max_mods)
    if r is None:
        print("no catalog available")
        return 1
    role_ranked, mod_ranked, step_ranked = r["ranked"]
    print(f"tokens from the intent : {' '.join(sorted(r['raw']))}")
    print(f"added by the lexicon   : {' '.join(sorted(r['expanded'] - r['raw'])) or '(none)'}")
    print(f"project signals        : {', '.join(r['evidence'][:12]) or '(none)'}")
    print(f"\nthresholds: minimum {m.MIN_POINTS} points, relative floor 50% of the leader, "
          f"cap {args.max_mods} mods. Signals only break exact ties.")
    print(f"config    : {m.display(m.CONFIG_FILE)}"
          + ("" if m.CONFIG_FILE.is_file() else " (absent, defaults in use)"))
    print(f"invariants: {m.display(m.INVARIANTS_FILE)}"
          + ("" if m.INVARIANTS_FILE.is_file() else " (absent, skipped)"))
    for label, ranked, chosen in (
        ("ROLES", role_ranked, {r["role"]["id"]}),
        ("MODS", mod_ranked, {x["id"] for x in r["mods"]}),
        ("STEPS", step_ranked, {p["id"] for p in r["steps"]}),
    ):
        print(f"\n{label}")
        for item, pts in ranked[:6]:
            print(f"  {'*' if item['id'] in chosen else ' '} {pts:>4}  {item['id']}")
    if r["uncovered"]:
        print(f"\nnot covered by the catalog: {', '.join(sorted(r['uncovered'])[:12])}")
    return 0


def cmd_list(args, m):
    catalog = m.load_catalog()
    kinds = [args.kind] if args.kind else ["roles", "mods", "steps"]
    if args.json:
        print(json.dumps({t: [{k: v for k, v in i.items() if k != "path"} for i in catalog[t]]
                          for t in kinds}, ensure_ascii=False, indent=2))
        return 0
    for kind in kinds:
        print(f"\n{kind.upper()}  ({len(catalog[kind])})")
        for item in sorted(catalog[kind], key=lambda i: i["id"]):
            extra = []
            if item.get("exclusive_group"):
                extra.append(f"group={item['exclusive_group']}")
            if item.get("domains"):
                extra.append("/".join(item["domains"]))
            tail = f"  [{' '.join(extra)}]" if extra else ""
            print(f"  {item['id']:<24} {item['description'][:86]}{tail}")
    print()
    return 0


def cmd_show(args, m):
    catalog = m.load_catalog()
    for kind in ("roles", "mods", "steps"):
        for item in catalog[kind]:
            if item["id"] == args.id:
                print(f"# source: {item['path']}\n")
                print(m.read_text(item["path"]))
                return 0
    print(f"error: there is no atom named {args.id!r}", file=sys.stderr)
    return 2


def cmd_current(args, m):
    if args.session:
        files = [m.state_path(args.session)]
    else:
        files = sorted(m.STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)             if m.STATE_DIR.is_dir() else []
    if not files or not files[0].is_file():
        print(f"the hook has not mounted anything for this project ({m.ROOT}) yet")
        return 0
    print(json.dumps(m.read_json(files[0], {}), ensure_ascii=False, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(prog="atoms", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--max-mods", type=int, default=None,
                   help="mod cap (default: maxMods from config/atoms.json, else 3)")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("mount"); a.add_argument("intent"); a.add_argument("--cwd")
    a.add_argument("--full", action="store_true"); a.set_defaults(func=cmd_mount)

    w = sub.add_parser("why"); w.add_argument("intent"); w.add_argument("--cwd")
    w.set_defaults(func=cmd_why)

    l = sub.add_parser("list"); l.add_argument("kind", nargs="?", choices=["roles", "mods", "steps"])
    l.add_argument("--json", action="store_true"); l.set_defaults(func=cmd_list)

    v = sub.add_parser("show"); v.add_argument("id"); v.set_defaults(func=cmd_show)

    c = sub.add_parser("current"); c.add_argument("--session"); c.set_defaults(func=cmd_current)

    args = p.parse_args()
    engine = load_engine()
    if args.max_mods is None:
        args.max_mods = engine.MAX_MODS
    return args.func(args, engine)


if __name__ == "__main__":
    sys.exit(main())
