#!/usr/bin/env python3
"""
Market engine: discovers the atoms that fit an intent.

A port of `discoverPipelineComponents()` from the Fluxor IDE's Meta-Agent. Over there the final
assembly is done by an LLM call; here the LLM is the agent itself, so the engine keeps only
the deterministic part —score the catalog, pick ONE role, stack mods without conflicts,
propose steps— and hands over the assembled result. No network, no extra model.

It lives next to the catalog it scores, and not in a hook or a skill, because both use it: the
`atoms` skill's preparation hook (`skills/atoms/hooks/prepare-batch.sh`) and its CLI
(`skills/atoms/atoms.py`). One single implementation of the scoring; if they diverged, the
skill would lie about what the hook mounts.

Where things are found (see .harness/contracts/harness-convention.md in Fluxor's market):

- The catalog is the directory this file lives in: `<harness>/market/` inside a project, or
  the top-level `market/` of the repository that publishes the market.
- Project root: $CLAUDE_PROJECT_DIR, else `git rev-parse --show-toplevel`, else the current
  directory. Harness: $HARNESS_DIR (relative paths resolve against the root), else
  `<root>/.harness`.
- `<harness>/INVARIANTS.md`, when present, is prepended to every mounted set. When absent it is
  silently skipped.
- `<harness>/config/atoms.json`, when present, tunes the limits (see the `atoms` SKILL.md for
  every key). Environment variables override it: ATOMS_MAX_MODS, ATOMS_BUDGET,
  ATOMS_MIN_CHARS, ATOMS_MIN_TOKENS.

Per-session state (so the same thing is not re-injected every turn) lives outside the tree, in
the system temp directory: the harness is versioned and this is one machine's cache, not the
project's.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path


# ---------------------------------------------------------------------------
# small readers (needed before the configuration is loaded)
# ---------------------------------------------------------------------------

def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# locating the project, the harness and the catalog
# ---------------------------------------------------------------------------

def _git_toplevel(start: Path):
    try:
        out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=3)
        top = out.stdout.strip()
        if out.returncode == 0 and top and Path(top).is_dir():
            return Path(top)
    except Exception:
        pass
    return None


def project_root() -> Path:
    """$CLAUDE_PROJECT_DIR, else the git top-level of the current directory, else the current
    directory. Never derived from where this file lives: the catalog may be shared by several
    projects, and walking up from it would find the wrong one."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    cwd = Path.cwd()
    return (_git_toplevel(cwd) or cwd).resolve()


def harness_dir(root: Path) -> Path:
    env = os.environ.get("HARNESS_DIR")
    if env:
        p = Path(env)
        return (p if p.is_absolute() else root / p).resolve()
    return root / ".harness"


ROOT = project_root()
HARNESS = harness_dir(ROOT)
# The catalog is the directory this file lives in.
MARKET = Path(__file__).resolve().parent


