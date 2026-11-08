"""Installs a selection of this catalog into a project's harness, and checks that it stays installed.

  marketplace.py install [--harness DIR]          copy the selected atoms, write the lock
  marketplace.py install --check [--harness DIR]  exit 1 on drift, without writing anything

The selection is the project's `<harness>/harness.json`, edited by hand (or, later, written by
Fluxor's harness sync). The lock is `<harness>/harness.lock.json`, written only by this command:
every installed file with its sha256, its executable bit and the atom it came from. Together they
answer the three questions a copy can get wrong:

- **Edited by hand?** A managed file whose bytes no longer match the lock. The fix is in the
  catalog, never in the copy: the copy is overwritten on the next install, so an edit there is lost.
- **Stale?** A lock that a fresh install would no longer produce: the catalog moved on and nobody
  reinstalled.
- **Unmanaged?** A file inside a managed folder that no atom installs and the selection does not
  declare `local`: a project-only atom has to be declared, or it is invisible to everyone who
  reasons about the harness from its selection.

`install` refuses to overwrite a hand-edited file unless `--force` is given (the catalog contract,
"How a project receives its harness", step 5), and it never deletes an unmanaged file: it only says
so. The project's own atoms are declared under `local` (`files` globs, plus inventory `cards`); a
local card with a catalog atom's id replaces that atom, and the project keeps its file, even one
an earlier install wrote: `install` never removes, nor refuses over, a taken-over path `local.files`
declares. `--check` fails on a local card with no file behind it, and on a path the catalog still
installs that `local.files` also claims (two owners).

A preset the selection names under `presets` adds its items to the skills and hooks it selects, and
is itself locked (it writes no file), so a preset that changed reads as a stale install. Its params
are not rendered here: a project installed from disk keeps its own `config/<skill>.json`.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path, PurePosixPath

# The lock and edited-file rules are fluxor-sync's, so a harness Fluxor serves and one installed
# from this catalog are judged the same way (card://JAVA-162).
import fluxor_sync
from fluxor_sync import disk_bytes

SELECTION = "harness.json"
LOCK = "harness.lock.json"
KIND_KEYS = {"skills": "skill", "roles": "role", "mods": "mod", "steps": "step", "flows": "flow",
             "hooks": "hook"}
SELECTION_KEYS = {"$schema", "$comment", "skills", "roles", "mods", "steps", "flows", "hooks", "presets", "engine",
                  "local", "external"}
LOCAL_KEYS = {"$comment", "files", "cards"}
INVENTORY_PATH = "market/inventory.json"
INVENTORY_KINDS = {"flows", "roles", "mods", "steps"}


class SelectionError(Exception):
    pass


def harness_dir(arg: str | None) -> Path:
    """`--harness`, else `$HARNESS_DIR`, else `<project root>/.harness` (harness-convention.md)."""
    if arg:
        return Path(arg).resolve()
    if os.environ.get("HARNESS_DIR"):
        return Path(os.environ["HARNESS_DIR"]).resolve()
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    if not root:
        try:
            root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                                  check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            root = os.getcwd()
    return Path(root).resolve() / ".harness"


def read_selection(harness: Path) -> dict:
    path = harness / SELECTION
    if not path.is_file():
        raise SelectionError(f"{path} does not exist: it names the atoms this harness installs")
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SelectionError(f"{path} is not valid JSON ({exc})") from exc
    if not isinstance(selection, dict):
        raise SelectionError(f"{path} must hold a JSON object")
    problems = [f"unknown key {k!r}" for k in sorted(set(selection) - SELECTION_KEYS)]
    local = selection.get("local", {})
    if not isinstance(local, dict):
        problems.append("'local' must be an object")
    else:
        problems += [f"local: unknown key {k!r}" for k in sorted(set(local) - LOCAL_KEYS)]
        cards = local.get("cards", {})
        if not isinstance(cards, dict):
            problems.append("'local.cards' must be an object")
        else:
            problems += [f"local.cards: unknown kind {k!r} (one of {', '.join(sorted(INVENTORY_KINDS))})"
                         for k in sorted(set(cards) - INVENTORY_KINDS) if not k.startswith("$")]
    external = selection.get("external", {})
    if not (isinstance(external, dict) and all(isinstance(v, str) and v for v in external.values())):
        problems.append("'external' must map an atom id to the reason the project has it without installing it")
    for key in KIND_KEYS:
        value = selection.get(key, [])
        if value != "*" and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            problems.append(f"{key!r} must be \"*\" or a list of atom ids")
    presets = selection.get("presets", [])
    if not (isinstance(presets, list) and all(isinstance(v, str) for v in presets)):
        problems.append("'presets' must be a list of preset ids")
    if problems:
        raise SelectionError(f"{path}: " + "; ".join(problems) + f". Known keys: {', '.join(sorted(SELECTION_KEYS))}")
    return selection


def selected_atoms(mp, atoms, selection: dict) -> tuple[list, list[str]]:
    """The atoms the selection names, and the problems: an unknown id, an unmet requirement. A
    project-local card with a catalog atom's id replaces that atom: the project keeps its own."""
    chosen, problems = [], []
    by_kind: dict[str, dict] = {}
    for atom in atoms:
        by_kind.setdefault(atom.kind, {})[atom.id] = atom
    local = {key: {c.get("name") for c in cards if isinstance(c, dict)}
             for key, cards in local_cards(selection).items()}
    from_presets, preset_problems = preset_items(by_kind, selection, chosen)
    problems += preset_problems
    for key, kind in KIND_KEYS.items():
        wanted = selection.get(key, [])
        pool = by_kind.get(kind, {})
        if wanted == "*":
            ids = sorted(i for i, a in pool.items()
                         if a.manifest.get("stability", "stable") != "deprecated"
                         and not (kind == "skill" and a.manifest.get("packaging") == "meta"))
        else:
            ids = list(wanted)
        ids = list(dict.fromkeys(ids + from_presets.get(key, [])))
        ids = [i for i in ids if i not in local.get(key, set())]
        for aid in ids:
            atom = pool.get(aid)
            if atom is None:
                problems.append(f"{key}: no {kind} called {aid!r} in the catalog")
            else:
                chosen.append(atom)
    if selection.get("engine", True):
        chosen += [a for a in atoms if a.kind == "engine"]
    # A requirement the project meets some other way (a skill the agent gets from its user profile,
    # say) is declared in `external` with the reason, so an unmet one is never silent.
    present = {a.id for a in chosen} | set(selection.get("external", {})) | set().union(*local.values())
    for atom in chosen:
        for ref in atom.manifest.get("requires", {}).get("atoms", []):
            dep = ref.split("@", 1)[0]
            if dep not in present:
                problems.append(f"{atom.id} requires {ref}, which the selection neither installs nor "
                                "declares under `external`")
    return chosen, problems


