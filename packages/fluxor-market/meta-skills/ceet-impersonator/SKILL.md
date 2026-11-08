---
name: ceet-impersonator
description: Drafts a simulated CEET pack for any role from evidence instead of an interview — a public figure's published work, or the work of someone who has recorded their own consent (a colleague, a repository author). Use when a user wants a draft cognitive clone of how a specific person works in a role and that person is not the one being interviewed. Every directive is traced to a source or marked unknown, and the pack is rendered and validated by ceet-core.
---

# CEET — Impersonator

## What this skill does

Fills a role's cognitive profile from **evidence** instead of a first-person interview, and renders it
into a **simulated pack** that follows the [pack contract](../ceet-core/references/pack-contract.md):
the same agents, skills, commands, rules and hooks an interview pack gets, each file labeled with the
Simulation Notice, plus an `evidence-map.md` that traces every directive to its source. The roles are
installed next to this skill (`../ceet-<role>/`); paths here are relative to this skill's directory.

## Who may be simulated

There are two bases, and nothing else (`consent.basis` in the pack, checked by the validator):

1. **`public-work`: a public figure**, from public, work-related material only (talks, published
   writing, public code, documented public decisions). The pack is never used commercially and never
   published, sold or marketed under their name.
2. **`consent`: anyone else**, repository authors and colleagues included, only with **their own
   recorded consent** ([consent](../ceet-core/references/consent.md)): they heard the statement and
   agreed to the uses. An operator's or employer's authorization is not consent.

Refuse everything else, and the uses no pack may serve (evaluation, hiring or screening, task
allocation by traits, promotion or termination, monitoring). The full policy is
[`references/safety-policy.md`](references/safety-policy.md).

## Inputs

1. `target_role`: one of the installed `ceet-*` roles.
2. `subject` and `basis`: who, and on which of the two bases above. For `consent`, the consent record.
3. `output_slug`: a kebab-case name for the pack folder that does not name the subject, e.g.
   `backend-simulated-01`.
4. The evidence: public sources for `public-work`; for `consent`, what the person agreed to share
   (a repository and author identity, documents).

## Run order

1. **Scope.** Confirm the basis. For `consent`, record it before reading anything
   (`../ceet-core/scripts/interview.py statement` gives the statement the person hears).
2. **Load the directive surface.** Every slot the role declares is in
   `../<target_role>/templates/cognitive-profile.md`; its form is `../<target_role>/interview/form.json`.
3. **Collect and map evidence** following [`references/mapping-protocol.md`](references/mapping-protocol.md):
   behavior at work, repeated patterns over anecdotes, never traits.
4. **Write `evidence-map.md`** in `.harness/packs/<output_slug>/`: the Simulation Notice under its title,
   then the contract v2 table with **one row per directive the role declares**:

   ```markdown
   | Ref | Directive | Confidence | Source | Evidence |
   |---|---|---|---|---|
   | E1 | `directives.architecture.style` | medium | https://… | What the source shows. |
   | E2 | `directives.testing.tdd_reality` | unknown | — | No evidence found. |
   ```

   A source is a URL, a commit (the bare hash as the whole cell, or `commit: <hash>`), or
   `doc: <document>`. `unknown` rows have no source.
5. **Write `cognitive-profile.json`** (`../ceet-core/schemas/cognitive-profile.schema.json`) with
   `source: "simulation"` and the consent record. A directive or identity slot with evidence cites its
   own rows as `[E<n>]`; one without is `{"_status": "not_synthesized", "_note": "unknown: no evidence found."}`.
   `identity.core_values` and `identity.frustration_triggers` are always
   `{"_status": "not_synthesized", "_note": "never simulated: this slot describes a trait."}`, and those
   two notes are the only ones a simulation takes. Nothing in it is an inferred trait, and there is no
   `private/reflection.md`.
6. **Render** with ceet-core, which adds the Simulation Notice to every file it writes:

   ```bash
   python3 ../ceet-core/scripts/render_pack.py render .harness/packs/<output_slug>          # review
   python3 ../ceet-core/scripts/render_pack.py render .harness/packs/<output_slug> --write
   ```

7. **Validate.** A non-zero exit means the pack is not loaded or shared:

   ```bash
   python3 scripts/validate_pack.py .harness/packs/<output_slug>
   ```

   It is ceet-core's validator (this skill requires `ceet-core@2`) and refuses any pack that is not
   `source: simulation`.

## Completion criteria

1. The role's full artifact set is rendered in the pack folder, never inside a skill folder.
2. Every directive has an evidence row; every populated directive cites sourced rows.
3. Every file, the evidence map included, carries the Simulation Notice.
4. Uncertainty is explicit: `low` or `unknown`, never invented precision.
5. `scripts/validate_pack.py` exits 0.
