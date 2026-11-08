---
name: review-harness
description: Checks that a project's .harness/ agent harness is still wired and free of lies - the .claude/ (and .agents/) bridge, hook scripts and their test benches, the AGENTS.md -> INDEX.md -> rules load chain, pointer files with no body, broken backticked links, AI docs outside the harness, skill frontmatter and the market copy. Use it after adding, moving or renaming anything inside .harness/, after touching AGENTS.md, CLAUDE.md, .claude/settings.json or .gitignore, when an agent does not seem to receive a rule, skill or hook, and before closing a batch that moved documentation.
---

# Checking the harness

A harness fails silently. If the `.claude/skills` symlink is lost, if a new rule is never imported
from `INDEX.md`, or if a `git mv` leaves twenty links pointing at the old path, everything still
looks correct: the files are there, the build is green, and simply no agent receives the rule.
This skill turns that silent failure into a non-zero exit code.

It assumes the layout in `.harness/contracts/harness-convention.md` of Fluxor's market (`.harness/` at the
project root, `AGENTS.md` importing `.harness/INDEX.md`, the bridge, the hook split).

## How it's used

```bash
.harness/skills/review-harness/review.sh            # full report
.harness/skills/review-harness/review.sh --quiet    # only WARN and FAILS lines
.harness/skills/review-harness/review.sh --root DIR # review another checkout
```

- **Project root:** `--root`, else `$CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel`, else
  the current directory. **Harness:** `$HARNESS_DIR`, else `<root>/.harness`.
- **Exit 0** when nothing is broken (warnings allowed), **exit 1** when at least one line says
  `FAILS`. A hook can call it and grep `FAILS` lines to show the agent what broke.
- **Read-only.** It never writes, never runs a hook, never touches the network. It does not run the
  hook test benches either: some hooks act on git state, and a reviewer must be safe to run
  anywhere. Run the bench itself (for example `.harness/hooks/test-hooks.sh`) after touching a hook.
- `review.sh` is the stable entry point; the checks live in `review.py` (Python 3.8+, standard
  library only). Python because the checks need real JSON parsing (settings, config, inventory),
  symlink resolution and path arithmetic that shell greps got subtly wrong. **Without `python3` it
  fails open**, like every harness hook: it prints a `WARN` saying the review did not run and exits
  0, so a missing interpreter never blocks a session.

Output lines are `ok`, `info`, `WARN` (an optional piece is missing, or something will rot) and
`FAILS` (something is broken now). Only `FAILS` changes the exit code.

## What it checks, and why each one