def preset_items(by_kind: dict, selection: dict, chosen: list) -> tuple[dict[str, list[str]], list[str]]:
    """The atom ids each selected preset adds, keyed like the selection (`skills`, `hooks`), and the
    problems. The presets themselves go into `chosen`, so the lock records their versions."""
    added: dict[str, list[str]] = {}
    problems = []
    key_of = {kind: key for key, kind in KIND_KEYS.items()}
    for pid in selection.get("presets", []):
        preset = by_kind.get("preset", {}).get(pid)
        if preset is None:
            problems.append(f"presets: no preset called {pid!r} in the catalog")
            continue
        chosen.append(preset)
        for item in preset.manifest.get("items", []):
            aid = item.get("key") if isinstance(item, dict) else None
            kind = next((k for k in ("skill", "hook") if aid in by_kind.get(k, {})), None)
            if kind is None:
                problems.append(f"presets: {pid} lists {aid!r}, which is not a skill or hook in the catalog")
            else:
                added.setdefault(key_of[kind], []).append(aid)
    return added, problems


def local_cards(selection: dict) -> dict[str, list[dict]]:
    """Inventory cards for the project's own atoms, keyed like the inventory (`roles`, `mods`...)."""
    cards = selection.get("local", {}).get("cards", {})
    return {k: v for k, v in cards.items() if isinstance(v, list)} if isinstance(cards, dict) else {}


