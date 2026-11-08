---
name: atoms
description: Inspect, explain or change the market's atom set — the role, the mods and the steps the preparation hook mounts for each batch. Use it when the user asks which role is active, asks for a different role or modifier ("switch to the X role", "turn on the Y mod", "change roles"), asks why an atom was picked, wants to see the catalog of roles/mods/steps, wants to wire the atoms hook into a project, or wants to add a new atom to the market. Also to reassemble the set when the task changes topic mid-session.
---

# Atoms

The market holds the composable pieces of an agentic configuration, ported from the Fluxor IDE's
market. Paths below are relative to the market directory:

- **Roles** (`roles/`) — **who** works. A persona: expertise, decision-making principles,
  quality standards, boundaries. **Only one is active at a time.** Mixing two produces an agent with
  multiple personalities that dilutes its own judgment; if the task genuinely spans front and back,
  that is what `full-stack-engineer` is for.
- **Mods** (`mods/`) — **how** the work is done. Stackable constraints injected as execution
  rules. Some declare an `exclusiveGroup` (two design systems can never stack) or an explicit
  `incompatibleWith`.
- **Steps** (`steps/`) — **one move**. Reusable atomic units that compose into a plan.

Every atom is **two things**: an `.md` with the prompt and a card in `inventory.json`. A card with
no `.md` is dropped at load time; an `.md` with no card is invisible to everyone.

The market also carries `lexicon.json` (the vocabulary that maps prompts, including Spanish ones,
onto the catalog) and `motor.py` (the scoring engine). The hook and the CLI below both import
`motor.py`, so what `atoms why` reports is exactly what the hook mounts.

## Layouts

The engine uses the catalog it sits next to, so the market works in either place:

| Layout | Market | Skill |
| --- | --- | --- |
| Project harness | `<harness>/market/` | `<harness>/skills/atoms/` (reached through `.claude/skills`) |
| Publishing repository | `market/` at the repository root | `skills/atoms/` |

Locations follow `.harness/contracts/harness-convention.md` (Fluxor's market): project root = `$CLAUDE_PROJECT_DIR`, else
`git rev-parse --show-toplevel`, else the current directory; harness = `$HARNESS_DIR` (relative
paths resolve against the root), else `<root>/.harness`. `atoms.py` looks for
`<harness>/market/motor.py` first and then `market/motor.py` two levels above itself, which covers
both rows of the table.

Optional parts degrade instead of failing:

- `<harness>/INVARIANTS.md` present: its `## N. Title` headings are prepended to every mounted set
  (the run of numbered headings; the first unnumbered `##` after them ends the list). Absent:
  silently skipped.
- `<harness>/config/atoms.json` absent: defaults apply.
- No market in the harness: the hook still emits the invariants, and `atoms.py` says what to copy.

Rendered text names paths relative to the project root (or absolute when outside it). Atom bodies
are written against the default `.harness/` layout; when the harness lives elsewhere, the engine
rewrites their `` `.harness/ `` references to the real location.

## The preparation hook

`hooks/prepare-batch.sh` (in this skill) is the `UserPromptSubmit` "preparation" hook of the
harness convention: it prepends the invariants and the atom set resolved for the prompt. It is the
deterministic half of Fluxor's Meta-Agent (the lexical discovery pass); you do the assembling with
the injected block. No network, no extra model.

It stays quiet on greetings, short loose sentences, slash commands and `!` commands, and it only
re-injects the full set when it **changes** within a session: if it is still the same, it leaves
one line as a reminder. A long session does not pay twice for the same persona. The per-session
cache lives in the system temp directory (`atoms-state/<hash of the project root>/`), never in the
tree.

It never blocks and fails open at every step: no `jq` means silence (it cannot emit well-formed
JSON), no Python 3.9+ or no market means invariants only, and any error exits 0.

Wire it in the project's `.claude/settings.json` (merge into an existing `hooks` object):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.harness/skills/atoms/hooks/prepare-batch.sh",
            "timeout": 10,
            "statusMessage": "Preparing the batch"
          }
        ]
      }
    ]
  }
}
```

The path assumes the skill is installed at `.harness/skills/atoms/`; adjust it if yours lives
elsewhere. The script must be executable (`chmod +x`) and needs `bash`, `jq`, and Python 3.9+
for the atom set.

## Overrides in any prompt

| Directive | Effect |
| --- | --- |
| `@role:<id>` | Forces that role over the scored one (the first one wins if repeated). |
| `@mod:<id>` | Attaches that mod (repeatable). Forced mods are placed first, win conflicts inside their exclusive group, and bypass `never_auto`. |
| `@noatoms` | Skips the whole block for this prompt, invariants included. |
| `@atoms:refresh` | Re-injects the full set even if nothing changed. |

Directives are case-insensitive. `lexicon.json` → `directive_aliases` maps extra spellings to
them (for example, Spanish-language aliases).

If the user asks for a role by name, apply it right away by reading `roles/<id>.md` — do not wait
for the next turn's hook.

**A prompt about a board card takes its role from the card, not from its wording** (when the
project sets `cards` in its config). The wording of "work PROJ-12" knows nothing about the card, so
scoring it would mount a persona the board never allowed: the hook mounts the mods and steps as
usual, and in place of a role body it says that the role is one of the card's eligible roles, chosen
once the card is read (the `backlog` skill, "Work under the card's contract and role"). An
autonomous loop's prompt, which names no card because the iteration picks it, is recognized by
`cards.loopMarkers`. `@role:<id>` still wins.

## Commands

```bash
A=.harness/skills/atoms/atoms.py     # or skills/atoms/atoms.py in the publishing repository

python3 $A current                   # what the hook mounted last in this project
python3 $A mount "<intent>"          # what would be mounted; --full prints the whole block
python3 $A why "<intent>"            # scores, thresholds, config and what the lexicon added
python3 $A list [roles|mods|steps]   # the catalog
python3 $A show <id>                 # an atom's full text
python3 $A --max-mods 5 mount "..."  # override the mod cap for one run
```

`why` is the diagnostic tool: if an atom never gets picked, it is almost always that the lexicon has
no vocabulary reaching it, not that the scoring is wrong.

## Configuration: `<harness>/config/atoms.json`

Every key is optional; the file itself is optional. Environment variables override the file.
`config.schema.json` in this skill is the file's JSON Schema and `config.example.json` is the
example below. The engine ignores keys it does not know, so a typo silently does nothing; the
schema rejects them. A `$`-prefixed key (for example `"$comment"`) is a comment.

| Key | Env override | Default | Meaning |
| --- | --- | --- | --- |
| `maxMods` | `ATOMS_MAX_MODS` | `3` | Cap on stacked mods per set. |
| `budget` | `ATOMS_BUDGET` | `14000` | Character budget for the injected block; the tail is trimmed beyond it. |
| `minChars` | `ATOMS_MIN_CHARS` | `20` | Prompts shorter than this mount nothing (unless a directive forces it). |
| `minTokens` | `ATOMS_MIN_TOKENS` | `3` | Minimum meaningful words for a prompt to mount a set. |
| `neverAuto` | — | `[]` | Atom ids (roles or mods, case-insensitive) never picked from wording in this project, added to the lexicon's `never_auto`. Still attachable with `@role:` / `@mod:`. |
| `allowAuto` | — | `[]` | Atom ids (case-insensitive) removed from the lexicon's `never_auto` for this project, so wording can pick them (e.g. `ds-house`, which is opt-in because it only makes sense with an in-house design system). |
| `signals` | — | `{}` | Extra project detectors merged over the lexicon's `project_signals` (an entry here replaces the lexicon's entry of the same name): `{"package.json": {"<dependency or scope>": [tokens]}, "files": {"<path>": [tokens]}}`. Signals only break exact score ties. |
| `cards` | — | off | Card-driven roles: `{"keyPrefixes": ["PROJ"], "loopMarkers": ["<path of the loop's prompt>"]}`. A prompt naming `PROJ-12`, or carrying a marker, mounts no scored role (see above), and the key is not scored. |

