---
name: reduction
description: Runs a code-reduction campaign over a Java and/or React/TypeScript codebase with the P0 protocol (measure first, apply only after explicit approval) and 21 techniques. J1-J10 cover Java, R1-R6 cover React, and T1-T5 are cross-cutting. Use it when the user asks to reduce, shrink, deduplicate, simplify or clean up code at scale, when they name a technique by its id ("apply J1", "run T2"), when they ask how many lines a refactor would save, or when a batch is about to touch the same shape in many files at once. Also use it to read the state of the campaign: which techniques were analyzed, what the verdict was, and what is still pending.
---

# Code reduction: the P0 protocol

A campaign to remove volume from a codebase. **It is a refactor, never a behavior change**, and it
runs in two phases with an approval gate between them. The expensive failure here is not writing
one bad abstraction. It is writing thirty of them before anyone sees a number.

**The sentence that governs it:** fewer lines is not the goal. **Less to discover is the goal.**
A technique that removes lines but forces the agent to open more files to understand one unit is
a loss. It gets marked `DISCARD` no matter how good the percentage looks.

In this document `reduction.py` means the script in this skill's directory (in a project with a
harness, usually `.harness/skills/reduction/reduction.py`). Run it with `python3`, from anywhere
inside the project.

## Start here: what the project already knows

```bash
python3 reduction.py config     # project root, analysis dir, source roots, UI package, decisions
python3 reduction.py list       # the 21 techniques and the state of each one
```

`config` shows every project fact the skill will use and where it came from (`config`,
`autodetected` or `default`). If a source root is wrong or missing, fix it in the config file
before measuring anything. A surface measured over the wrong roots is a wrong number with a
command behind it, which is worse than no number.

### Decisions the project has already made

A generic checklist cannot know this part. **Some techniques are already decided by the
project**, and running an analysis on them is not diligence. It reopens a closed decision. Before
analyzing a technique, look for what the project has already written down, in this order:

1. The `decided` key of the config (see below). `list` prints these, and `new` refuses to open
   an analysis for them without `--force`, which you pass only when the user explicitly asks.
2. If the project has a harness: `PREFERRED_TECHNOLOGIES.csv` (a `FORBIDDEN` library kills the
   technique that needs it), `adr/`, `INVARIANTS.md`, and any pattern catalog in `contracts/`.
3. The build itself: the dependencies already present, and architecture tests (ArchUnit or
   similar) that encode boundaries.

When you find a decision that is not in `decided` yet, propose adding it, with its source.

Typical shapes, for illustration only:

- **J3 `DISCARD`** when the project's persistence is plain JDBC and every ORM is forbidden: a
  generic repository with derived queries needs exactly that ORM.
- **J7 `PARTIAL`** when a compile-time mapping generator is forbidden (for example, because a new
  dependency for a dozen mappers did not pay for itself): only "delete the 1:1 mapper" survives.
- **J2 restricted** when the domain's ports are single-implementation *by design* (hexagonal
  architecture): J2 never touches those, because the architecture tests rest on them.
- **J9 already a rule** when the testing guideline already says "parametrize when cases differ
  only in data": J9 applies it, it does not re-decide it.
- **T3 closed** when the project already derives its map from code (for example, with the
  `topology` skill): no hand-written tree file gets created.
- **T5 mostly closed** when bounded contexts are already build modules: the compiler enforces
  the boundaries, and only the declared gaps are left.

## Configuration

Project facts live in `.harness/config/reduction.json` (under `$HARNESS_DIR/config/` when that
variable is set). **The file is optional**: every key has a default or is autodetected, and a
key you leave out keeps its default. Paths are relative to the project root.

The project root is `$CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel`, else the current
directory. The harness is `$HARNESS_DIR`, else `<root>/.harness`.

