# docs-verified: Reader-First, Code-Verified Documentation Modifier

When this modifier is active, documentation says what the code does today, organized around what its reader needs to do. Every factual claim is traced to its source, and what could not be verified is marked.

## Rules

1. **One reader and one type per page.** Before writing, name the reader and the Diataxis type of each page (tutorial, how-to guide, reference or explanation). A page never mixes types; content for another need moves to its own page and is linked.
2. **Trace every claim to the code.** A flag, default, route, status code, limit or path is traced to a symbol, a config file, an API definition or a command's output. Another document is never the source.
3. **Run every example.** Each example is run against the version documented, and its output matches the page.
4. **Mark what could not be verified.** A claim or example that cannot be checked here (a secret, a paid service, missing hardware) is marked unverified, with the reason.
5. **The code wins.** When code and page disagree, the page is rewritten to match. Code that looks wrong becomes a bug card for its owner, never a page describing what it should do.
6. **Plain language.** Second person, present tense, active voice, one term per concept, in the project's terms and style guide first.
7. **Links and anchors resolve.** A page with a broken link or anchor is not done.

## Behavioral Overrides

- The agent finishes with a list of the claims checked, the examples run and what remains unverified.
- If the reader of a page is unclear, the agent asks the card's owner instead of guessing.
- Pre-existing pages that break these rules are fixed only where the change already touches them; the rest are reported.
