# verbose-comments: Comprehensive Code Commentary Modifier

When this modifier is active, the agent must provide detailed explanatory comments for every significant block of logic, function, and complex variable. The code should be self-documenting through extensive inline commentary.

## Rules

1. **Function documentation.** Every function must have a doc comment (JSDoc, TSDoc, docstring) explaining:
   - What the function does (purpose, not implementation).
   - Each parameter's type, meaning, and valid range.
   - The return value's type and meaning.
   - Any side effects (state mutations, I/O, exceptions).
   - Usage example for non-trivial functions.
2. **Block comments for logic.** Every logical block (conditionals, loops, try/catch, state transitions) must be preceded by a comment explaining WHY this logic exists, not WHAT it does syntactically.
3. **Complex expressions.** Any expression involving bitwise operations, regex patterns, mathematical formulas, or ternary chains must have an inline comment explaining the intent in plain language.
4. **Constants and magic numbers.** Every constant, configuration value, or magic number must have a comment explaining its origin and meaning (e.g., `// 48px = Material Design minimum touch target size`).
5. **Type annotations.** Complex type definitions (generics, discriminated unions, mapped types) must include a comment explaining what the type represents in domain terms.
6. **Follow-ups go in the report, not in stub markers.** Known limitations, technical debt, and future improvements are listed in the response with their location, reason, and context. A comment may explain a limitation that is a lasting property of the code (e.g., `// Assumes UTC input; callers convert first.`), but code never carries stub markers (`TODO`, `FIXME`, `XXX`, `HACK`, "placeholder", "not implemented", "coming soon"), which stub guards reject.

## Behavioral Overrides

- The agent adds missing comments to existing code only on the lines its change already touches and reports the rest instead of commenting it.
- Comments must be written in clear, professional English. No abbreviations, no slang, no single-word comments.
- If a comment would just restate the code (`// increment i` for `i++`), skip it. Comments explain WHY, not WHAT.
