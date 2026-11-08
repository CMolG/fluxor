# Impersonator mapping protocol

How evidence becomes directive values in a simulated pack. The formats are ceet-core's
[pack contract](../../ceet-core/references/pack-contract.md); who may be simulated is the
[safety policy](safety-policy.md).

## 1. The directive surface

1. Read the role's `templates/cognitive-profile.md` (`../<role>/templates/` from this skill) and list
   every `{directives.<domain>.<field>}` slot. Each one gets a row in the evidence map, even if the row
   is `unknown`.
2. The role's `interview/form.json` says what each directive means: the questions that feed a slot
   (`feeds`) are what the evidence has to answer.
3. The `{identity.*}` slots are optional: `cognitive_signature`, `decision_framework` and
   `communication_voice` are filled only from their own sourced rows, like a directive, and
   otherwise left not synthesized with no row. `core_values` and `frustration_triggers` are never
   filled and get no row: a value or a frustration is a motive ([safety policy](safety-policy.md)).

## 2. Allowed evidence

| Basis | Allowed | Not allowed |
| --- | --- | --- |
| `public-work` | Public talks and interviews, published writing, public code, publicly documented decisions | Rumor, unsourced claims, private channels, fabricated quotes |
| `consent` | What the person agreed to share: their commits, diffs and review comments in a named repository, documents they provided | Anything outside what they agreed to; HR or private context |

## 3. From evidence to a value

1. Prefer repeated signals over one-off anecdotes; say when a directive rests on one source.
2. Write the value as the person's practice, in work language (`"I split migrations into expand and
   contract. [E4]"`), never as a personality label.
3. Confidence:
   - `high`: several converging sources;
   - `medium`: partial evidence, plausible reading;
   - `low`: a thin signal, worded conservatively;
   - `unknown`: nothing found. The slot is then not synthesized, and cites no row.
4. A slot left empty says why with one of two fixed notes, never free text, so nothing about the
   person reaches the pack outside the evidence map: `unknown: no evidence found.`, or
   `never simulated: this slot describes a trait.` for the two traits in §1.
5. Keep role fit explicit: evidence from outside the role's context is `low` at most.

## 4. The evidence map

`evidence-map.md` in the pack folder: a title, the Simulation Notice, then the contract v2 table.

```markdown
# Evidence map

> **Simulation Notice:** …

| Ref | Directive | Confidence | Source | Evidence |
|---|---|---|---|---|
| E1 | `directives.architecture.style` | high | https://… | Two talks and a design doc describe the same split. |
| E2 | `directives.testing.tdd_reality` | unknown | — | No evidence found. |
```

- `Ref` is `E<n>`, unique: a ref used by two rows fails validation. The profile cites it as `[E<n>]`.
- `Source` is a URL, a commit (the bare hash as the whole cell, or `commit: <hash>`), or
  `doc: <document>`. A row without one is only valid as `unknown`.
- A directive may have several rows. A populated directive cites at least one of **its own** rows
  that is not `unknown`, and never a row the map gives to another directive; `[teachback]` alone
  does not back it.

## 5. Render and validate

ceet-core renders the pack from `cognitive-profile.json` and adds the Simulation Notice to every file
it writes; `scripts/validate_pack.py` then checks all of the above. Nothing is hand-edited after the
render: a change goes into the profile or the evidence map, and the pack is rendered again.