Complete example (illustrative names):

```json
{
  "maxMods": 4,
  "budget": 16000,
  "minChars": 20,
  "minTokens": 3,
  "neverAuto": ["ds-shadcn", "ds-tailwind"],
  "allowAuto": ["ds-house"],
  "signals": {
    "package.json": { "@acme/ui": ["design-system", "house", "ui", "component"] },
    "files": { "packages/ui": ["design-system", "house", "ui"] }
  }
}
```

That example is how a project with its own design system makes `ds-house` the only design-system
mod picked automatically: `ds-house` is opted in, and the substrate mods stay available on
request.

Project signals are read from both the session's directory and the project root (in a monorepo the
root `package.json` is often only the workspace).

## Precedence

The invariants rule over everything. Then what the user asks for; then the mods; then the role;
and last your own defaults. Atoms shape **how** you work: they do not widen, trim or reinterpret
**what** was asked. The `security-hardened` mod does not authorize a security refactor nobody
ordered, and `test-driven` does not turn a one-line fix into a test-suite project.

Among stacked mods the order is **security > correctness > scope > style**; on a tie, the one listed
first wins.

## Adding an atom

Always both files; with only one the atom does not exist.

1. Write `<kind>/<name>.md` following the shape of its neighbors. A role needs Expertise,
   Decision-Making Principles, Quality Standards, an `## Interaction Style` block (Before acting /
   Deliverable shape / Pushback / Voice) and Boundaries. A mod needs Rules and Behavioral Overrides
   written as hard constraints, not as suggestions. Keep it project-neutral: project facts belong
   in `<harness>/config/<name>.json`, which the atom tells the agent to read.
2. Add the card to `inventory.json` with `name`, `icon`, `iconLibrary`, `description`, `tags`
   and `domains`. Mods also accept `exclusiveGroup`, `incompatibleWith` and a `runtime` block
   (`blockTools`, `attachTools`, `contract`).
3. If the atom has to be reachable from Spanish or from the project's files, add the mapping to
   `lexicon.json`. The engine only sees the vocabulary you give it.
4. Check with `python3 $A why "<a prompt that should pick it>"` that it really reaches it, and
   that every card has its `.md` and every `.md` its card.

Each kind's conventions live in `roles/AGENTS.md`, `mods/AGENTS.md` and `steps/AGENTS.md`. Read
them before writing.

## Copies of the market and resyncing

The canonical catalog is the publishing repository's top-level `market/`. A project harness holds a
**copy** in `<harness>/market/`, not a link: what you add in one place does not show up in the
others, and a project may carry local atoms or lexicon entries on purpose. When resyncing, diff in
both directions and move generic improvements upstream; keep project facts in
`<harness>/config/`, never in the shared atoms. The Fluxor IDE's own market has no `lexicon.json`
or `motor.py`, because there an LLM does the assembling; Fluxor opens a project's
`market/inventory.json` when it has one, so the same catalog can be browsed there as is.