def display(path: Path) -> str:
    """A path as the agent should read it: relative to the project root when it is inside it,
    absolute otherwise. Rendered text never claims `.harness/` when the harness is elsewhere."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix() or "."
    except (ValueError, OSError):
        return path.as_posix()


MARKET_REL = display(MARKET)
HARNESS_REL = display(HARNESS)
INVARIANTS_FILE = HARNESS / "INVARIANTS.md"
CONFIG_FILE = HARNESS / "config" / "atoms.json"
# One subdirectory per project, keyed by a hash of its root: no project name in the path, and
# `atoms current` does not report another project's session.
STATE_DIR = (Path(tempfile.gettempdir()) / "atoms-state"
             / hashlib.sha1(str(ROOT).encode("utf-8")).hexdigest()[:12])


# ---------------------------------------------------------------------------
# configuration: defaults < <harness>/config/atoms.json < environment
# ---------------------------------------------------------------------------

CONFIG = read_json(CONFIG_FILE, {})
if not isinstance(CONFIG, dict):
    CONFIG = {}


def _setting(key: str, env: str, default: int) -> int:
    value = default
    try:
        if key in CONFIG:
            value = int(CONFIG[key])
    except (TypeError, ValueError):
        pass
    try:
        if os.environ.get(env):
            value = int(os.environ[env])
    except ValueError:
        pass
    return value


def _string_list(key: str) -> list:
    got = CONFIG.get(key)
    return [str(x) for x in got] if isinstance(got, list) else []


MAX_MODS = _setting("maxMods", "ATOMS_MAX_MODS", 3)
BUDGET = _setting("budget", "ATOMS_BUDGET", 14000)
MIN_CHARS = _setting("minChars", "ATOMS_MIN_CHARS", 20)
MIN_TOKENS = _setting("minTokens", "ATOMS_MIN_TOKENS", 3)

# Width of the preselection — the `.slice(0, 5)` of selectRelevant() in the original.
PRESELECTION = 5
# One exact hit on the registry card (2 x CARD_WEIGHT). Below that it is noise.
MIN_POINTS = 6
# The registry card is a curated summary; a role's body is thousands of words that match by
# substring against almost anything. Without this weight, "table component" picked
# backend-engineer because "frontend" appears in its Boundaries section.
CARD_WEIGHT = 3
# The project signals (dependencies and files in the cwd) do NOT arbitrate: they only break
# exact ties, as a secondary sort key. There was a version that reordered everything falling
# within 8% of the leader, for cases where the wording did not discriminate ("implement the
# command palette", with four roles within two points of each other). It was withdrawn once
# measured: the real gap was not in the scoring but in the vocabulary —the lexicon did not
# know `palette`, `renderer`, `sidebar` or the Spanish for "shortcut"— and once it was filled
# in, the wording alone got every bench case right. What the arbitration did do was break the ones
# that were already right: "audit the endpoint's security" (asked in Spanish) handed
# security-researcher (44) over to full-stack-engineer (41) because the repo had
# `.github/workflows`. If an ambiguous case shows up again, the answer is lexicon, not a
# smarter tie-break.


# ---------------------------------------------------------------------------
# catalog
# ---------------------------------------------------------------------------

def load_catalog() -> dict:
    """Registry cards joined to their .md. A card with no .md is dropped: there is no prompt
    to inject. An .md with no card is invisible, which is the other half of the contract."""
    inv = read_json(MARKET / "inventory.json", {})
    if not isinstance(inv, dict):
        inv = {}
    cat = {}
    for kind in ("roles", "mods", "steps"):
        items = []
        for order, card in enumerate(inv.get(kind) or []):
            if not isinstance(card, dict):
                continue
            name = card.get("name")
            if not name:
                continue
            md = MARKET / kind / f"{name}.md"
            if not md.is_file():
                continue
            items.append({
                "id": name,
                "description": card.get("description", ""),
                "tags": card.get("tags") or [],
                "domains": card.get("domains") or [],
                "incompatible": card.get("incompatibleWith") or [],
                "exclusive_group": card.get("exclusiveGroup"),
                "runtime": card.get("runtime"),
                "path": md,
                "order": order,
            })
        cat[kind] = items
    return cat


def load_lexicon() -> dict:
    lexicon = read_json(MARKET / "lexicon.json", {})
    return lexicon if isinstance(lexicon, dict) else {}


# ---------------------------------------------------------------------------
# scoring — port of tokenize() / scoreAgainstIntent() / selectRelevant()
# ---------------------------------------------------------------------------

def normalize(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value.lower())
                   if not unicodedata.combining(c))


def tokenize(value: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", normalize(value)) if len(t) >= 3}


def score(text: str, tokens: set) -> int:
    """Literal port: exact hit +2, substring in either direction +1 (once per token)."""
    if not tokens:
        return 0
    component_tokens = tokenize(text)
    total = 0
    for token in tokens:
        if token in component_tokens:
            total += 2
        for ct in component_tokens:
            if token in ct or ct in token:
                total += 1
                break
    return total


def card_text(item: dict) -> str:
    return " ".join([item["id"], item["description"],
                     " ".join(item["tags"]), " ".join(item["domains"])])


def score_item(item: dict, body: str, tokens: set) -> int:
    return CARD_WEIGHT * score(card_text(item), tokens) + (score(body, tokens) if body else 0)


def rank(items: list, tokens: set, bodies: dict, signals: set = frozenset()) -> list:
    """What the user wrote rules; the project signals only break ties. Mixing them would let a
    React dependency beat the word "refactor"."""
    scored = [(it, score_item(it, bodies.get(it["id"], ""), tokens),
               score_item(it, bodies.get(it["id"], ""), signals) if signals else 0)
              for it in items]
    scored.sort(key=lambda p: (-p[1], -p[2], p[0]["id"]))
    return [(it, own) for it, own, _ in scored]


# ---------------------------------------------------------------------------
# intent
# ---------------------------------------------------------------------------

def synonyms_for(token: str, synonyms: dict) -> list:
    """Exact key; failing that, the longest key sharing >=5 characters of prefix. Spanish
    arrives conjugated (a present-tense form of "refactor") and the lexicon keys are infinitives."""
    if token in synonyms:
        return synonyms[token]
    best, longest = None, 0
    for key in synonyms:
        if key.startswith("_"):
            continue
        common = min(len(key), len(token))
        if common >= 5 and key.startswith(token[:common]) and token.startswith(key[:common]) and common > longest:
            best, longest = key, common
    return synonyms.get(best, []) if best else []


def expand(prompt: str, lexicon: dict) -> tuple:
    synonyms = lexicon.get("synonyms", {})
    stop = set(lexicon.get("stopwords", []))
    raw = {t for t in tokenize(prompt) if t not in stop}
    expanded = set(raw)
    for token in raw:
        for mapped in synonyms_for(token, synonyms):
            expanded.update(tokenize(mapped))
    return expanded, raw


def has_work_verb(prompt: str, lexicon: dict) -> bool:
    return bool(tokenize(prompt) & {normalize(v) for v in lexicon.get("work_verbs", [])})


def signal_table(lexicon: dict) -> dict:
    """The lexicon's generic detectors, extended (not replaced) by the project's own
    `signals` in `config/atoms.json` — e.g. its in-house UI package mapped to `design-system`."""
    base = lexicon.get("project_signals") or {}
    extra = CONFIG.get("signals") if isinstance(CONFIG.get("signals"), dict) else {}
    table = {}
    for key in ("package.json", "files"):
        merged = dict(base.get(key) or {})
        merged.update(extra.get(key) or {})
        table[key] = merged
    return table


def project_signals(cwd: Path, lexicon: dict) -> tuple:
    """Dependencies and marker files in the session's directory and at the project root (they
    differ in a monorepo: the root `package.json` is often only the workspace)."""
    cfg = signal_table(lexicon)
    tokens, evidence = set(), []

    places = []
    for place in (cwd, ROOT):
        try:
            resolved = place.resolve()
        except OSError:
            continue
        if resolved not in places and resolved.is_dir():
            places.append(resolved)

    for place in places:
        pkg = place / "package.json"
        if pkg.is_file():
            data = read_json(pkg, {})
            deps = {}
            if isinstance(data, dict):
                for key in ("dependencies", "devDependencies", "peerDependencies"):
                    got = data.get(key)
                    if isinstance(got, dict):
                        deps.update(got)
            for dep, mapped in (cfg.get("package.json") or {}).items():
                if dep not in evidence and any(n == dep or n.startswith(dep + "/") for n in deps):
                    tokens.update(tokenize(" ".join(mapped)))
                    evidence.append(dep)

        for marker, mapped in (cfg.get("files") or {}).items():
            if marker not in evidence and (place / marker).exists():
                tokens.update(tokenize(" ".join(mapped)))
                evidence.append(marker)

    return tokens, evidence


# ---------------------------------------------------------------------------
# resolving the set
# ---------------------------------------------------------------------------

def incompatibility_graph(mods: list) -> dict:
    """Explicit `incompatibleWith` (symmetrized) plus the pairs that derive on their own from
    `exclusiveGroup` — the same rule the market loader applies in Fluxor."""
    graph = {m["id"]: set(m["incompatible"]) for m in mods}
    for mid, others in list(graph.items()):
        for other in others:
            graph.setdefault(other, set()).add(mid)
    groups = {}
    for m in mods:
        if m["exclusive_group"]:
            groups.setdefault(m["exclusive_group"], []).append(m["id"])
    for members in groups.values():
        for a in members:
            for b in members:
                if a != b:
                    graph.setdefault(a, set()).add(b)
    return graph


def pick_mods(ranked: list, forced: list, incompatible: dict, cap: int) -> list:
    by_id = {it["id"]: it for it, _ in ranked}
    chosen, taken = [], set()

    for mid in forced:
        it = by_id.get(mid)
        if it and mid not in taken:
            chosen.append(it)
            taken.add(mid)

    for it, pts in ranked:
        if len(chosen) >= cap:
            break
        if it["id"] in taken or pts <= 0:
            continue
        if any(other in incompatible.get(it["id"], set()) for other in taken):
            continue
        chosen.append(it)
        taken.add(it["id"])

    return chosen


def apply_aliases(prompt: str, lexicon: dict) -> str:
    """Directive aliases from the lexicon (e.g. a Spanish spelling of @noatoms) are rewritten to
    their canonical English form before parsing."""
    for alias, canonical in (lexicon.get("directive_aliases") or {}).items():
        if alias.startswith("_") or not isinstance(canonical, str):
            continue
        prompt = re.sub(re.escape(alias), canonical, prompt, flags=re.IGNORECASE)
    return prompt


def directives(prompt: str, lexicon: dict = None) -> dict:
    text = apply_aliases(prompt, lexicon or {})
    lower = text.lower()
    return {
        "skip": "@noatoms" in lower,
        "refresh": "@atoms:refresh" in lower,
        "roles": re.findall(r"@role:([a-z0-9-]+)", text, re.IGNORECASE),
        "mods": re.findall(r"@mod:([a-z0-9-]+)", text, re.IGNORECASE),
    }


def never_auto(lexicon: dict) -> set:
    """Atoms never picked by wording: the lexicon's generic list plus the project's own
    `neverAuto`, minus what the project opts back in with `allowAuto` (e.g. `ds-house` in a
    project that has an in-house design system). They stay attachable with @role:/@mod:."""
    never = {m.lower() for m in list(lexicon.get("never_auto", [])) + _string_list("neverAuto")}
    return never - {m.lower() for m in _string_list("allowAuto")}


def wording_can_pick(item: dict) -> bool:
    """A board role (tag `board`) works a card because of the card's category and phase, which
    the board decides; a prompt's wording never picks it, or `backend-developer` would take
    every interactive prompt `backend-engineer` answers today. One that also serves interactive
    sessions says so with `interactive`. Either way, @role:<id> still attaches it. A step or a mod
    tagged `flow` only makes sense inside a flow (a step reads "the task the flow was started from"),
    so wording never suggests it either."""
    tags = item.get("tags") or []
    return not ({"board", "flow"} & set(tags)) or "interactive" in tags


# A card names its own role. When the batch is about a board card, the role is one of the roles
# the board allows for that card (from its category, phase and signals), chosen by the agent once
# it has read the card: the wording of "work PROJ-12" knows nothing about the card, and scoring it
# would mount a persona the board never allowed. A project turns this on with `cards.keyPrefixes`
# in its atoms.json; an autonomous loop whose prompt names no card (the iteration picks it) is
# recognized by one of `cards.loopMarkers`.
def _card_settings() -> tuple:
    cards = CONFIG.get("cards") if isinstance(CONFIG.get("cards"), dict) else {}
    prefixes = [p for p in cards.get("keyPrefixes") or [] if isinstance(p, str) and p]
    markers = [m for m in cards.get("loopMarkers") or [] if isinstance(m, str) and m]
    pattern = re.compile(r"\b(?:%s)-\d+\b" % "|".join(map(re.escape, prefixes))) if prefixes else None
    return pattern, markers


CARD_KEY, LOOP_MARKERS = _card_settings()


def card_source(prompt: str) -> str | None:
    """The card key the prompt names, `loop` for an autonomous loop's iteration, or None."""
    match = CARD_KEY.search(prompt) if CARD_KEY else None
    if match:
        return match.group(0)
    return "loop" if any(m in prompt for m in LOOP_MARKERS) else None