def expected_install(mp, harness: Path, selection: dict) -> tuple[dict[str, dict], dict[str, dict], list[str]]:
    """What a fresh install writes: {install path: {sha256, executable, atom, source}} plus the
    atoms with their versions and hashes, and the problems that stop it."""
    atoms, errors = mp.load_catalog()
    chosen, problems = selected_atoms(mp, atoms, selection)
    problems = errors + problems
    tracked, git_exec = mp.tracked_files(), mp.git_executables()
    files: dict[str, dict] = {}
    locked_atoms: dict[str, dict] = {}
    for atom in sorted(chosen, key=lambda a: (a.kind, a.id)):
        described = mp.describe_files(atom, tracked, git_exec)
        locked_atoms[atom.id] = {"kind": atom.kind, "version": atom.version, "hash": mp.atom_hash(atom, described)}
        for f in described:
            if f["path"] in files:
                problems.append(f"{f['path']}: installed by both {files[f['path']]['atom']} and {atom.id}")
            files[f["path"]] = {"sha256": f["sha256"], "executable": f["executable"], "atom": atom.id,
                                "source": f["source"]}
    if any(a.kind in mp.MARKET_KINDS for a in chosen):
        inventory = mp.fluxor_inventory(chosen)
        for key, extra in local_cards(selection).items():
            merged = {c["name"]: c for c in inventory.get(key, [])}
            merged.update({c["name"]: c for c in extra if isinstance(c, dict) and c.get("name")})
            inventory[key] = [merged[n] for n in sorted(merged)]
        data = mp.dump_json(inventory).encode("utf-8")
        files[INVENTORY_PATH] = {"sha256": mp.sha256_bytes(data), "executable": False, "atom": None,
                                 "generated": True, "_bytes": data}
    return files, locked_atoms, problems


