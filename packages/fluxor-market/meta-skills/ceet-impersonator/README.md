# CEET impersonator

A **skill** that drafts any CEET role pack from evidence instead of an interview: a *simulated pack*.
Runs inside any AI assistant that loads Anthropic-style skills; the renderer and the validator are
ceet-core's and need Python 3.9+.

## Who it simulates

1. **A public figure** (`basis: public-work`), from public, work-related material only. Never used
   commercially, never published or marketed under their name.
2. **Anyone else** (`basis: consent`), repository authors included, only with their own recorded
   consent. An operator's authorization is not enough.

The rules are in [`references/safety-policy.md`](references/safety-policy.md).

## What it produces

In `.harness/packs/<output-slug>/` of your project (the
[pack contract](../ceet-core/references/pack-contract.md)):

1. `evidence-map.md`: one row per directive the role declares, `| Ref | Directive | Confidence | Source | Evidence |`,
   each with a source (URL, commit, `doc: <document>`) or an explicit `unknown`.
2. `cognitive-profile.json`: `source: simulation`, the consent record, directives citing `[E<n>]`.
3. Everything ceet-core renders from those two: `core.md`, `cognitive-profile.md`, the role's agents,
   skills, commands, rules and hooks, adapters and `pack.json`, each file with the Simulation Notice.

## How to run it

1. Ask your assistant to run `ceet-impersonator` with a `target_role` (e.g. `ceet-backend-engineer`),
   the subject and basis, and an `output_slug` that does not name the subject.
2. Render and validate:

   ```bash
   python3 ../ceet-core/scripts/render_pack.py render .harness/packs/<output-slug> --write
   python3 scripts/validate_pack.py .harness/packs/<output-slug>
   ```

There is no shipped example pack: the tests build a synthetic one
(`../ceet-core/tests/support.py`, `simulated_pack`).

## Related docs

1. [`references/mapping-protocol.md`](references/mapping-protocol.md): how evidence becomes directives.
2. [`references/safety-policy.md`](references/safety-policy.md): who may be simulated, and the refusals.