def resolve(prompt: str, cwd: Path, mod_cap: int = None) -> dict | None:
    mod_cap = MAX_MODS if mod_cap is None else mod_cap
    lexicon = load_lexicon()
    catalog = load_catalog()
    if not catalog.get("roles"):
        return None

    expanded, raw = expand(prompt, lexicon)
    signals, evidence = project_signals(cwd, lexicon)

    role_bodies = {i["id"]: read_text(i["path"]) for i in catalog["roles"]}
    role_ranked = rank(catalog["roles"], expanded, role_bodies, signals)
    mod_ranked = rank(catalog["mods"], expanded, {}, signals)
    # Wording preselects only what it may pick (a mod tagged `flow` belongs to a flow, as a step does).
    # A forced @mod: still attaches from the full ranking below.
    wording_mods = [(i, s) for i, s in mod_ranked if wording_can_pick(i)]
    step_ranked = rank(catalog["steps"], expanded, {}, signals)

    dir_ = directives(prompt, lexicon)
    never = never_auto(lexicon)

    role = None
    if dir_["roles"]:
        role = next((i for i, _ in role_ranked if i["id"] == dir_["roles"][0].lower()), None)
    if role is None:
        role = next((i for i, _ in role_ranked if i["id"] not in never and wording_can_pick(i)), None)
    if role is None:
        return None

    incompatible = incompatibility_graph(catalog["mods"])
    top_mod = wording_mods[0][1] if wording_mods else 0
    shortlist = [(i, s) for i, s in wording_mods[:PRESELECTION]
                 if s >= MIN_POINTS and s >= top_mod * 0.5 and i["id"] not in never]
    forced = [m.lower() for m in dir_["mods"]]
    # A forced mod is attached even when the wording would not have preselected it (or when it
    # is in `never_auto`, whose whole point is being attachable only on request).
    listed = {i["id"] for i, _ in shortlist}
    shortlist += [(i, s) for i, s in mod_ranked if i["id"] in forced and i["id"] not in listed]
    mods = pick_mods(shortlist, forced, incompatible, mod_cap)

    step_ranked = [(i, s) for i, s in step_ranked if wording_can_pick(i)]
    top_step = step_ranked[0][1] if step_ranked else 0
    steps = [i for i, s in step_ranked[:4] if s >= MIN_POINTS and s >= top_step * 0.5]
    steps.sort(key=lambda p: p["order"])

    catalog_tokens = set()
    for kind in ("roles", "mods", "steps"):
        for it in catalog[kind]:
            catalog_tokens |= tokenize(card_text(it))
    # A token the lexicon expands is NOT uncovered: its atoms live under the catalog's English
    # vocabulary (the Spanish word for "experience" -> ux -> design-engineer). Without this
    # discount, the <uncovered> block contradicted the very scoring that had just got it right
    # through that same token.
    synonyms = lexicon.get("synonyms", {})
    uncovered = {t for t in raw if len(t) >= 5 and t not in catalog_tokens
                 and not synonyms_for(t, synonyms)
                 and not any(t in ct or ct in t for ct in catalog_tokens)}

    return {
        "catalog": catalog, "role": role, "mods": mods, "steps": steps,
        "ranked": (role_ranked, mod_ranked, step_ranked),
        "evidence": evidence, "role_bodies": role_bodies,
        "raw": raw, "expanded": expanded, "uncovered": uncovered,
        "directives": dir_, "lexicon": lexicon,
    }


