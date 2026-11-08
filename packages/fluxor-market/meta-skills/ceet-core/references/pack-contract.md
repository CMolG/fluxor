# Pack contract

A **pack** is what a CEET meta-skill produces for one person in one role: the cognitive clone and the
AI environment rendered from it. The same contract covers packs from an interview (`ceet-<role>`) and
simulated packs from public evidence (`ceet-impersonator`). The skills that read packs
(`ceet-autodiscover`, `ceet-sub-agent-orchestration`) rely on it. Version 2 of this contract comes with
ceet-core 2; the JSON formats are in `../schemas/`.

## Where a pack goes

- **Default:** `<harness>/packs/<pack-id>/`, where `<harness>` is `$HARNESS_DIR`, else
  `<project root>/.harness`, and the project root is `$CLAUDE_PROJECT_DIR`, else
  `git rev-parse --show-toplevel`, else the current directory.
- **`<pack-id>`:** `<role>-<person>` in kebab-case, `<role>` being the meta-skill id without `ceet-`
  (`backend-engineer-alex`). A simulated pack uses the `output_slug` the user chose.
- **Never inside a skill folder.** Installed skills are managed files: the harness compares them
  against their content hash and reports an edit as drift.
- **A pack is personal data** ([consent](consent.md)). It carries its own `.gitignore` files:
  `private/` is always ignored, and the whole pack is ignored unless the person chose
  `storage: repository`.

## Layout

```
<pack-id>/
├── pack.json                manifest: meta-skill and form versions, source, consent, templates hash,
│                            the SHA-256 of every shared file, the adapter files installed in the project
├── core.md                  the short always-on core: how the person thinks, decides and speaks, their
│                            best-evidenced directives, and an index of what loads on demand
├── cognitive-profile.md     the full clone for people: the role's profile template, every slot filled
├── cognitive-profile.json   the ground truth everything is rendered from (no verbatim answers)
├── examples/
│   ├── decisions.json       real decisions with their rationale
│   └── decisions.md         the same, readable
├── agents/ skills/ commands/ rules/     the role's templates, rendered, at the same relative paths
├── hooks/                   engineering roles: judgment at git events (*.md) and checks.json
├── bin/                     ceet_check.py and examples.py, copied so the pack runs on its own
├── adapters/<tool>/         native files for Claude Code, Cursor, Copilot, AGENTS.md, Agent Skills
├── README.md                what the pack is, how to load it, how to erase it
├── evidence-map.md          simulated packs only: every directive's evidence, source and confidence
├── profile-changelog.md     what moved at each re-profile, newest first (render_pack.py reprofile)
└── private/                 never shared, never loaded by an agent doing work
    ├── answers.json         the consent record and every answer, verbatim (the interview state)
    ├── reflection.md        what synthesis inferred and the person did not say (interview packs only)
    ├── teachback.md         directives with their evidence, for the person's review
    └── teachback.json       the person's verdicts
```

Only `cognitive-profile.json`, `examples/decisions.json`, `private/*` and (for simulations)
`evidence-map.md` are written by the synthesis. Everything else is written by
`scripts/render_pack.py`, deterministically, and listed with its hash in `pack.json`; an edit shows as
drift in `validate_pack.py`.

## Re-profiling and `profile-changelog.md`

A re-profile never overwrites `cognitive-profile.json` in place. The new synthesis goes to a scratch
file, and `render_pack.py reprofile <pack> --profile <new.json> [--decisions <new.json>]` compares it
with the pack's profile: every `identity.*` and `directives.*` slot, `checks.<kind>`,
`contradictions.<Qa>-<Qb>` and `decisions.<id>`, each added, removed or changed with what it cites.
Without `--write` it only prints that; with it, it replaces the profile (and the decisions), sets
`meta.version` (minor bump, major when the old profile answered another major of the form) and
`meta.date`, puts one entry at the top of `profile-changelog.md`, and renders as `render --write` does,
with the adapters the pack already has unless `--adapter` says otherwise. If the render refuses, the
pack is left as it was. Nothing moved: nothing is written.

The new profile must be answered against the role's current form (the same major `formVersion`), or
it is refused. Simulated packs are re-profiled through `ceet-impersonator`.

Each entry is a heading `## <date> · profile <old> → <new>` and one `- ` line per moved item: the
slot, what it cites, and its new value through the render's sanitizer on one line. It carries the
profile's own synthesized values, never an answer. The changelog is a shipped source like the
profile: hashed in `pack.json`, so a hand edit is drift, and `validate_pack.py` reports an entry with
another heading or nothing listed.

## Loading

| Loads | What |
| --- | --- |
| Always | `core.md`. Short on purpose: models follow fewer instructions reliably as their number grows, and drift from long system prompts. |
| With the task | The one agent, skill, command or rule file that matches it; each carries the directives of its own domain. |
| As demonstrations | The three to five decisions of `examples/` closest to the task (`bin/examples.py select`, or the Claude Code `UserPromptSubmit` hook the adapter offers). |
| Never, for work | `cognitive-profile.md` (for people), `private/`. |

## Rendering

- Each file under the role's `templates/` renders to the same relative path
  (`templates/agents/code-reviewer.md` → `agents/code-reviewer.md`).
