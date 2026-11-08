---
name: autoloop
description: Runs the backlog on its own with N Claude sessions in parallel, each on a different card in its own git worktree, all integrating into one control branch, with a supervisor that clears every session's context between cards. Use it when the user types `/autoloop` (`/autoloop 3`, `/autoloop --target <branch>`, `/autoloop status`, `/autoloop stop`), asks to "run the loop", "work the sprint on its own", "start N agents on the backlog", asks what the loop is doing, or wants it stopped; and inside a loop session, for claiming a card, publishing it, and integrating a reviewed card into the control branch.
---

# Autoloop: the backlog, worked in parallel

`backlog` says how ONE session works a card. This skill runs many of them at once without them
stepping on each other: a **supervisor** keeps N background sessions alive, one per **slot**; each
slot is a **git worktree**; each card is **claimed** by exactly one slot; every reviewed card is
**integrated** into one **control branch**, which a person merges into the main branch by hand.

```
/autoloop 3 ─► supervisor (no model, detached)
                 ├─ slot 1: ~/wt/loop-1 ─ claude --bg ─ claims PROJ-12 ─ wt/PROJ-12 ─┐ publish
                 ├─ slot 2: ~/wt/loop-2 ─ claude --bg ─ reviews PROJ-9 ──────────────┼─► merge + push
                 └─ slot 3: ~/wt/loop-3 ─ claude --bg ─ claims PROJ-14 ─ wt/PROJ-14 ─┘   control branch
```

**Why these pieces and not others.** Subagents cannot do it: a session cannot clear its own
context, and a card's work needs a fresh one. `claude -p` cannot either: it kills a session's
background tasks seconds after its turn ends. `claude --bg` sessions can, and `claude agents --json`
says whether each is `busy` or `idle`, which is all a supervisor needs. Worktrees, because two
sessions in one tree share an index and a checkout. A claim, because the tracker accepts a second
session on a card an agent already works. One control branch, because the cards of a sprint are
reviewed against each other, not against a main branch that moves without them.

## Before the first call

1. **Read `.harness/config/autoloop.json`** (keys below; every one optional).
2. **The `backlog` skill must work in this session**: its MCP server connected. The workers use it
   for everything about cards; this skill never talks to the tracker itself.
3. The tool is `node <skill>/scripts/autoloop.mjs <command>` (the CLI below), run from the project.
   Node 18 or later, git, and `claude` on the PATH; `gh` for the spent check (without it, a spent
   branch is not detected and the check says so).
4. **This machine's tracker credential**, when the config names `pickRun`: `start` runs it once and
   exits 6 when it fails, naming why. Without it every session starts on `unknown` and relaunches
   (2026-11-03, a machine with no heartbeat token: a relaunch per session, and every resumed review
   misread). On Officium the credential is the heartbeat token: the backlog's `heartbeat.setup`, once
   per machine, then `start` again.

**A project in WSL, opened from Windows** (`\\wsl.localhost\<distro>\...`) is detected from the
path: git, `gh` and the setup command run inside the distro through `wsl.exe` (Windows git fails
on those paths), `claude` and the supervisor run natively on Windows with the UNC path as the cwd,
and the slot's variables reach WSL through `WSLENV`. Nothing to configure.

## `/autoloop`: what the person types