# ---------------------------------------------------------------------------
# invariants — derived from INVARIANTS.md, never rewritten here
# ---------------------------------------------------------------------------

def compact_invariants() -> list:
    """Extracts the `## N. Title` headings of <harness>/INVARIANTS.md. Deriving instead of
    copying is what keeps this list and the file from drifting apart: if someone adds a
    commandment, it shows up on its own. The list is the run of numbered headings; the first
    unnumbered `##` after it (an appendix such as "What's not here") ends it. No file, no
    block."""
    text = read_text(INVARIANTS_FILE)
    if not text:
        return []
    found = []
    for m in re.finditer(r"^##\s+(.+?)\s*$", text, re.M):
        title = m.group(1)
        if re.match(r"\d+\.", title):
            found.append(title)
        elif found:
            break
    return found


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def localize(text: str) -> str:
    """Atom bodies are written against the default layout (`.harness/...`). When this project's
    harness lives elsewhere, point those references at the real place."""
    if HARNESS_REL == ".harness":
        return text
    return text.replace("`.harness/", "`" + HARNESS_REL.rstrip("/") + "/")


def render_invariants() -> list:
    commandments = compact_invariants()
    if not commandments:
        return []
    out = ["<invariants>",
           "What is not up for discussion in this project. The detail and the why of each one",
           f"is in `{display(INVARIANTS_FILE)}`; open the one that affects you before you act."]
    out.extend(f"  {m}" for m in commandments)
    out.append("</invariants>")
    out.append("")
    return out