| Key | Type | Default when absent |
| --- | --- | --- |
| `analysisDir` | path | `<harness>/analysis`. If the project has no harness, `new` creates `.harness/analysis/` and says so; set this key to put the analyses elsewhere (for example `docs/reduction`). |
| `sources.java` | list of paths | Autodetected: every Maven (`pom.xml`) or Gradle (`build.gradle`, `build.gradle.kts`) module that has `src/main/java`. Only `*.java` files under these roots are measured. |
| `sources.react` | list of paths | Autodetected: every directory with a `package.json` that depends on `react`, `react-dom`, `next`, `typescript` or `@types/react`, or that has a `tsconfig.json`. Workspace roots (a `workspaces` field, `pnpm-workspace.yaml` or `lerna.json`) are skipped because their members are detected on their own. Files measured: `.ts .tsx .js .jsx .mjs .cjs`. |
| `uiPackage` | string or `null` | Autodetected when exactly one detected project's `package.json` name ends in `ui`, `design-system` or `components` (for example `@acme/ui`). Otherwise none, and R3/R4 treat "the shared UI package" as something to propose rather than use. |
| `exclude` | list of globs | Build output, dependencies, generated and vendored code: `**/node_modules/**`, `**/target/**`, `**/build/**`, `**/dist/**`, `**/out/**`, `**/.next/**`, `**/.nuxt/**`, `**/.turbo/**`, `**/.gradle/**`, `**/coverage/**`, `**/generated/**`, `**/generated-sources/**`, `**/__generated__/**`, `**/vendor/**`, `**/third_party/**`, `**/.git/**`, `**/.harness/**`, `**/.claude/**`, `**/*.min.js`, `**/*.d.ts`. Hidden directories are always skipped. **Setting the key replaces the whole list**, so copy the defaults you want to keep. |
| `tests` | list of globs | `**/src/test/**`, `**/src/testFixtures/**`, `**/src/it/**`, `**/__tests__/**`, `**/test/**`, `**/tests/**`, `**/e2e/**`, `**/*.test.*`, `**/*.spec.*`, `**/*Test.java`, `**/*Tests.java`, `**/*IT.java`. Test files never count toward the saving, so `surface` leaves them out unless you pass `--tests`. Setting the key replaces the list. |
| `decided` | object: technique id to reason | `{}`. Decisions the project already carries (see above). |
| `verify` | object: name to command | Autodetected: `./mvnw -q -pl <module> -am test` (or `mvn`) when there is a root `pom.xml`, `./gradlew :<module>:test` when there is a `gradlew`, and `<pnpm/yarn/npm> test` when the root `package.json` has a `test` script. These are the commands phase 2 runs after every batch. |

Globs are matched against the path relative to the project root, prefixed with `./`, so
`**/generated/**` also matches a top-level `generated/`. A `$`-prefixed key (for example
`"$comment"`) is ignored; any other unknown top-level key is reported, because it is almost
always a typo. Inside `sources`, only `java` and `react` are read. `config.schema.json` in this
skill is the file's JSON Schema (stricter: it also rejects unknown keys inside `sources`) and
`config.example.json` is the example below.

A complete example:

```json
{
  "$comment": "Project facts for the reduction skill. Every key is optional.",
  "analysisDir": ".harness/analysis",
  "sources": {
    "java": ["server"],
    "react": ["web/landing", "web/dashboard", "packages/ui"]
  },
  "uiPackage": "@acme/ui",
  "exclude": [
    "**/node_modules/**", "**/target/**", "**/dist/**", "**/.next/**",
    "**/generated/**", "**/generated-sources/**", "**/vendor/**", "**/*.d.ts"
  ],
  "tests": ["**/src/test/**", "**/__tests__/**", "**/*.test.*", "**/*.spec.*"],
  "decided": {
    "J3": "DISCARD: persistence is JDBC over DataSource; every ORM is FORBIDDEN (ADR 0004)",
    "J7": "PARTIAL: the mapping generator is FORBIDDEN; only deleting 1:1 mappers survives"
  },
  "verify": {
    "java": "cd server && ./mvnw -q -pl <module> -am test",
    "react": "pnpm -r test",
    "architecture": "cd server && ./mvnw -q -pl app -Parchitecture test"
  }
}
```

`check` fails on an invalid config (bad JSON, wrong types, unknown keys, a source root that is
not a directory, an unknown technique id in `decided`). The other commands warn and continue with
the defaults.

## P0: the protocol

### Phase 1: analysis. No code gets modified.

