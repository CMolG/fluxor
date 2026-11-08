---
name: topology
description: Derives a JS/TS workspace's real package graph (pnpm, npm, yarn or bun workspaces) from package.json files and the imports that really exist in the code, and checks it - no cycles, no phantom dependencies, plus the project's own layering rules (forbidden edges between package groups, isolated groups, leaf groups, exceptions with a reason) declared as data. Its `route` command maps domain vocabulary to bounded contexts (Maven reactor modules or TypeScript packages) so the agent can route a concept instead of grepping for it. Use it before asserting how packages relate, before adding a workspace dependency, when a README, ADR or plan describes the architecture and you are about to act on it, when deciding where a new concept belongs, and when closing out work that touched package.json files or cross-package imports.
---

# Real workspace topology

Architecture rules usually live in prose: a rules file, an ADR, a README. **A document is not
evidence.** A README can say "the desktop shell mounts each app in an iframe" while someone has just
imported one app's component inside the shell. It compiles, it runs, it looks fine, and nobody finds
out until that app has to be deployed on its own and can't.

This skill reads no document. It builds the graph from two sources that can't lie, the
workspace's `package.json` files and the imports that really exist in the code, and checks the
invariants against it. The generic invariants always run. The project's own layering rules are
**data** in `.harness/config/topology.json`, so the rules the prose describes become a check that
fails.

## How it's used

Paths are relative to this skill's directory; run from anywhere inside the project.

```bash
python3 topology.py map            # the whole graph, one or two lines per package
python3 topology.py verify         # exit 0 if clean, 1 if there are violations (the default command)
python3 topology.py graph          # the graph as JSON: {name: {dir, deps, groups?}}, for other tools
python3 topology.py route          # bounded contexts -> their domain vocabulary
python3 topology.py route wallet   # ...and where a concept lives
python3 tests/run_tests.py         # the skill's own fixture tests
```

- **Project root:** `$CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel`, else the current
  directory. **Config:** `$HARNESS_DIR/config/topology.json`, else
  `<root>/.harness/config/topology.json`. Both are optional.
- **Workspace packages** come from the `workspaces` config key if set, else `pnpm-workspace.yaml`,
  else the `workspaces` field of the root `package.json` (array or `{ "packages": [...] }`). With
  none of them, a root `package.json` with a `name` is checked as a single package. With no JS at all,
  `map`/`verify` say so and exit 0, and `route` may still work.
- **Imports** come from one `git grep` over versioned and untracked-but-not-ignored sources, so
  `node_modules`, build output and anything `.gitignore`d is skipped for free. It takes a fraction
  of a second on a repository with dozens of packages. Without git (not a repository, git missing
  or refusing the directory) it falls back to walking the package directories, which is slower
  but reports the same thing.
- **It writes nothing.** No cache, no index, no file in the tree.

## What it checks, and why

Always on, with no config:

1. **No cycles between workspace packages.** This is the one rule that depends on no decision of
   the project: a cycle breaks a cold build and makes it impossible to extract a piece.
2. **No phantom dependency**: something imported in a package's code that isn't declared in *that
   package's* `package.json` (`dependencies`, `devDependencies`, `peerDependencies` or
   `optionalDependencies`). With pnpm or npm hoisting it works by accident, through the root
   `node_modules`, and it breaks the day the package is installed, built or deployed on its own.
   Worse, it turns the declared graph into a lie, and preventing that is the reason this skill
   exists. These are not phantoms:
   - relative and absolute paths, `#subpath` imports, and scheme specifiers (`node:fs`,
     `virtual:x`, `bun:test`);
   - Node built-ins (`fs`, `path/posix`, ...);
   - self-imports (a package importing its own name);
   - `tsconfig`/`jsconfig` `paths` aliases (`@/*`, `shared/*`, ...), following `extends`, and
     folders under `baseUrl`;
   - `import type` of a package whose `@types/...` is declared;
   - dependencies declared in the root `package.json`, unless `phantoms.rootDependencies` is
     `false`.

   A workspace package is always an edge of the graph and must always be declared, even if a
   `paths` alias makes it compile without the declaration.