def render(r: dict, full: bool) -> str:
    out = render_invariants()

    role, mods, steps, card = r["role"], r["mods"], r["steps"], r.get("card")

    if not full:
        label = (f"the role from card {card}" if card else role["id"]) \
            + (" + " + ", ".join(m["id"] for m in mods) if mods else "")
        out.append(f"<atoms>Still mounted: {label}. No changes since the previous turn.</atoms>")
        return "\n".join(out)

    out.append("<atoms>")
    out.append("The market's atom set resolved for this batch. Adopt it as your working")
    out.append("configuration.")
    out.append("")
    out.append("Laws:")
    out.append("- There is ONE active role. Two personas are never mixed.")
    out.append("- Mods stack on top of the role. On a clash, the order is")
    out.append("  security > correctness > scope > style; on a tie, the first listed wins.")
    out.append("- What the user asks for rules over both, and the invariants rule over all.")
    out.append("  Atoms shape HOW you work; they neither widen nor reinterpret WHAT was asked.")
    if r["evidence"]:
        out.append(f"- Project signals: {', '.join(r['evidence'][:12])}")
    out.append("")

    if card:
        which = "the card this iteration picks" if card == "loop" else f"card {card}"
        out.append(f'<role source="card" card="{card}">')
        out.append(f"No role is scored from this prompt's wording: {which} names it (the `backlog`")
        out.append("skill, \"Work under the card's contract and role\").")
        out.append("1. Read the card and its category's contract. An unmet entry contract sends the")
        out.append("   card back to refinement with a comment listing what is missing; it is not")
        out.append("   worked on a guess.")
        out.append("2. The role is one of the roles the board allows for the card; when several fit,")
        out.append(f"   the one for what the card touches. Load `{MARKET_REL}/roles/<id>.md` and adopt")
        out.append("   it, with every mod its `roles/<id>.json` lists under `requires.atoms` (a review")
        out.append(f"   role's `rule-enforcer`, at `{MARKET_REL}/mods/<mod>.md`). The action plan opens")
        out.append("   with `Role: <id>` and why.")
        out.append("3. The closing comment walks the exit contract item by item and names the role.")
    else:
        out.append(f'<role id="{role["id"]}">')
        out.append(localize(r["role_bodies"].get(role["id"], "").strip()))
    out.append("</role>")
    out.append("")

    if mods:
        out.append("<constraints>")
        for m in mods:
            out.append(f'<mod id="{m["id"]}">')
            out.append(localize(read_text(m["path"]).strip()))
            rt = m.get("runtime") or {}
            if rt.get("blockTools"):
                out.append(f"RUNTIME: tools forbidden while this mod is active — {', '.join(rt['blockTools'])}.")
            if rt.get("contract"):
                out.append(f"RUNTIME CONTRACT: {json.dumps(rt['contract'], ensure_ascii=False)}")
            out.append("</mod>")
        out.append("</constraints>")
        out.append("")

    if steps:
        out.append("<suggested_plan>")
        out.append("Atomic market steps that fit, in execution order. It is a starting skeleton,")
        out.append("not a mandate: drop or reorder whatever does not apply.")
        for i, p in enumerate(steps, 1):
            out.append(f'{i}. {p["id"]} — {p["description"]}  (`{MARKET_REL}/steps/{p["id"]}.md`)')
        out.append("</suggested_plan>")
        out.append("")

    if r["uncovered"]:
        out.append("<uncovered>")
        out.append("Terms from the request with no atom in the catalog: "
                   + ", ".join(sorted(r["uncovered"])[:12]) + ".")
        out.append("Do not invent atoms for them. If one keeps recurring, it is a candidate to")
        out.append("enter the market.")
        out.append("</uncovered>")
        out.append("")

    out.append(f"Full catalog in `{MARKET_REL}/`. Override with @role:<id> / @mod:<id>,")
    out.append("skip with @noatoms, or use the `atoms` skill to inspect and reassemble.")
    out.append("</atoms>")

    text = "\n".join(out)
    if len(text) > BUDGET:
        text = text[:BUDGET].rsplit("\n", 1)[0] + "\n[set trimmed by the context budget]\n</atoms>"
    return text


