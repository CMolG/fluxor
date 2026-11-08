# locale-es: Spanish Localization Completeness

When this modifier is active, the agent guarantees that the project's Spanish catalog is a COMPLETE and ACTUALLY TRANSLATED mirror of the English source catalog — every key the English catalog defines exists in the Spanish one with a real Spanish value, never the English string left untouched.

## Catalog location

The runtime contract checks the default locations, `src/i18n/es.ts` against the source `src/i18n/en.ts` (either may be `.tsx`), because the engine needs static path patterns. Those defaults are the only layout this mod verifies: a project whose catalogs live elsewhere (another path, JSON or YAML files, one file per namespace) should not enable this mod until the location is configurable, because the contract would check files the project does not use.

## Rules

1. **Full key parity with English.** Every dotted key present in the English source catalog MUST also exist in the Spanish catalog. No missing keys, no keys deferred "for later."
2. **Every value is a REAL Spanish translation.** Copying the English string verbatim into the Spanish catalog is a rejection, not a translation — every value must read as natural Spanish. An identical English/Spanish value pair is only acceptable for genuine brand names, proper nouns, or code-like tokens, never for actual sentences or labels.
3. **Never empty, never a stub.** No value may be `''`, `'TODO'`, the bare key name, or a placeholder. A missing translation is worse than an obviously-fake one — both fail the same way, but a silent stub hides the defect.
4. **Preserve ICU placeholders exactly.** Named interpolations and plural/select forms (`{name}`, `{count, plural, one {# item} other {# items}}`) must survive translation untouched in form, translated only in their surrounding literal text and plural category text.
5. **Identical flat dotted keys as the source.** The Spanish catalog's shape mirrors the English one exactly — same flat structure, same key strings, only the values differ. Never nest, rename, or reorganize keys relative to the source.
6. **Track the source, don't lag it.** Whenever the English catalog gains a new key, the Spanish catalog must gain the same key with a real translation in the same change — a translated catalog that was complete last week is incomplete today if the source moved on.

## Behavioral Overrides

- Before declaring any step "done," the agent diffs the keys of the English and Spanish catalogs — any key present in one and absent in the other fails the step.
- The agent never ships a Spanish value that is byte-identical to its English counterpart unless the underlying concept (a proper noun, a brand, a code) is genuinely language-invariant.
- If a Spanish translation would require a sentence restructure to sound natural (word order, gendered agreement), the agent restructures it — a literal word-for-word substitution that reads as broken Spanish is treated as untranslated.
- If the agent is uncertain about regional Spanish variance (e.g. `es-MX` vs `es-ES` vocabulary), it defaults to broadly neutral, international Spanish and does not fragment the catalog into regional sub-locales unless explicitly asked.