1. **Route before searching.** Find the module or project first, then search inside it. A blind
   `grep` over the whole tree as the first tool is a bet, not a method.
   `python3 reduction.py route [args]` runs the `topology` skill (`map` by default) when it is
   installed next to this one. Without it, `route` prints the configured source roots, which is
   still a better starting point than the whole tree.
2. **Measure the surface**: files, occurrences, LOC affected. Real numbers from real commands,
   pasted into the analysis file. `python3 reduction.py surface '<regex>' --lang java|react|all`
   prints the `Surface:` and `Top 10 files by impact:` lines over the configured roots, with
   exclusions and tests applied, and states its method. A regex is not a compiler: when the
   technique needs exactness (for example, "interfaces with exactly one implementation"), use a
   stronger method and **say which method you used**. An estimate with no command behind it is
   an opinion.
3. **Estimate the two axes.** Not only LOC before and after with the percentage, but also
   **context per unit**: how many files you must open to understand one change, before and
   after. The second number is the one that decides the verdict.
4. If the technique is ambiguous, read the official documentation **for the exact version the
   project uses**. Take the version from the build files, lockfiles or the harness's
   `PREFERRED_TECHNOLOGIES.csv` if it has one, not from memory. Cite the sources.
5. Write the result with the template below. `python3 reduction.py new <id>` writes the skeleton
   with the right frontmatter into the analysis directory. **If the file already exists, update
   it. Never duplicate it.**
6. **Stop here.** Nothing is applied until the user explicitly approves that technique.

### Phase 2: application. Only after approval.

7. **Small batches, one commit per batch, green at every commit.** A 300-file refactor in one
   commit cannot be reviewed or bisected.
8. **Zero behavior changes.** If a test has to change to make the refactor pass, stop: either it
   was not a refactor, or the test was checking the thing you just broke. Say so out loud instead
   of adjusting the test.
9. **Verify with what the project has**: the `verify` commands from `config`, per module where the
   build supports it, and a full run before the pull request. With Maven, keep `-am` (also-make):
   without it the module is tested against stale installed artifacts of its siblings, so a green
   run proves nothing. If the project has architecture
   tests, they are the only automatic proof that a boundary survived a refactor that moved code
   between layers. If the batch touched `package.json` files or imports between packages and the
   `topology` skill is installed, run `python3 reduction.py route verify`.
10. **Record the real figure.** Fill the `Real LOC:` line with the real LOC against the estimate.
    A campaign whose estimates are never checked against reality produces better and better
    estimates of nothing.

> **Mutation testing.** If the project has it, run it on the modules a batch touched: it is the
> guard against a refactor that silently weakens the suite. If it does not, **do not pretend it
> was checked**. Adding it is a new dependency, so stop and ask the user with two or three
> options and their trade-offs. Until then, the guard is step 8 plus a review of the diff, and
> the report says that plainly.

## Hard rules

- **Indirection is only worth it at scale, and the denominator is the system, not the file.** An
  abstraction breaks even only when the lines it removes across all its call sites exceed what
  it costs: its own lines plus one more file every reader must open. Collapse what *changes for
  the same reason*, not what merely *looks alike*.
- **Do not write contamination while reducing**: a wrapper that only re-exports, a comment that
  repeats the line below it, `any` / `@ts-ignore` / an empty `catch {}`, dead code kept "just in
  case". If the project has written rules about this, they take precedence.
- **No reflection, no dynamic code generation, no inheritance deeper than one level.** For
  example, in a project that compiles to a native image, reflection-based deserialization needs
  explicit registration, so a "clever" reduction through reflection breaks the build as well as
  readability.
- **Names stay self-describing.** If a generic or an abstraction needs a comment to be
  understood, it did not pay for itself.
- **No new conventions.** If the project has a pattern catalog or a chosen architectural line, a
  reduction that introduces a new shape is not a reduction. It is a second way to do the same
  job, and it costs every future batch the work of figuring out which one it is in.
- **A new dependency is a decision for the user.** Present two or three options with their
  trade-offs, and record the choice where the project records technology decisions.
- **Counting is honest.** Tests do not count toward the saving (otherwise the shortest path to
  "fewer lines" is deleting them), and lines are counted **after** formatting, or "reducing"
  degenerates into cramming ternaries together.

## The analysis file