| Command | What to do |
| --- | --- |
| `/autoloop [n] [--target <branch>] [--phases <p,...>]` | Resolve the control branch (below). With neither `--target` nor `target` in the config, read the **active sprint** through the backlog and pass its number as `--sprint <n>`. Then `start [n] [--target <b> \| --sprint <n>] [--phases <p,...>]` and report the slots it printed. `n` defaults to `slots` in the config. |
| `/autoloop review` (or "only review", "a review pass", in any words) | The same, with `--phases review`: the workers take only cards in Review, never refine or build one, and park once none is left. `--phases` takes any of `review`, `ready`, `todo`, `refine`, comma-separated; `all` (the default) is the backlog's own pick order. A running loop is changed by `stop` and `start` again. |
| `/autoloop standby [n] [...]` (or "wait for the board", "start it from the tracker") | The same `start`, with `--standby`: the supervisor and its worktrees are up (a new worktree's `setup` runs at the first Start), no session is launched, and the loop waits for the tracker's Start (`remoteSwitch` in the config; without it `start` exits 2). |
| `/autoloop status` | `status`: the phases, and per slot its worktree, session id, state (`busy`/`idle`/`parked until`/setup/disabled and why), the card it holds and how many it finished. Add the board's view: the backlog's working cards. |
| `/autoloop stop` | `stop [--reason <text>]`. Every session is stopped within one poll; **nothing is removed**: worktrees keep their uncommitted work, claims stay, conversations stay resumable. The next `start` resumes each slot where it was. A supervisor that was killed instead leaves its sessions running, and the next `start` adopts them rather than launching a second session into the same worktree. |

`start` exits 5 when the control branch is spent and 2 when it cannot be resolved; say why and ask,
never guess a branch. It exits 6 when the config's `pickRun` fails (see "Before the first call").

## The control branch

Where all the slots' reviewed work goes. Resolved in this order:

1. `--target <branch>`, the person's choice for this run;
2. `target` in the config, the person's standing choice;
3. else the active sprint's branch, `targetTemplate` with `{projectTag}` (the config's
   `projectTag`, else the backlog's key prefix in lower case) and `{sprint}`:
   `feat/cb-{projectTag}-sprint-{sprint}` by default ("cb" = control branch), in **rounds**: a sprint
   outlives its control branch's pull request, so the template's branch is the sprint's first round and
   `<branch>-<n>` its n-th. The live round is the latest on the remote that has not merged; once it merges,
   the next one is opened (2026-11-03: one sprint went through seven rounds named by hand).

Missing on the remote, it is created there from `<remote>/<baseBranch>`, as a remote ref only, so
no local branch can end up tracking the base branch. **Its pull request is merged into the main
branch by a person, never by the loop.** Once that pull request merges the branch is **spent**:
nothing more is integrated into it. Under the template, the workers move the loop on with
`target --sprint <n>`: the sprint's next round, or the next sprint's first; a branch the person chose stops
the loop, and the person names the next one. `target --check` also lists commits that reached the branch after its merge:
they are carried to the next one, never left behind.

## The worker protocol

Every worker gets `prompt.md` (this skill's), with the project's own notes appended from the
config's `prompt`, and its slot's values filled in. In short:

1. `target --check` first; a spent branch is never integrated into.
2. **Resume before picking**: `slot` says `RESUME` when this slot holds a claim, sits on a
   `wt/<KEY>` branch, has uncommitted changes or a merge in progress. A session that died, relaunched
   or was recycled while silent left it; the next one in the same slot finishes it, read as its unit
   (the tracker's unit read, `cards.unit` on Officium): a resumed epic is worked in its sweep's phase,
   never in the epic's own column, which says Action while its sweep waits for review (2026-11-03).
3. **Claim before taking**: `claim <KEY> [<KEY>...]` with the candidates in the backlog's pick order
   claims the first one free and prints it. That card, and no other, is the worker's; it marks it
   actively worked in the tracker at once. Exit 1: all taken, get more candidates. The candidates
   come from the tracker's own pick, asked again with every refused key left out, never from a card
   search of the worker's: a search sees cards, not units, and split an epic's review card by card
   (2026-10-28). Under `--phases` the pick is asked for those phases only (the `{{PHASES}}` placeholder);
   a resumed card is finished whatever its phase. **Never released as it was found**: a card the
   worker cannot work for a reason in its own state gets its wall once (`requestHuman`, unblocking it)
   before it is released, because the pick hands an unchanged unit to the next session, and the next
   (2026-11-03: 33 sessions on two epics). **Nothing to claim**: `idle [--reason <text>]`
   ends the turn instead of `done` (refused while the slot holds a claim, a `wt/` branch, changes
   or a merge), and the supervisor parks the slot for `idleRetryMinutes`.
4. **Run on the card's model**: the tracker serves `runConfigs` (`{role: {model, effort}}`) on every card view. The session starts before it has a card, so when its model, effort or tool tier differs from the card's role, the worker runs `relaunch --model <m> --effort <e> --tier <t>` and ends its turn. The tier is the role's `toolTier` (`read`, `comment` or `write`), when the catalog names one: the tools the session may use, held by the launch (see "Tool tiers" below). The supervisor restarts the slot on that model (below); the claim stays held, so the new session resumes the same card through `RESUME`. Every card view also serves `mods` (`{role: [modId]}`): the worker reads each mod of its role with `mods.get` and follows it. A Refine card is planned, not built: its worker writes the action plan to the card and nothing to the tree. On a tracker with workflows, a Refine card with no `workflow` is first a workflow session: it writes the card's workflow (`cards.setWorkflow`) and nothing else, then ends, on the `workflow` cell rather than the matrix's. A card inside an epic takes its epic's workflow, written once for all the epic's cards, so its workflow session writes the epic's (or adds the part the card's category lacks) instead.
5. **Author** on `wt/<KEY>` (`begin`), every commit with the key; `publish` when it goes to review.
   **A sweep**: on a tracker that executes by epic, the pick can be an epic with a `sweep`. It is one
   unit: `begin <EPIC>`, then every checkpoint in the sweep's order in this one session, on the sweep's
   run (the same for all of them), with the tracker's checkpoint write between them and a commit per
   checkpoint; never a relaunch mid-epic. The checkpoint the sweep names `next` is always buildable: a
   sibling In Review was built on `wt/<EPIC>`, whatever that card's `blocked` says. Nor a checkpoint sent back to To do mid-sweep, nor a session
   that ends after one step while the epic has work it can still do: a checkpoint's comments are read
   before it is resumed, and one that waits on a person is asked once and stays In progress while the
   sweep goes on. A sweep in review integrates `wt/<EPIC>` once and approves or sends back each of its
   cards.
6. **Reviewer = integrator**, never in the session that built the work: a review is a fresh session's
   reading of it, and another session of the same slot may give it (owner decision, 2026-10-28,
   by machine, a unit every slot had touched could never be reviewed). `integrate <KEY> merge` (it merges the
   PUBLISHED branch, and refuses a local one with commits that were never published) → resolve
   conflicts on the control branch, reading the cards it names → re-run the card's checks on the
   merged tree → `integrate <KEY> push`. Pass: `approve` to deploy, with the audit's scorecard. Fail: `integrate <KEY> abort`, back to To do
   with `sendBack` (reason `integration-failed`, plus any other) and the findings.
7. `done` last: frees the slot's claims, parks the worktree on the control branch's tip, and writes
   the done marker. A workflow session ends with its card still in Refine: that is its phase's end. The supervisor recycles the session when its turn ends.
   With the config's `doneCheck`, `done` is **refused** (exit 7) while the tracker says the held unit still has
   work for the session, which it would hand straight back to the next one: a sweep that names a checkpoint to
   build, a card still In progress that nothing holds back. A model's habit of stopping after a commit is not
   fixed by the prompt alone (2026-11-03: two sweeps in a row ended after one commit, and each next session paid
   a start to go on; Haiku had done the same before). `done --forced run-killed|environment|context` is the
   closed list of exits past it, and a check that cannot answer lets the `done` through with a warning.

## The supervisor

`start` launches it detached (`<git common dir>/autoloop/supervisor.log`); it outlives the session
that ran `/autoloop`. Every `pollSeconds` it reads `claude agents --json` and, per slot:

| Seen | It does |
| --- | --- |
| no session | `claude --bg` in the slot's worktree, with the rendered prompt (read again for every launch) and the slot's variables; a parked slot waits until its `parkedUntil` |
| idle marker and `idle` | park: `claude stop`, `claude rm`, marker removed; no session until `idleRetryMinutes` have passed, then a new one looks for a card again. A done marker wins over an idle marker, and an idle marker over a relaunch marker |
| done marker and `idle` | recycle: `claude stop`, `claude rm`, marker removed; a new session next poll |
| done marker and `busy` | waits while the transcript is still written (a `Stop` hook sent the session back to work); recycles after `doneGraceSeconds` of silence, since an armed Monitor keeps a finished session `busy` |
| relaunch marker and `idle` | relaunch: `claude stop`, `claude rm`, marker removed; the claims and the done marker are untouched, `cards` does not grow, and the slot's `run` becomes the marker's `{model, effort, toolTier}` (the tier when the marker names one; a marker with a tier this skill does not know is no relaunch). The next session launches with `--model` and `--effort` after `claude.args`, and with the tier's tools held back. `run` outlives later recycles, so the next card of the same phase needs no relaunch. A done marker wins over a relaunch marker |
| no transcript write for `idleMinutes` | recycle, marker or not: nobody is working there. The claim stays, so the next session resumes the card |
| gone within `startTimeoutSeconds` of its launch, or never seen | a failed start; `maxFailedStarts` in a row disables the slot, with the reason in `status` |
| a stop request | `claude stop` on every session (not `rm`), then it exits |
| standby | `claude stop` on every session (not `rm`), as a stop request, but the supervisor stays: the slots launch again when the remote switch says start |

**The remote switch** (`remoteSwitch` in the config) lets the tracker start and stop the loop. Every
`pollSeconds` (20; in practice the first poll after it, so every 30 s with the default 15 s poll) the supervisor runs its `command`, without a session or a model, with
`AUTOLOOP_STATE` `running` or `idle` (standing by); the command reports that state to the tracker
and prints back the order the board queued: `start` leaves standby, `stop` enters it. A loop that
stops beating shows offline there. A failing or garbled run is logged and decides nothing; `status`
shows `standby` and the last beat. Only a local `stop` ends the supervisor.
The order may carry a `reason` (and a `gate` object: `branch`, `compareUrl`, `wallCard`): a tracker can stop the
loop with one, for example an integration gate asking a person to merge the control branch. The supervisor logs
it, keeps it in its state until the next `start`, and `status` prints it as `Stopped by the tracker: ...`; the
person restarts the loop after acting.

It also refreshes its slots' claims every poll; a claim older than `claimTtlMinutes` has no live
supervisor behind it and another slot may take it over (one taker at a time, under a lock, so a
stale claim has exactly one new owner). A new worktree runs the config's `setup` (dependencies)
before its first session, without holding up the other slots.

**A poll that fails decides nothing**, and the next one runs: `claude agents` output that is no
session list (an update notice alone, say) makes that poll's sessions unknown, and an error in one
slot keeps that slot as it was without losing what the others did. Each is a line in the log.

**The prompt's `{{MODEL}}`, `{{EFFORT}}` and `{{TIER}}`** are the slot's `run`, or `unknown` before its first relaunch, so a worker can tell whether it already runs what its card asks for.

## Tool tiers

A role declares the most its session may do with its tools (`toolTier`: `read` reads the tree and the board, `comment` also runs the project's declared checks and this CLI, `write` is the session as it is). With `tiers.enabled` true in the config, the supervisor launches a `read` or `comment` session without `Edit`, `Write`, `NotebookEdit` and `PowerShell` (`--disallowedTools`), with `AUTOLOOP_TOOL_TIER` in its environment. The project's guard hook reads that variable and holds the shell: default-deny, a command passes only when every part of it is allowed by the tier, and a redirect writes only to the declared `scratch` and `outputs` directories. A `write` session, a run with no tier, and any session with tiers switched off launch exactly as before. The guard closes the tool surface; it does not sandbox a command the tier allows, which can still write by its own behaviour. `{{PHASES}}` is `start`'s `--phases` (`all` without it), and `{{IDLE_RETRY}}` the config's `idleRetryMinutes`.

**The slot's environment**: `AUTOLOOP_SLOT`, `AUTOLOOP_SLOTS`, `AUTOLOOP_TARGET`,
`AUTOLOOP_MACHINE` (`<machine>-loop-<n>`, so the tracker's resumable cards are per slot), and
`AUTOLOOP_PORT_OFFSET` (`n × portOffsetStep`), plus the config's `env` with `{{MACHINE}}`-style
placeholders filled. They are passed in a per-slot settings file (`claude --settings`), never
through the launching process: every background session is hosted by Claude Code's background
daemon and inherits the daemon's environment, which is whichever launch started it. And the tool
derives the slot from the worktree's own name (`<worktreePrefix><n>`), refusing a variable that
disagrees, so two slots can never share claims.

## Long sessions: compaction, and the prompt's prefix

A sweep can outgrow the context a model works well in. Claude Code compacts a session itself when it
reaches its auto-compact window, keeping the session, its system prompt and its run: give the slots a
window with `claude.args` (`--autocompact 200k`, say). Nothing is lost to it, because every
checkpoint ends in a commit and a tracker write, and the worker re-reads the epic and `git log` after
one. The skill adds no compaction of its own: a session cannot clear its own context, and relaunching
would pay the start context again. The prompt keeps what changes per session (the picked card, model,
effort and tier) in its last section, after the project's notes, so consecutive sessions of a slot
share the rest of the prefix.

## Shared resources: what a project must do

Parallel slots share a machine. What collides, and how a project avoids it:

- **Ports.** Every fixed port a test server binds adds `AUTOLOOP_PORT_OFFSET` (0 outside the loop).
- **CPU.** Test runners divide their default worker count by `AUTOLOOP_SLOTS`.
- **One-at-a-time jobs** (a full attestation run): a lock under the git common dir.
- **Conflicts git does not see**: migration ids or sequence numbers two cards pick at once,
  generated baselines and lockfiles (regenerate, never hand-merge). The project's prompt names them.

## Configuration: `.harness/config/autoloop.json`

`config.schema.json` is the schema, `config.example.json` an example.

| Key | Default | Meaning |
| --- | --- | --- |
| `slots` / `maxSlots` | `2` / `6` | Slots when `/autoloop` names none; the most it accepts. |
| `target` | none | The control branch the person chose (wins over the template). |
| `targetTemplate` | `feat/cb-{projectTag}-sprint-{sprint}` | The sprint's control branch. |
| `projectTag` | the backlog's key prefix, lower case | `{projectTag}` in the template. |
| `remote` / `baseBranch` | `origin` / `main` | Where branches live; what a new control branch starts from. |
| `worktreeRoot` / `worktreePrefix` | `~/wt` / `loop-` | Slot worktrees: `~/wt/loop-1`... (`~` is the git side's home). |
| `setup` | none | Shell command run once in a new worktree (e.g. installing dependencies). |
| `prompt` | none | Project notes appended to the worker prompt (path from the project root). |
| `machineName` | `hostname` | `hostname`, `env:VAR` or a literal; each slot is `<it>-loop-<n>`. |
| `env` | `{}` | Extra variables for every worker; values may use the prompt placeholders. |
| `idleMinutes` / `doneGraceSeconds` / `pollSeconds` / `startTimeoutSeconds` / `maxFailedStarts` | `30` / `120` / `15` / `120` / `3` | The supervisor's clock. |
| `claimTtlMinutes` | `15` | Age at which an unrefreshed claim may be taken over. |
| `portOffsetStep` | `100` | `AUTOLOOP_PORT_OFFSET` = slot × this. |
| `doneMarker` | `.claude/autoloop.done` | What `done` writes in the worktree. |
| `relaunchMarker` | `.claude/autoloop.relaunch` | What `relaunch` writes in the worktree (`{model, effort, at}`). |
| `idleMarker` / `idleRetryMinutes` | `.claude/autoloop.idle` / `30` | What `idle` writes in the worktree (`{reason, at}`); how long a parked slot waits before a new session looks again. |
| `claude` | `{"command": "claude", "args": ["--dangerously-skip-permissions"]}` | How a worker is launched (`--bg` and its name are added). |
| `liaison` | none | `{command, pollSeconds = 60}`. With 2 or more slots the supervisor itself (no session, no model, no tokens) runs `command` every `pollSeconds`, from the project root with `AUTOLOOP_MACHINE` set to the lowest enabled slot's machine, and a 30 s timeout. It prints ONE JSON line, `{pending, open, summary}`; a non-null `open` (http(s) only) is opened in the person's default browser on this machine (Windows `rundll32 url.dll,FileProtocolHandler`, macOS `open`, WSL `explorer.exe`, Linux `xdg-open`, never through a shell). A failing or garbled run is logged and decides nothing. `status` shows its last result. With one slot, or without it, there is no liaison. |
| `pickRun` | none | `{command}`: before each launch the supervisor itself runs `command` from the project root with `AUTOLOOP_MACHINE` set to the slot's machine, and starts the session on the `{"model", "effort"}` its ONE JSON line prints (the backlog skill's `officium-next-run.mjs` on Officium). A slot that holds a claim gets the run of ITS card (`AUTOLOOP_CARD`); any other slot gets the run of the first card no live claim on the machine holds (`AUTOLOOP_EXCLUDE`, the live claim keys, comma-separated), in the run's `--phases` when it has them (`AUTOLOOP_PHASES`, comma-separated). The tracker may use `AUTOLOOP_MACHINE` too: the slot has no session while it is asked, so whatever its machine still shows as actively worked is stale and can be ended, and the slot's own unfinished unit can come before the pick (Officium does both). The line may name that card as `"key"`: the prompt receives it as `{{CARD}}`, and the session claims it first instead of ranking the backlog again (`none` for a holder, which resumes its claim, or when no key came). A session that started on another model than its card's spends a whole turn only to relaunch; with it, a relaunch is the exception. A slot a relaunch restarted keeps the run it had; a failing or garbled run keeps the slot's run. The run may name its `toolTier` too; an unknown one makes the run no run at all. |
| `tiers` | `{enabled: false}` | `{enabled, scratch, outputs, checks}`. With `enabled` true, a `read` or `comment` session is launched without the file-writing tools (see "Tool tiers"). `scratch` and `outputs` are the directories a held session may write to, relative to the project root; `checks` are the command prefixes a `comment` session may run (its declared checks). A `read` session runs no check and no CLI command. Disabled, every launch is as before. |
| `remoteSwitch` | none | `{command, pollSeconds = 20}`: the tracker's Start/Stop switch (see The supervisor). The command prints ONE JSON line, `{"command": "start" | "stop" | null}` (plus an optional `reason` string and `gate` object), and runs from the project root with `AUTOLOOP_STATE`, `AUTOLOOP_MACHINE`, `AUTOLOOP_SLOTS` and `AUTOLOOP_TARGET`. Any number of slots. |
| `doneCheck` | none | `{command}`: the done gate (worker protocol, step 7). Run from the project root with `AUTOLOOP_CARD` set to the held keys; it prints ONE JSON line, `{"open", "key", "reason"}` (the backlog skill's `officium-done-check.mjs` on Officium). `open: true` refuses the `done`; a failure lets it through with a warning. |
| `preflight` | none | `{command}`: what this machine cannot run, asked once by `start` before any session; a non-zero exit is printed as a warning and the loop starts anyway (an epic's gate once spent 12.5 minutes learning that the dev API was down). |
| `cli` | `node .harness/skills/autoloop/scripts/autoloop.mjs` | How the prompt tells workers to run this tool. |

## Limits

- **One machine.** Claims are directories in the git common dir. Several machines on one backlog
  need the tracker to claim (`next` excluding taken cards, a conflict for a second taker).
- **Unattended means bypassed permissions.** Workers start with `--dangerously-skip-permissions` by
  default, like any unattended agent; the project's own hooks are what guard it.