# ---------------------------------------------------------------------------
# hook mode
# ---------------------------------------------------------------------------

def state_path(session: str) -> Path:
    return STATE_DIR / (re.sub(r"[^A-Za-z0-9_-]", "_", session or "no-session")[:80] + ".json")


def hook_mode() -> int:
    """Reads the UserPromptSubmit JSON from stdin and writes the block to stdout. It never
    blocks: this prepares the batch, it does not police an invariant."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    prompt = str(payload.get("prompt") or payload.get("user_prompt") or "").strip()
    session = str(payload.get("session_id") or "")
    cwd = Path(payload.get("cwd") or ROOT)
    if not cwd.is_dir():
        cwd = ROOT

    lexicon = load_lexicon()
    dir_ = directives(prompt, lexicon)
    if dir_["skip"] or not prompt or prompt.startswith("/") or prompt.startswith("!"):
        return 0

    card = None if dir_["roles"] else card_source(prompt)
    forced = bool(dir_["roles"] or dir_["mods"] or card)
    if not forced:
        if len(prompt) < MIN_CHARS:
            return 0
        expanded, raw = expand(prompt, lexicon)
        if len(raw) < MIN_TOKENS:
            return 0
        if not has_work_verb(prompt, lexicon):
            # With no work verb we only continue if the wording lands squarely in the catalog.
            catalog = load_catalog()
            probe = rank(catalog["roles"], expanded, {})
            if not probe or probe[0][1] < MIN_POINTS * 2:
                return 0

    # The key's prefix is not intent: "JAVA-12" must not score the Java-flavored mods.
    r = resolve(CARD_KEY.sub(" ", prompt) if CARD_KEY else prompt, cwd)
    if r is None:
        return 0

    r["card"] = card
    who = f"card:{card}" if card else r["role"]["id"]
    fingerprint = f"{who}|{','.join(sorted(m['id'] for m in r['mods']))}"
    path = state_path(session)
    previous = read_json(path, {})
    same = isinstance(previous, dict) and previous.get("fingerprint") == fingerprint \
        and not dir_["refresh"]

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "fingerprint": fingerprint, "role": who,
            "mods": [m["id"] for m in r["mods"]], "steps": [p["id"] for p in r["steps"]],
            "project": str(ROOT), "cwd": str(cwd),
            "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    sys.stdout.write(render(r, full=not same))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(hook_mode() if len(sys.argv) > 1 and sys.argv[1] == "hook" else 0)
    except Exception:
        sys.exit(0)   # fail open: a broken engine cannot stall a batch