def harness_files(harness: Path) -> set[str]:
    """Files under the harness that git sees (tracked, or untracked and not ignored), relative to it.
    Ignored files (`__pycache__`) are nobody's business here."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."],
                             cwd=harness, capture_output=True, check=True)
        return {p for p in out.stdout.decode("utf-8").split("\0") if p and (harness / p).is_file()}
    except (OSError, subprocess.CalledProcessError):
        return {p.relative_to(harness).as_posix() for p in harness.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts}


def managed_roots(files: dict[str, dict]) -> set[str]:
    """The folders an install owns: each installed skill's folder and the market's kind folders.
    A file there that no atom installs is unmanaged."""
    roots = set()
    for path in files:
        parts = PurePosixPath(path).parts
        if parts[0] == "skills" and len(parts) > 2:
            roots.add(f"skills/{parts[1]}/")
        elif parts[0] == "market":
            roots.add("market/" if len(parts) == 2 else f"market/{parts[1]}/")
    return roots


def is_local(rel: str, selection: dict, mp) -> bool:
    return mp.glob_match(rel, selection.get("local", {}).get("files", []))


def unmanaged(harness: Path, files: dict[str, dict], selection: dict, mp) -> list[str]:
    roots = managed_roots(files)
    found = []
    for rel in sorted(harness_files(harness)):
        if rel in files or is_local(rel, selection, mp):
            continue
        top = PurePosixPath(rel).parts
        inside_root = any(rel.startswith(r) and (r != "market/" or len(top) == 2) for r in roots)
        # A skill folder no atom installs is unmanaged too, unless the selection declares it local.
        if inside_root or (top[0] == "skills" and len(top) > 2):
            found.append(rel)
    return found


def claimed_twice(files: dict[str, dict], selection: dict, mp) -> list[str]:
    """Paths this install writes that `local.files` also claims: two owners, and the catalog's copy
    would overwrite whatever the project keeps there."""
    return [rel for rel in sorted(files) if is_local(rel, selection, mp)]


def local_cards_without_file(harness: Path, selection: dict) -> list[str]:
    """Install paths of the `local.cards` whose file is missing: the inventory would advertise an
    atom with nothing behind it. A local card sits where a catalog atom of its kind installs."""
    return [rel for key, cards in local_cards(selection).items() for card in cards
            if isinstance(card, dict) and card.get("name")
            for rel in [f"market/{key}/{card['name']}.md"] if not (harness / rel).is_file()]


def read_lock(harness: Path) -> dict:
    return fluxor_sync.read_lock(harness / LOCK)


def lock_document(files: dict[str, dict], locked_atoms: dict[str, dict], mp) -> dict:
    entries = {p: {k: v for k, v in f.items() if not k.startswith("_")} for p, f in sorted(files.items())}
    snapshot = mp.sha256_bytes("\n".join(f"{a}@{v['version']} {v['hash']}" for a, v in sorted(locked_atoms.items()))
                               .encode("utf-8") + b"\n" + json.dumps(entries.get(INVENTORY_PATH, {})).encode("utf-8"))
    return {"schemaVersion": 1, "snapshot": snapshot, "atoms": dict(sorted(locked_atoms.items())), "files": entries}


def edited_by_hand(mp, harness: Path, lock: dict) -> list[tuple[str, str]]:
    """(install path, reason) for every locked file whose bytes or mode no longer match the lock."""
    return fluxor_sync.edited_files(harness, lock)


def source_hint(rel: str, entry: dict) -> str:
    if entry.get("generated"):
        return "generated by the installer"
    return f"its source is the catalog's {entry.get('source', '?')}"


def check(mp, harness: Path) -> int:
    try:
        selection = read_selection(harness)
    except SelectionError as exc:
        print(f"error: {exc}")
        return 1
    files, locked_atoms, problems = expected_install(mp, harness, selection)
    lock = read_lock(harness)
    failures = [f"error: {p}" for p in problems]
    if not lock:
        failures.append(f"error: {harness / LOCK} is missing: run `marketplace.py install`")
    else:
        for rel, reason in edited_by_hand(mp, harness, lock):
            failures.append(f"error: {rel}: edited by hand ({reason}); {source_hint(rel, lock['files'][rel])}. "
                            "Edit the source, bump its version, `lock`, then `install`.")
        expected = lock_document(files, locked_atoms, mp)
        if expected["files"] != lock.get("files") or expected["atoms"] != lock.get("atoms"):
            stale = sorted(a for a in set(expected["atoms"]) | set(lock.get("atoms", {}))
                           if expected["atoms"].get(a) != lock.get("atoms", {}).get(a))
            what = ", ".join(stale) if stale else "the inventory"
            failures.append(f"error: the installed harness is stale ({what}): run `marketplace.py install`")
    for rel in unmanaged(harness, files, selection, mp):
        failures.append(f"error: {rel}: unmanaged file in a managed folder; install it from the catalog, "
                        f"declare it under `local` in {SELECTION}, or remove it")
    for rel in claimed_twice(files, selection, mp):
        failures.append(f"error: {rel}: installed from the catalog and declared local in {SELECTION}; "
                        "narrow `local.files`, or take the atom over with a local card")
    for rel in local_cards_without_file(harness, selection):
        failures.append(f"error: {rel}: missing, but a local card in {SELECTION} names it; "
                        "restore the file or drop the card")
    for line in failures:
        print(line)
    if failures:
        return 1
    print(f"ok: {len(lock['files'])} installed files from {len(lock['atoms'])} atoms match the catalog")
    return 0


def install(mp, harness: Path, force: bool = False) -> int:
    try:
        selection = read_selection(harness)
    except SelectionError as exc:
        print(f"error: {exc}")
        return 1
    files, locked_atoms, problems = expected_install(mp, harness, selection)
    if problems:
        for p in problems:
            print(f"error: {p}")
        return 1
    old = read_lock(harness)
    # A taken-over file (in the old lock, not in this install) is the project's to edit; one the
    # catalog still installs is not, whatever `local.files` matches (card://JAVA-551).
    edited = [(rel, why) for rel, why in edited_by_hand(mp, harness, old)
              if why != "deleted" and not (rel not in files and is_local(rel, selection, mp))]
    if edited and not force:
        for rel, why in edited:
            print(f"error: {rel}: edited by hand ({why}); move the change into the catalog first, "
                  "or pass --force to discard it")
        return 1
    written = 0
    for rel, entry in files.items():
        target = harness / rel
        data = entry["_bytes"] if "_bytes" in entry else mp.read_content(entry["source"])
        current = disk_bytes(target) if target.is_file() else None
        if current != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written += 1
        if os.name != "nt":
            target.chmod(0o755 if entry["executable"] else 0o644)
    removed = 0
    for rel in sorted(set(old.get("files", {})) - set(files)):
        target = harness / rel
        # An installed atom the project took over is in the old lock and not in this install; the
        # file is the project's now (card://JAVA-551).
        if target.is_file() and not is_local(rel, selection, mp):
            target.unlink()
            removed += 1
            parent = target.parent
            while parent != harness and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    mp.write_lf(harness / LOCK, mp.dump_json(lock_document(files, locked_atoms, mp)))
    print(f"installed {len(locked_atoms)} atoms into {harness}: {written} file(s) written, {removed} removed")
    for rel in unmanaged(harness, files, selection, mp):
        print(f"warning: {rel}: unmanaged file in a managed folder (left in place; declare it local or remove it)")
    for rel in claimed_twice(files, selection, mp):
        print(f"warning: {rel}: installed from the catalog and declared local in {SELECTION} (the catalog's copy wins)")
    for rel in local_cards_without_file(harness, selection):
        print(f"warning: {rel}: missing, but a local card in {SELECTION} names it")
    return 0
