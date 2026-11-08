"""The compatibility data every consumer needs, computed once from the manifests.

A harness designer has to grey out a mod that cannot stack with the ones already enabled, the
harness endpoint has to refuse an impossible selection, and an exporter has to order stacked
constraints. If each of them derived that from `incompatibleWith` and `exclusiveGroup` on its own,
they would disagree (the Fluxor renderer already did: it ignored exclusive groups). So the bundle
ships the answer, `compatibility.json`, built here.

- `pairs`: every pair of mods that cannot be active together, symmetric, with the reasons
  (declared by one side or both, or a shared exclusive group).
- `groups`: exclusive groups and their members.
- `precedenceOrder` and each mod's `precedence`: how stacked mods are ordered when they conflict.
  Constraints the user declared outrank all of them.
- `dependencies`: what each atom requires (`requires.atoms`), for resolving a selection.
"""

from __future__ import annotations

PRECEDENCE_ORDER = ["security", "correctness", "scope", "style"]


def compute(manifests: list[dict]) -> dict:
    mods = {m["id"]: m for m in manifests if m.get("kind") == "mod"}
    reasons: dict[tuple[str, str], set[str]] = {}

    def add(a: str, b: str, reason: str) -> None:
        if a == b:
            return
        reasons.setdefault(tuple(sorted((a, b))), set()).add(reason)

    for mod in mods.values():
        for other in mod.get("incompatibleWith", []):
            if other in mods:
                add(mod["id"], other, f"declared by {mod['id']}")

    groups: dict[str, list[str]] = {}
    for mod in mods.values():
        if mod.get("exclusiveGroup"):
            groups.setdefault(mod["exclusiveGroup"], []).append(mod["id"])
    for group, members in groups.items():
        members.sort()
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                add(a, b, f"exclusive group {group}")

    partners: dict[str, set[str]] = {mid: set() for mid in mods}
    for a, b in reasons:
        partners[a].add(b)
        partners[b].add(a)

    return {
        "schemaVersion": 1,
        "precedenceOrder": PRECEDENCE_ORDER,
        "mods": {
            mid: {
                "precedence": mod.get("precedence"),
                "enforcement": mod.get("enforcement"),
                **({"exclusiveGroup": mod["exclusiveGroup"]} if mod.get("exclusiveGroup") else {}),
                "incompatibleWith": sorted(partners[mid]),
            }
            for mid, mod in sorted(mods.items())
        },
        "pairs": [{"a": a, "b": b, "reasons": sorted(r)} for (a, b), r in sorted(reasons.items())],
        "groups": dict(sorted(groups.items())),
        "dependencies": {
            m["id"]: sorted(m.get("requires", {}).get("atoms", []))
            for m in sorted(manifests, key=lambda m: m["id"])
            if m.get("requires", {}).get("atoms")
        },
    }


def one_sided(manifests: list[dict]) -> list[tuple[str, str]]:
    """Declarations only one side makes. Harmless for the computed matrix, but a reader of one
    manifest would not learn about the conflict, so validation warns."""
    mods = {m["id"]: m for m in manifests if m.get("kind") == "mod"}
    found = []
    for mod in mods.values():
        for other in mod.get("incompatibleWith", []):
            if other in mods and mod["id"] not in mods[other].get("incompatibleWith", []):
                found.append((mod["id"], other))
    return sorted(found)


def conflicts(selection: list[str], matrix: dict) -> list[dict]:
    """The pairs of a selection that cannot be active together."""
    chosen = set(selection)
    return [p for p in matrix["pairs"] if p["a"] in chosen and p["b"] in chosen]


def order_by_precedence(selection: list[str], matrix: dict) -> list[str]:
    """Stable order for stacking: security first, style last; ties keep the selection's order."""
    rank = {name: i for i, name in enumerate(matrix["precedenceOrder"])}
    mods = matrix["mods"]
    return sorted(selection, key=lambda m: rank.get(mods.get(m, {}).get("precedence"), len(rank)))