One file per technique in the analysis directory, named `<id>-<slug>.md`, and it is the only
artifact phase 1 produces. Ceiling: **60 non-blank lines**. The point is the figures, not the
prose; the reasoning belongs in the commit or in the technique file.

```
---
technique: <id> — <name>
scope: java | react | transversal
date: <YYYY-MM-DD>
verdict: APPLY | PARTIAL | DISCARD
---
Surface: <n files>, <n occurrences>, <n LOC>
Estimated saving: <LOC before> -> <LOC after> (<%>)
Context per unit: <n files before> -> <n files after>
Self-description risk: low | medium | high — <one line>
Migration cost: <batches>
Top 10 files by impact: <list>
Blockers: <list or none>
Sources consulted: <urls>

Real LOC: <filled in after phase 2, never before>
```

`verdict` is the load-bearing field. `new` writes `PENDING`, which authorizes nothing. Only
`APPLY` and `PARTIAL` authorize phase 2, and only after the user says so. **`DISCARD` is a
result, not a failure**: a technique measured and rejected with its reason is worth more than one
nobody ever ran, because it stops being proposed again every few months.

`check` is the executable half of this contract. It fails on: a file with no frontmatter, an
unknown technique id, two files for the same technique, a missing frontmatter field, a `scope`
that does not match the technique, a verdict outside the enum, a final verdict with the template
placeholders untouched, and a file over the line ceiling. It reports, without failing, a
`PENDING` file and the case that actually happens: an `APPLY` or `PARTIAL` whose `Real LOC:` line
was never filled in after phase 2. A `README.md` in the directory is ignored.

## The CLI

```bash
python3 reduction.py config                  # resolved project facts and where each came from
python3 reduction.py list                    # the 21 techniques, their verdicts and decisions
python3 reduction.py new J1 [--force]        # analysis skeleton with the right frontmatter
python3 reduction.py check                   # 0 if config and analyses are well-formed, 1 if not
python3 reduction.py surface '<regex>' [--lang java|react|all] [--tests]
python3 reduction.py route [topology args]   # delegates to the topology skill when installed
```

The script needs only the Python 3.9+ standard library. It writes only inside the analysis
directory and never touches source code: applying a technique is the agent's job, under the
approval gate, and a script that could do it on its own would be a way around that gate.

## The techniques

Open them one at a time, never all at once. Each file says what to detect, what to replace it
with, and what it must not touch.

| File | Techniques |
| --- | --- |
| `techniques/java.md` | J1 records/sealed · J2 single-impl interfaces · J3 generic persistence · J4 central exception mapping · J5 declarative validation · J6 strategy registry · J7 mapping layer · J8 interceptors · J9 parametrized tests · J10 home-grown utilities |
| `techniques/react.md` | R1 generated API client · R2 schema-driven forms · R3 shared design system · R4 variants over clones · R5 declarative tables · R6 single fetching layer |
| `techniques/transversal.md` | T1 schema-first contract · T2 dead code · T3 predictable location · T4 enforced conventions · T5 domain modularization |

A project with only one stack skips the other catalog: J1-J10 need `sources.java`, and R1-R6 need
`sources.react`.

## The order

**First, one pass of analysis only, over everything that applies**, so the decisions are made
against figures instead of against whichever technique came to mind. Then application, in this
order:

1. **T2**: delete before refactoring. Never migrate code that is about to die.
2. **T3, T4**: zero lines saved, immediate effect on how fast the agent finds things.
3. **T1**: cuts the duplication between stacks at the root.
4. **J1, J2, J4, J5**: high volume, low risk.
5. **R1, R2, R6**: the bulk of the frontend.
6. **J6, J7, J9, J10, R3, R4, R5**: second wave.
7. **T5**: usually the residue only; modularization is expensive and often partly done already.
8. **J8**: last, and only if the analysis confirms it does not raise context per unit.

Anything in `decided` as `DISCARD` drops out of the order.

## What never gets applied

JSON-configuration-driven UI, metaprogramming, deep inheritance, and generic abstractions built
for a second use case that does not exist yet. They all reduce lines and blow up context: the
agent can no longer read one unit and understand it, which is the entire thing this campaign
optimizes for.
