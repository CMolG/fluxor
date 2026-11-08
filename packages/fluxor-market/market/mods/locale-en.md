# locale-en: Source Catalog Completeness (English)

When this modifier is active, the agent guarantees that the project's English catalog is the COMPLETE, authoritative source catalog for every user-facing string in the application. English is the source of truth every other locale translates FROM — if a key is missing here, no other locale can ever define it correctly.

## Catalog location

The runtime contract checks the default location, `src/i18n/en.ts` (or `.tsx`), because the engine needs a static path pattern. That default is the only layout this mod verifies: a project whose English catalog lives elsewhere (another path, JSON or YAML files, one file per namespace) should not enable this mod until the location is configurable, because the contract would check a file the project does not use.

## Rules

1. **English is the source of truth.** Every string a component renders through the project's translation function (for example `t('some.key')`), anywhere in the codebase, MUST have a corresponding entry in the English catalog. A key used but not defined in English is a build-blocking defect, not a nice-to-have.
2. **No missing keys.** Before considering the catalog done, the agent must enumerate every translation call site across the workspace and cross-check it against the catalog's own keys. Any call site without a matching key must be added.
3. **No stubs, no placeholders.** Every value must be a real, shippable English string — never `'TODO'`, an empty string `''`, the bare key name, or a placeholder comment. A stub in the source catalog propagates as a stub to every translated locale.
4. **Flat dotted keys only.** The catalog is a single-level object: `{ 'settings.title': 'Settings', 'auth.login.cta': 'Log in' }`. Never nest namespaces as objects — a flat key lookup silently misses a nested key.
5. **ICU placeholders stay intact and named.** Interpolated values use ICU syntax with named placeholders (`{name}`, `{count, plural, one {# item} other {# items}}`) — never positional concatenation.
6. **Additive, never destructive.** When new UI needs new strings, add new keys — never repurpose or silently rename an existing key that other locales already translate against, since that orphans every translation of it.

## Behavioral Overrides

- Before declaring any step "done," the agent searches the workspace for every translation call and verifies each resolved key exists in the English catalog. A single missing key fails the step.
- If a component is written before its copy is finalized, the agent still adds a real (even if provisional) English string immediately — never a TODO — and revises it in place later.
- If the same concept needs a key in two contexts (e.g., a "Cancel" button in a modal vs. a form), the agent prefers a shared, well-named key ONLY when the strings are genuinely identical in every locale forever; otherwise it creates two distinct keys.
- If a downstream locale mod (e.g. `locale-es`) reports a key it cannot translate because the English source is ambiguous or missing, the agent treats that as a defect in THIS catalog and fixes it here first.
