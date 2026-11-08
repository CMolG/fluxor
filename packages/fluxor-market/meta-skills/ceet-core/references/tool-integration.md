# Tool integration

> A CEET pack is portable Markdown plus JSON; each AI tool gets an **adapter** rendered from it. The
> portable pack stays the source of truth: edit the profile and re-render, never an adapter. Tool file
> formats change often; this page reflects the tools' documentation as of September 2026, so check a
> tool's own docs when something does not load.

## What loads when

| Load | Files | Why |
| --- | --- | --- |
| Always | `core.md` | How the person thinks, decides and speaks, and their best-evidenced rules, kept short: models follow fewer instructions reliably as their number grows, and drift from long system prompts. |
| With the task | one file of `agents/`, `skills/`, `commands/` or `rules/` | Each carries the directives of its own domain. |
| As demonstrations | the 3–5 closest entries of `examples/decisions.md` | Real decisions move a model toward a person more than prose does. |
| Never, for work | `cognitive-profile.md`, `private/` | The full clone is for people; `private/` is never loaded. |

## Rendering and installing adapters

```bash
python3 scripts/render_pack.py render <pack> --adapter claude-code --adapter cursor --write
python3 scripts/render_pack.py install <pack> --adapter claude-code          # dry run
python3 scripts/render_pack.py install <pack> --adapter claude-code --yes    # after approval
```

`install` copies the adapter's files to the same paths in the project, refuses to overwrite a file it
did not install (`--force` to replace), and records every file in `pack.json`, so
`render_pack.py erase` can remove them. Files named `*.section.md` and `settings.hooks.json` are
**merged by hand** into an existing file; `install` lists them.

| Adapter | Files (under `adapters/<tool>/`) | Notes |
| --- | --- | --- |
| `agents-md` | `AGENTS.section.md` | A section for the project's `AGENTS.md` (Codex, Cursor, Copilot, Gemini CLI, Devin and others read it): the core inline, pointers to the rest. In a project that follows the harness convention, import `core.md` from `.harness/INDEX.md` instead. |
| `agent-skills` | `<pack-id>-<skill>/SKILL.md` | One Agent Skill per file of `skills/`: spec-only front matter (`name` equal to the folder, ≤64 characters; `description` ≤1,024), CEET provenance in `metadata`. Works in every client of the open standard. |
| `claude-code` | `.claude/agents/<name>.md`, `.claude/commands/<name>.md`, `.claude/skills/<pack-id>-<name>/SKILL.md`, `CLAUDE.section.md`, `settings.hooks.json` | Subagents with `name` and `description`; commands; skills. `CLAUDE.section.md` is one import line, `@<pack>/core.md`. `settings.hooks.json` holds the hooks to merge into `.claude/settings.json`: a `UserPromptSubmit` hook that adds the closest decisions to each prompt, and, only when the checks' bench is green, a `PreToolUse` hook that blocks a `git commit` failing the pack's checks (exit 2). |
| `cursor` | `.cursor/rules/<pack-id>-core.mdc` (always applied), `.cursor/rules/<pack-id>-<name>.mdc` | `.mdc` with `description` and `alwaysApply`; a plain `.md` there is ignored. Rules and agents are applied when their description matches. |
| `copilot` | `.github/instructions/<pack-id>.instructions.md` (`applyTo: "**"`), `.github/agents/<name>.agent.md` | The core as repository instructions; custom agents with a `description`. |

## Hooks and checks

Engineering packs have `hooks/*.md` (judgment an agent applies at a git event) and `hooks/checks.json`
(what is not a judgment call: a credential in a diff, the commit message format, a pattern the person
bans). The checks run with the copy of `ceet_check.py` in the pack's `bin/`:

```bash
python3 <pack>/bin/ceet_check.py bench --pack <pack>     # green or red, on its cases and on the current tree
python3 <pack>/bin/ceet_check.py pre-commit --pack <pack>
python3 <pack>/bin/ceet_check.py commit-msg --pack <pack> .git/COMMIT_EDITMSG
```

Wire a check only when its bench is green, and only with the person's approval: as git hooks (a
`pre-commit` and a `commit-msg` script calling the modes above, through `core.hooksPath` or the
project's hook manager) or through the Claude Code adapter. A red check is a work item, not a
guardrail. Every mode fails open: a broken check never blocks every commit.

## Tools without an adapter

- **Claude (claude.ai, Desktop, API):** add `core.md` to the project knowledge or the system prompt,
  and the matching `agents/` or `skills/` file per task.
- **ChatGPT:** `core.md` in the custom instructions or a GPT's instructions; `examples/decisions.md`
  and the rules as knowledge.
- **Gemini:** `GEMINI.md` with `@file` imports of `core.md`, or a Gem's instructions.
- **Windsurf / Devin Desktop:** workspace rules with `core.md`; `AGENTS.md` is read as well.
- **Aider:** `aider --read <pack>/core.md`, or `read:` in `.aider.conf.yml`.
- **Anything else:** "You are working with <person>. Follow the core below on every task," then
  `core.md`, then the file that matches the task.

## Updating

A re-profile goes through `render_pack.py reprofile <pack> --profile <new.json>` (dry run, then
`--write`): it records what moved in `profile-changelog.md` and re-renders the adapters the pack already
has. After that, or after a hand edit to `cognitive-profile.json` and a `render --write` with the same
adapters, `install` again: files the pack installed are replaced, files edited by hand since are
reported.
