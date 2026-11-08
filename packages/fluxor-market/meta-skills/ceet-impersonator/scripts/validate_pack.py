#!/usr/bin/env python3
"""Validate a pack written by ceet-impersonator: ceet-core's validator, for simulated packs only.

  validate_pack.py .harness/packs/<output-slug>
  validate_pack.py <pack> --role-dir path/to/ceet-<role> --json

Every check lives in ceet-core 2 (`../ceet-core/scripts/validate_pack.py`): the consent basis, a row
in `evidence-map.md` for every directive the role declares with a source or an explicit `unknown`,
`[E<n>]` citations, the Simulation Notice in every file, no reflection on the person. This wrapper adds
one rule of its own: the pack must say `source: simulation`, so a pack this skill wrote cannot skip
those checks by claiming to come from an interview.

Exit 0 when valid, 1 with findings, 2 on usage errors or a missing ceet-core 2. Standard library only
(Python 3.9+).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "ceet-core"
REQUIRED_MAJOR = "2"


def load_core():
    """ceet-core's validate_pack module, or SystemExit(2) when ceet-core 2 is not installed beside us."""
    manifest = CORE / "skill.json"
    if not manifest.is_file():
        print(f"error: ceet-core is not installed next to this skill ({CORE}); ceet-impersonator requires ceet-core@{REQUIRED_MAJOR}",
              file=sys.stderr)
        raise SystemExit(2)
    version = json.loads(manifest.read_text(encoding="utf-8")).get("version", "")
    if version.split(".")[0] != REQUIRED_MAJOR:
        print(f"error: ceet-impersonator requires ceet-core@{REQUIRED_MAJOR}, found {version or 'no version'}", file=sys.stderr)
        raise SystemExit(2)
    # Loaded by path under its own name: this file is also called validate_pack.py.
    spec = importlib.util.spec_from_file_location("ceet_core_validate_pack", CORE / "scripts" / "validate_pack.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pack_source(pack: Path) -> str | None:
    """The profile's `source`, or None when ceet-core will report the profile itself as missing or broken."""
    try:
        return json.loads((pack / "cognitive-profile.json").read_text(encoding="utf-8")).get("source")
    except (OSError, ValueError, AttributeError):
        return None


def validate(pack: Path, role_dir: str | None = None) -> tuple[list[str], list[str]]:
    source = pack_source(pack)
    if source is not None and source != "simulation":
        return [f"cognitive-profile.json source is {source!r}: ceet-impersonator only writes simulated packs "
                "(source 'simulation'); validate an interview pack with ceet-core's validate_pack.py"], []
    return load_core().validate(pack, role_dir)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate a simulated pack written by ceet-impersonator.")
    parser.add_argument("pack", help="the pack folder (e.g. .harness/packs/<output-slug>)")
    parser.add_argument("--role-dir", help="the role's folder, when it is not installed next to ceet-core")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    core = load_core()
    pack = Path(args.pack).resolve()
    if not pack.is_dir():
        print(f"error: not a directory: {pack}", file=sys.stderr)
        return 2
    source = pack_source(pack)
    if source is not None and source != "simulation":
        errors, _ = validate(pack, args.role_dir)
        if args.json:
            print(json.dumps({"pack": pack.name, "valid": False, "errors": errors, "warnings": []}, indent=2))
        else:
            print(f"error: {errors[0]}\npack {pack.name}: invalid (1 error(s))")
        return 1
    return core.main(argv)


if __name__ == "__main__":
    sys.exit(main())
