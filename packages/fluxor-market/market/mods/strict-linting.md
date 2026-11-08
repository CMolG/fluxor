# strict-linting: Zero-Warning Enforcement Modifier

When this modifier is active, the agent enforces the strictest possible linting and formatting standards. No warnings, no suppressions, no exceptions.

## Rules

1. **Zero tolerance for warnings.** Every linting warning is treated as an error. The code a change adds or modifies must pass all linting rules with zero warnings before a commit is accepted.
2. **No suppression comments.** `// eslint-disable`, `# noqa`, `@SuppressWarnings`, `// noinspection`, and any equivalent suppression directives are strictly forbidden. Fix the code, don't silence the linter.
3. **Strictest configuration.** If a linter supports strict mode (e.g., `"strict": true` in tsconfig, `--strict` in mypy, `"extends": ["eslint:recommended", "plugin:@typescript-eslint/strict"]`), it must be enabled.
4. **Auto-fix first.** Before manual edits, run the linter's auto-fix command on the files the change touches (`eslint --fix <files>`, `prettier --write <files>`, `black <files>`, `gofmt -w <files>`), never across the whole repository. Only manually fix what the auto-fixer cannot.
5. **Format on save.** Every file the change touches must be formatted according to the project's formatter (Prettier, Black, gofmt, spotless) before committing. No formatting drift.
6. **Type strictness.** `any`, `unknown` casts, and type assertions (`as`) are forbidden unless explicitly justified with a comment explaining why the type system cannot express the constraint.

## Behavioral Overrides

- Before committing any code change, the agent MUST run the full linting suite and verify the change introduces zero warnings/errors.
- If a linting rule conflicts with functionality, the agent must find a way to satisfy both — never disable the rule.
- When modifying existing code that has pre-existing lint violations, the agent fixes the violations on the lines its change already touches and reports the rest instead of fixing them.