From config (see [Configuration](#configuration)), each one a list of offending edges:

3. **Forbidden edges between groups**: `{"from": "host", "to": "miniapp"}`. For example: apps are
   mounted by the shell at runtime, so an import puts one app inside the shell's bundle. That is
   exactly the coupling the architecture ruled out, and the symptom is that there is no symptom.
4. **Isolated groups**: no member may depend on another member. For example: each app deploys on
   its own, and an app-to-app import turns two apps into one that no longer deploys separately.
5. **Leaf groups**: members may depend only on their own group (plus `mayDependOn`). For example: a
   design system consumed by the whole ecosystem. If it imports one of its consumers, it inverts
   the dependency and can no longer be extracted.

**Every exception needs its reason written down.** An exception or a phantom ignore without a
`reason` is itself a violation, and it does not apply until it has one. Without a reason nobody can
tell a decision from an accident. An exception that no longer excuses anything is reported as a
note, because a stale exception is a hole waiting for the next edge. When this skill was ported
from the monorepo it was written for, that note found that the original's only two hard-coded
exceptions had never excused anything: no rule constrained the package they were written for.

Config mistakes (invalid JSON, unknown keys, a rule naming a group that doesn't exist) are reported
as violations too. A typo that silently switches a rule off is worse than a loud error.

## Configuration

`.harness/config/topology.json`. Every key is optional; with no file only the generic checks run.
`config.schema.json` in this skill is the file's JSON Schema and `config.example.json` is the
example below. The only `$` key accepted is a top-level `$schema` (for editors); a `$comment` is
an unknown key like any other.
Globs: `*` stays within one path segment, `**` crosses segments. Wherever a glob selects
**packages**, it is matched against both the package **name** and its **directory** (relative to
the root), so `"@acme/app-*"` and `"apps/*"` both work.

| Key | Default | Meaning |
| --- | --- | --- |
| `workspaces` | autodetected | Package directory globs, used instead of `pnpm-workspace.yaml` / `package.json` `workspaces`. `!glob` excludes. |
| `extensions` | `.ts .tsx .js .jsx .mjs .cjs .mts .cts` | Source files scanned for imports. |
| `exclude` | `[]` | Path globs whose files are not scanned (e.g. `"**/examples/**"`). |
| `phantoms.scope` | `"all"` | `"all"`: every bare import must be declared. `"workspace"`: only imports of workspace packages. `"off"`: no phantom check. |
| `phantoms.rootDependencies` | `true` | Dependencies declared in the root `package.json` count as declared for every package. |
| `phantoms.ignore` | `[]` | `{"import": <glob on package name or specifier>, "in": <package glob, optional>, "reason": <required>}`. |
| `groups` | `{}` | `{<group>: {"packages": [<package globs>], "isolated": false, "leaf": false, "mayDependOn": [<groups>], "reason": <optional, printed with violations>}}`. A package may belong to several groups. |
| `forbidden` | `[]` | `{"from": <group>, "to": <group>, "reason": <printed with violations>}`. |
| `exceptions` | `[]` | `{"from": <package glob>, "to": <package glob>, "reason": <required>}`. Excuses an edge from forbidden/isolated/leaf rules. Never excuses cycles or phantoms. |
| `route.maven` | autodetected | `false` switches Maven routing off. Otherwise an object with the keys below (`true` is the same as leaving it out). |
| `route.maven.root` | root `pom.xml`, else the top-level `pom.xml` files found | Reactor root directory (or a list of them). Modules are read recursively from `<module>` entries. |
| `route.maven.contexts` | none | Directory glob(s), one directory per bounded context (e.g. `"backend/contexts/*"`). Without it, each module whose directory ends in `domainSuffix` is a context, with its sibling `<ctx>-*` modules as layers. |
| `route.maven.domainSuffix` | `"-domain"` | Marks the module whose types are the context's vocabulary. |
| `route.maven.expectedLayers` | `[]` | e.g. `["domain", "application", "infrastructure"]`. Contexts missing one are flagged in `route`. |
| `route.maven.excludeTypePaths` | `[]` | Path globs of type files left out of the vocabulary (e.g. `"**/ports/**"`). |
| `route.packages` | `[]` | Package globs whose exported `class`/`interface`/`type`/`enum` names form a vocabulary (TypeScript routing). Test and story files are skipped. |
| `route.patternSuffixes` | `Repository, Service, Resource, Mapper, Client, ...` | Suffixes that name a pattern, not a concept; they sort last in the vocabulary. |
| `route.note` | none | One line printed after `route` output (e.g. where the pattern catalog lives). |

### Complete example

Illustrative only. This is the rule set of a real monorepo with the names changed: a desktop shell
that mounts independently deployed apps in iframes, a design system, a marketing site that
showcases apps, and a Maven backend organized in bounded contexts.

```json
{
  "workspaces": ["shell", "site", "packages/*", "packages/apps/*"],
  "exclude": ["**/examples/**"],
  "phantoms": {
    "scope": "all",
    "rootDependencies": true,
    "ignore": [
      { "import": "server-only", "in": "packages/apps/*",
        "reason": "Provided by the framework's bundler; it is never installed." }
    ]
  },
  "groups": {
    "shell": { "packages": ["shell"] },
    "app": {
      "packages": ["packages/apps/*"],
      "isolated": true,
      "reason": "Each app deploys on its own under its base path; shared code goes to packages/*."
    },
    "design-system": {
      "packages": ["@acme/ui", "@acme/brand"],
      "leaf": true,
      "reason": "Consumed by the whole ecosystem: it may only depend on itself."
    }
  },
  "forbidden": [
    { "from": "shell", "to": "app",
      "reason": "Apps are mounted by same-domain iframe, not by import (see the architecture ADR)." }
  ],
  "exceptions": [
    { "from": "site", "to": "packages/apps/player",
      "reason": "The site's showcase renders the app's real leaf components, not a mockup." }
  ],
  "route": {
    "maven": {
      "root": "backend",
      "contexts": "backend/contexts/*",
      "domainSuffix": "-domain",
      "expectedLayers": ["domain", "application", "infrastructure"],
      "excludeTypePaths": ["**/ports/**"]
    },
    "packages": ["packages/sdk"],
    "note": "What goes in each layer is fixed by the project's pattern catalog."
  }
}
```

The exception above only has an effect if a rule forbids `site -> app`. If none does, `verify` notes
that the exception is stale.

## `route`: the part that attacks slowness

`map` and `verify` check. `route` **routes**, which is a different problem. An agent is rarely slow
for lack of capability. It is slow because it **rediscovers the architecture on every task**. A
senior developer doesn't search; they know "this goes in billing" before opening the editor.

`route` prints, for each bounded context, the domain vocabulary it really has (say, `billing` is
`Wallet`/`Budget`/`LedgerEntry` and `iam` is `ApiKey`/`Organization`/`Role`). Given a term, it
answers directly where the term lives. This replaces the exploratory `grep`, which over a thousand
Java files is guessing.

- **Maven:** the contexts come from the reactor (`<module>` entries, recursively). The vocabulary is
  the type names in each context's domain module (`<ctx>-domain` by default). With a term, the
  domain types are searched first. Only if nothing matches are the other modules of the context
  searched, because a concept can be an **operation** with no type of its own. In the original
  project, "unsubscribe" answered "does not appear" while an `...UnsubscribeService` sat in the
  application layer, which is the exact invitation to build it twice.
- **TypeScript:** each package in `route.packages` is a context, and its exported type names are
  the vocabulary.
- **Nothing configured or detected:** `route` says so and prints the config to add.

The term is matched **word by word**, not as a phrase, because no type is named after a sentence.
Matching the full string once made a four-word query answer "does not appear" with the right
context sitting there, whole, and that is worse than no answer because it invites creating what
already exists. The search also doesn't translate: type names are in the language of the code, so
search in that language before concluding something doesn't exist.

**It reads no document and versions nothing.** A stale index is worse than no index, because the
agent believes it. This one can't go stale because it doesn't exist between two calls.

What **is** a heuristic, stated as one: the vocabulary's ordering assumes an aggregate has a short
name with no pattern suffix (`Wallet` before `JdbcWalletRepository`). If the concept you want
doesn't show up in the map, use the form with a term, which looks at every type.

## Limits, stated plainly

- Imports are found by pattern (`from '...'`, `import '...'`, `import(...)`, `require(...)`,
  `require.resolve(...)`, `vi.mock`/`jest.mock` and friends), not by a parser. Commented-out lines
  are skipped. A string literal that happens to read `from 'x'` would count as an import.
- Aliases defined only in a bundler config (`vite`, `webpack`), and modules a framework provides
  without installing them, are not visible to it. Declare them with `phantoms.ignore` and a reason.
- The graph's edges are the union of declared workspace dependencies and imported workspace
  packages. A declared but unused workspace dependency is still an edge, as it is for the package
  manager.

## Tested, including failing

`tests/run_tests.py` builds three synthetic workspaces (git-initialized) in a temporary directory
and runs every command against them:

- a clean pnpm workspace full of legal-but-tricky imports (alias, `baseUrl`, built-ins,
  self-import, type-only, a root dependency, a commented-out import, `Buffer.from('...')`) that must
  pass;
- a broken npm workspace with a cycle, workspace and external phantoms, a forbidden edge, an
  isolated-group edge, a leaf edge, an exception with and without a reason, an ignore without a
  reason and a config typo, where each one must fire, with and without git;
- a Maven reactor where `route` must autodetect the contexts, find terms, fall back to operations,
  and add TypeScript packages from a config passed through `HARNESS_DIR`.

`--keep DIR` leaves the fixtures in place. A validator that has only ever been seen passing hasn't
been tested: each assertion was also checked to fail when the code it covers is disabled.

## What this is NOT

It is not a knowledge map or a code index. A versioned map of the code was evaluated and rejected
in the project this came from. It went stale, and the agent believed it. The conclusion was that a
map has a place only **outside the tree**, **generated on demand** and built from **real domain
units** rather than inferred abstractions. This is exactly that: its units are the packages and
modules the project already has, it is computed on the fly, and it is discarded. If anyone proposes
versioning its output, that is the argument against it.