- A slot `{a.b.c}` takes the value at `a` → `b` → `c` of `cognitive-profile.json`; the role's name
  slot takes `name`; `{meta.date}`, `{meta.version}` and `{meta.fingerprint_hash}` come from `meta`
  (the render fills a missing date, `1.0.0`, and the first 12 hex characters of the SHA-256 of the
  answers, sorted keys, no whitespace). `{identity.contradictions}` is rendered from `contradictions`
  when it has no value of its own.
- **No slot survives.** A slot without evidence is `{"_status": "not_synthesized", "_note": "..."}`
  in the JSON and renders as "Not synthesized: <note>".
- **Every value is sanitized** (invisible, bidirectional and control characters removed; hidden
  comments and import lines escaped; instruction-like text flagged for review). The sources the
  pack ships as they are (`cognitive-profile.json`, `evidence-map.md`, `examples/decisions.json`)
  have their invisible and bidirectional characters stripped in place too.
- Directive values are first person and cite `[Q<n>]` (a question of the form they were answered
  against, `formVersion`), `[E<n>]` (a row of a simulated pack's evidence map) or `[teachback]` (the
  person's own wording at teachback).
- A simulated pack gets the Simulation Notice under the first heading of every file.

## `cognitive-profile.json`

`../schemas/cognitive-profile.schema.json`; which slots a role requires comes from its
`templates/cognitive-profile.md`. Required: `schemaVersion` (`2.0.0`), `artifactType`, `role`,
`formVersion`, `source` (`interview` or `simulation`), `name`, `consent`, `identity`, `directives`.
Optional: `meta`, `contradictions`, `checks` (rules precise enough to run as a check, each with the
question it came from and, for a banned pattern, a line it must block and one it must pass),
`review.specialCategoryCleared`, `teachback`.

## `pack.json`

`../schemas/pack.schema.json`: `packId`, `metaSkill` (`id@version` when known), `formVersion`,
`source`, `profileVersion`, `renderedAt`, `consent`, `templatesHash` (the template set it was rendered
from), `files` (path and SHA-256 of every shared file) and `installed` (adapter files copied into the
project, so erasure can remove them).

## Delivered through Fluxor online

A project whose harness comes from Fluxor online (`fluxor-sync`) can carry a pack to the person's
other projects and machines, without committing it:

- `fluxor-sync pack publish <pack-id>` uploads the pack as rendered: every file `pack.json` lists, plus
  `pack.json` and the root `.gitignore`, **never `private/`**. Fluxor keeps it only when every sha256
  matches `pack.json`, the pack comes from an interview (`source: interview`) under
  `ceet-consent-2`, and the account still holds that consent for the role. Re-render before
  publishing a pack you edited; publishing again replaces it.
- Every project it is attached to receives it at `<harness>/packs/<pack-id>/` on its next pull: a
  shared copy (no `private/`, so `validate_pack.py` warns "a shared copy?"), with its `.gitignore`, and
  the writer's own lock in `.fluxor/`. An edit to a synced file is kept and reported as drift.
- `core.md` loads at session start from the writer's output, never from a committed `AGENTS.md`
  line. The hooks the Claude Code adapter declares run only after the person approves them
  (`fluxor-sync approve --consented <pack-id>:ceet-check`), and again after a `bin/` script changes.
- `fluxor-sync pack detach <pack-id>` takes it off this project, `pack unpublish` off Fluxor; erasing
  the interview or withdrawing consent in Fluxor does too. The next pull removes what the writer
  wrote; the copy on the machine that rendered it, and its `private/`, stay until `render_pack.py
  erase`.

## Simulated packs

`ceet-impersonator` writes packs from evidence instead of an interview. On top of the above:

- `source: simulation`, no `private/answers.json`, no `private/reflection.md`, and a consent record
  with `basis: public-work` (a public figure, from public work material) or `basis: consent` (anyone
  else, who agreed);
- `evidence-map.md` is a table `| Ref | Directive | Confidence | Source | Evidence |` with **one row
  per directive the role declares**: a source (a URL, a commit as the whole cell or `commit: <hash>`,
  or `doc: <document>`) and a confidence of `high`, `medium` or `low`, or `unknown` with no source; a
  directive with only `unknown` rows is not synthesized, and a populated one cites its own rows as
  `[E<n>]`, at least one of them sourced (a row of another directive does not count). Each `E<n>`
  names one row: a ref used twice is an error, never "the last row wins";
- an `identity.*` slot follows the same rule: populated only when it cites its own sourced rows,
  otherwise not synthesized. It needs no row to be left empty. A simulation has no `contradictions`
  list (its items cite interview questions);
- `identity.core_values` and `identity.frustration_triggers` are **never populated** in a
  simulation, and the evidence map gives them no row: a value or a frustration is a motive, which
  a simulated pack does not infer (the impersonator's safety policy, "No inferred traits");
- a not-synthesized slot's `_note` is one of two fixed reasons, never free text, which would carry
  a claim about the person past the evidence map: `unknown: no evidence found.`, or
  `never simulated: this slot describes a trait.` for the two slots above;
- every file carries the Simulation Notice;
- the pack passes `scripts/validate_pack.py` before anyone loads it.

## Versioning

`schemaVersion` of `cognitive-profile.json` and `pack.json` follows SemVer: patch for clarifications,
minor for a new optional key, major for a rename, a removal or a changed meaning. A role whose
templates rename or drop a slot is a major bump of that meta-skill: existing packs no longer match it.
A role whose form changes what a question id asks is a major bump of its `formVersion`.