1. **The bridge.** Runtimes discover skills and hooks only in their own directories, so living in
   `.harness/` is not enough. Per provider (autodetected, or set in the config):
   - **Claude Code:** `.claude/skills` resolves to `.harness/skills` (a symlink or a junction; a
     plain directory is a `WARN` if complete and a `FAILS` naming the skills it lacks; a one-line text
     file holding the target means the repo was checked out with `core.symlinks=false`).
     `.claude/settings.json` exists, is valid JSON, and every `.harness/hooks/<file>` it runs (or
     `.harness/market/hooks/<file>`, a hook installed from the catalog) exists
     and is executable, locally and in the git index (a hook committed as `100644` works on the
     machine that wrote it and on no fresh clone). Commands without `"$CLAUDE_PROJECT_DIR"` are
     warned (a relative path breaks when the session's working directory moves; an absolute one is
     one machine's), and so are commands that run logic outside those two folders.
   - **Codex:** the skills directory (`.agents/skills` by default) resolves to `.harness/skills`, and
     the hooks file (`.codex/hooks.json` by default), if present, references existing hooks.
     `AGENTS.md` is Codex's native entry, so the load chain covers its rules.
   - **The hook split:** `UserPromptSubmit` (preparation), `PreToolUse` (invariants) and
     `PostToolUse`/`Stop` (closing cycles). A missing half is a `WARN` by default: the harness then
     protects only part of what it claims to. Set `requireHookSplit` to make it fail.
2. **The bridge is versioned.** `.gitignore` usually ignores `.claude/`; without explicit negations a
   fresh clone arrives with no skills and no hooks while `.harness/` looks complete. The proof is
   not reading `.gitignore` but asking git whether it has the files (`git ls-files
   --error-unmatch`). An ignored bridge file `FAILS` with the negation to add; an untracked one is a
   `WARN`. It also checks that `.harness/INDEX.md` itself is not ignored.
3. **The load chain.** The root `CLAUDE.md` reaches `AGENTS.md` (symlink or `@AGENTS.md`),
   `AGENTS.md` imports `@.harness/INDEX.md`, **every** `.harness/rules/*.md` is imported by the index
   unless its front matter says otherwise, `INVARIANTS.md` (if present) is imported too, and every
   `@` import resolves. A rule nobody imports is a rule that does not exist, so the other two kinds
   are checked for the path that does reach them: `load: scoped` (loaded by its `paths:`) needs its
   copy in `.claude/rules/` when Claude Code is a provider, and both `load: scoped` and
   `load: on-demand` must be named in the index as `rules/<file>`. Also warned: the index importing anything beyond
   `rules/*.md` and `INVARIANTS.md` (imports are transitive: one extra `@` rides in every session,
   forever), and a `rules/projects/*.md` that no subproject `AGENTS.md` imports.
4. **`AGENTS.md` / `CLAUDE.md` have no body.** Each one is a pointer: at most `pointerMaxLines`
   non-blank lines and at least one `@` import that resolves. When the body lives in
   `.harness/rules/`, a local copy goes stale the moment someone edits the original. For Claude
   Code, a subproject `AGENTS.md` needs a sibling `CLAUDE.md` (Claude Code reads `CLAUDE.md` in
   subdirectories, not `AGENTS.md`), and a subproject `CLAUDE.md` must import its sibling
   `AGENTS.md` so the two cannot drift apart. Copies inside generated directories (`target/`,
   `dist/`, `.next/`, `node_modules/`...) are skipped: a pointer packaged into a build artifact is
   not a second pointer anyone reads.
5. **Broken links.** Every backticked path in Markdown that starts with `.harness/` and does not
   exist. It is what breaks when a file is moved. Templates and patterns are skipped (`<name>`,
   `*`, `{...}`, `000X`, `XX-XX`, `...`), as is a layout folder written with its trailing slash
   (`.harness/plans/` names where plans go, even before the first one). Dated evidence
   (`plans/`, `reports/`, `audits/`) is not scanned by default: it names files as they were called
   the day it was written, and rewording a record to follow a rename is not what it is for.
6. **AI documentation outside the harness.** Plans, specs, decisions and reports written to *direct*
   the work belong in `.harness/`; what describes one piece and is read when opening it (README,
   CHANGELOG, a module's contract) stays next to the code. A `docs/` or `plans/` folder that agents
   keep writing into outside the harness grows unnoticed: in the project this skill comes from, one
   such folder reached two thousand files before anyone triaged it. Default patterns are
   conservative (`plans/`, `specs/`, `adr/`, `superpowers/`, `.tech_proposals/`) and only warn;
   `docs/` inside subprojects is checked only when `strayDocs.subprojectDocs` is on (a root `docs/`
   is often human documentation). Set `strayDocs.fail` once the check is green.
7. **Hook test benches.** A hook without cases rots: its first false positive gets it disabled by
   hand and it never comes back. Every wired hook needs a bench: a case file matching
   `hookBench.casePatterns` next to it (default `<hook-stem>.cases*.tsv`), a mention in the
   runner (default `test-hooks.sh`), or a test file matching `hookBench.testPatterns` (for a hook
   whose behavior is a script, such as a heartbeat or a lock, rather than a decision). By default a blocking (`PreToolUse`) hook without a bench
   `FAILS` and any other hook only warns (a `Stop` or `SessionStart` hook often has to be tested by
   hand). A script that has cases but is wired by no provider is warned as a dead guardrail.
8. **Skills.** Every entry in `.harness/skills/` has a `SKILL.md` whose frontmatter `name` matches
   its folder and whose `description` is not empty: the description is the only thing an agent
   reads when deciding whether to use it. Broken skill symlinks fail.
9. **Market copy** (only if `.harness/market/` exists). An atom is two things: its entry in
   `inventory.json` and its `.md`. With only one it does not exist (the engine drops an entry with
   no file; nobody sees a file with no entry) and nothing says so: that role is simply never
   chosen. Every inventory kind that has a folder is compared; `lexicon.json` must be valid JSON.
   - **9b. Installed copies** (only if `installCheck` is set). A harness installed from a catalog
     carries copies nobody may edit: an edit there is lost on the next install, and until then the
     copy and its source disagree. The review runs the installer's own read-only check and
     `FAILS` when it exits non-zero, with its first lines as the reason.
10. **Recorded friction** (only if `frictionLog` is set; never fails). If the project's hooks log
    every block as `date<TAB>hook<TAB>reason`, the review summarizes it by hook. A guardrail
    topping the list is either a rule nobody internalized or a false positive; both call for
    looking before touching the rule.

## Configuration: `.harness/config/review-harness.json`

Optional. Without it every check runs with the defaults below and providers are autodetected. An
unknown key is reported as a `WARN` (typo guard); an invalid file `FAILS`. Paths and globs are
relative to the project root; in globs `*` and `**` both cross `/`, a leading `**/` also matches at
the root, and a trailing `/**` also matches the folder itself. `config.schema.json` in this skill
is the file's JSON Schema (it rejects the unknown keys the review only warns about) and
`config.example.json` is the example below.

| Key | Default | Meaning |
| --- | --- | --- |
| `providers` | autodetect: `claude` if `.claude/` or `CLAUDE.md` exists, `codex` if `.codex/` or `.agents/` exists | Bridges to check (`claude`, `codex`; `null` or `[]` autodetects). Listing a provider makes its missing bridge a failure instead of a warning. |
| `requiredHooks` | `[]` | Hook file names (in `.harness/hooks/`) that must be wired by some provider. |
| `requireHookSplit` | `false` | `true` turns a missing half of the hook split into a failure. |
| `pointerMaxLines` | `12` | Maximum non-blank lines in an `AGENTS.md` / `CLAUDE.md`. |
| `ignore` | `[]` | Globs excluded from every file scan (pointers, links, stray docs). Generated folders are always skipped. |
| `links.exclude` | `[".harness/plans/**", ".harness/reports/**", ".harness/audits/**"]` | Markdown files whose links are not checked. |
| `links.allowMissing` | `[]` | Exact paths allowed not to exist (a file an ADR retired on purpose, still named by history). |
| `links.placeholders` | `["XX", "000X", "..."]` | Substrings that mark a template path. |
| `strayDocs.patterns` | `["**/plans/**", "**/specs/**", "**/adr/**", "**/superpowers/**", "**/.tech_proposals/**"]` | Markdown outside the harness matching these is stray AI documentation. Replaces the default list. |
| `strayDocs.subprojectDocs` | `false` | Also flag `<dir>/docs/**` for every directory that has its own `AGENTS.md`. |
| `strayDocs.allow` | `[]` | Globs exempted from the stray-docs check. |
| `strayDocs.fail` | `false` | `true` makes stray docs failures instead of warnings. |
| `hookBench.casePatterns` | `["{stem}.cases*.tsv"]` | Case files that count as a bench; `{stem}` is the hook name without extension, `{name}` with it. |
| `hookBench.testPatterns` | `[]` | Test files (globs from the project root) that count as a bench, e.g. `"scripts/test/{stem}.test.mjs"`. |
| `hookBench.runner` | `"test-hooks.sh"` | Bench runner in `.harness/hooks/`; a hook it names counts as covered. `null` or `""`: no runner. |
| `hookBench.require` | `"blocking"` | Which hooks fail without a bench: `"blocking"` (`PreToolUse`), `"all"` or `"none"`. The rest warn. |
| `hookBench.exempt` | `[]` | Hook names that need no bench (say why in the harness). |
| `codex.skillsDir` | `".agents/skills"` | Where Codex discovers repository skills. |
| `codex.hooksFile` | `".codex/hooks.json"` | Where Codex hooks are wired. |
| `frictionLog` | unset | Path of the blocks log (`$VARS` and `~` expand; an unset `$TMPDIR` falls back to the system temp folder), e.g. `"$TMPDIR/<project>-harness-friction.tsv"`. |
| `installCheck` | unset | Argv of the installer's read-only drift check, run from the project root (check 9b). |

A complete example (illustrative, for a monorepo with subprojects and a friction log):

```json
{
  "$comment": "Allowances for review-harness. Keys: see the skill's SKILL.md.",
  "providers": ["claude", "codex"],
  "requiredHooks": ["prepare-batch.sh", "bash-invariants.sh"],
  "requireHookSplit": true,
  "pointerMaxLines": 12,
  "ignore": ["research/**", "vendor-docs/**"],
  "links": {
    "exclude": [".harness/plans/**", ".harness/reports/**", ".harness/audits/**", "ONGOING.md"],
    "allowMissing": [".harness/skills/old-tool/old_tool.py"],
    "placeholders": ["XX", "000X", "..."]
  },
  "strayDocs": {
    "patterns": ["**/docs/**", "**/plans/**", "**/specs/**", "**/adr/**", "**/.backlog/**"],
    "subprojectDocs": true,
    "allow": ["docs/public/**"],
    "fail": true
  },
  "hookBench": {
    "casePatterns": ["{stem}.cases*.tsv"],
    "runner": "test-hooks.sh",
    "require": "blocking",
    "exempt": ["final-cycle.sh", "session-lock.sh"]
  },
  "codex": { "skillsDir": ".agents/skills", "hooksFile": ".codex/hooks.json" },
  "frictionLog": "$TMPDIR/my-project-harness-friction.tsv"
}
```

Keys starting with `$` are comments and are ignored.

## When it fails

Fix what it says and run it again. If what fails is the load chain (3) or a pointer with a body
(4), **do not close the batch**: there are written rules that no agent is receiving, which is
exactly the state the harness exists to prevent. A new check that starts red on an existing
project is a work item, not a reason to lower the bar: add the allowance to the config with a
`$comment` saying why, and remove it when the debt is paid.
