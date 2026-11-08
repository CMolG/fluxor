# Adapter: Officium

Officium is a kanban tracker with an MCP server built for agents: it records agent runs, detects
human edits, and has a lane for work that needs a person, so every part of the protocol maps to a
native operation and nothing degrades.

## Connection

| | |
| --- | --- |
| Default `mcpServer` | `officium` |
| Hosted endpoint (`mcpUrl`) | `https://javadaba.com/api/officium/mcp` (a self-hosted instance serves the same path on its own host) |
| Board (`boardUrl`) | `https://javadaba.com/officium/app` |
| Auth | OAuth with the user's account on that host: the client opens the sign-in on first use (`codex mcp login <server>` for Codex). |

Setup, once per machine (from `backlog.json`):

```bash
claude mcp add --transport http officium https://javadaba.com/api/officium/mcp
codex mcp add officium --url https://javadaba.com/api/officium/mcp && codex mcp login officium
```

## The two tools

The server exposes two tools: **`discover`** lists the operations with their parameter schemas,
and **`query {operation, params}`** runs one. Every operation below is called through `query`.
Call `discover` once when an operation's parameters are unclear: the schema there is the truth, and
it outranks this file if they ever disagree.

Every write takes the card's **`expectedVersion`**. A stale one answers `version_conflict` with the
CURRENT card: re-read, merge your change onto it, retry. Writes are recorded as the agent's, which
is what lets the server tell a person's edit from an agent's.

**Answers are short by default.** A write answers the card's `id`, `projectId`, `key`, `status`,
`version` and `updatedAt`, plus what the write itself produced (the new links, the sprint, the comment
or time entry id). `cards.get` answers the whole card with its last 3 comments, `omitted` counts the
rest, and no time entries; `cards.next` answers the card without `description` and `actionPlan`. Pass
`view: "full"` to any of them for the answer as it was before. The short form is a contract:
`cards.get` and `cards.next` keep their `excerpt` and everything a pick needs, and the hooks read the
card key from the first fields of a write.

## Mapping

| Abstract operation | Officium operation | Notes |
| --- | --- | --- |
| `listWorking` | `cards.working` | Cards with an active agent session. |
| `listResumable(machine)` | `cards.resumable {projectId, machine}` | Cards in `doing` whose last run came from that machine and that nobody is working. |
| `listHumanEdited` | `cards.search {humanEditPending: true}` | Cards a person changed since an agent last acknowledged. |
| `acknowledgeHumanEdit(card)` | `cards.acknowledgeHumanEdit` | Always, even when there was nothing to do. |
| `listNeedsHuman` | `cards.needsHuman` | The "Needs you" lane. |
| `nextCard` | `cards.next` | The `ai` card to work now, from Review, Ready, To do or Refine: hotfix and security first, then the project's precedence rules by the position of the first rule a card matches, then priority and that phase order (a project without rules is unchanged). Carries its `phase` and `eligibleRoles`; from the active sprint while one runs; skips human cards, epics and cards an agent is on. `beyondSprint: true` (REST `?beyondSprint=true`) leaves the sprint when none of its cards is eligible: an outside card that blocks a blocked sprint card, else the best card in no sprint. |
| `listBlocked(sprint)` | `cards.search {projectId, sprint, blocked: true}` | The filter is `sprint` (the sprint id); each card carries `blockedBy` as keys. |
| `getCard(card)` | `cards.get` | The card, its last 3 comments and `omitted` counts; `view: "full"` for every comment and time entry. Carries the version. |
| `priorFailures(card, touched?)` | `cards.priorFailures {projectId, keyOrId, touched?}` (REST `POST /officium/v1/projects/{id}/cards/{keyOrId}/prior-failures`, body `{touched}`) | `touched` is `[{path, cards: [KEY...]}]`, from `scripts/card_refs.py touching <path>...` (at most 20 paths, 30 keys each; over a limit it answers `invalid_touched`). Answers `items` (send-backs and escaped defects, each with its `bases`, `reasons`, `ruleViolations` and a `quote` of its findings), and `recurring` patterns. Window, budget and threshold are the project's `quality settings` (`projects.setQualitySettings {projectId, priorFailures}`, owner only; `{}` resets); the defaults are 14 days, 8 findings, 5 cards, a threshold of 3. |
| `listSprints` | `sprints.list` | |
| `setSprint(card, sprint)` | `cards.setSprint` | |
| `moveCard(card, status, role?)` | `cards.move {status, role}` | `role`, one of the card's `eligibleRoles`, is kept with the project's active work profile and that role's model and effort as the phase run `metrics.get` reads `profiles` from (JAVA-1527); a role the card does not offer is dropped, not refused, so copy it from the card's `eligibleRoles` at the status you leave. |
| `rejectCard(card, reason, note, card?)` | `cards.move {status: "rejected", rejection: {reason, note, card?}}` | `meta.states` lists the reasons (`rejectionReasons`, each with `namesCard`) and whether rejecting is on (`rejectionEnabled`); while it is off the move answers `rejection_disabled`. |
| `approve(card, status, scorecard, role?)` | `cards.move {status /* deploy or done */, qualityScorecard: {architecture, clean_code, testing_rigor, runtime_guardrails, ux_and_polish?, observations?, role}}` | Each dimension `clean` or `minor_observations`; `ux_and_polish` only (and then required) on a card with the `touches-ui` signal. Required of an agent on an `ai` card (`contract_unmet`), with `role` one of its `eligibleRoles`; never on an epic. It also needs, posted since the card last entered Review, a comment with a `Rules checked:` line and a table of rows whose verdict is `pass`, `violated`, `not verified` or `not applicable` (`contract_unmet`), none `violated` (`review_rule_violated`: that is a `sendBack`), and a `Screens:` line in the same comment on a `touches-ui` card. The card keeps every review exit in `reviewOutcomes`. |
| `sendBack(card, status, reasons, findings, role?, ruleViolations?)` | `cards.move {status, reviewReturn: {reasons, findings, role, ruleViolations?}}` | `findings` list the blocking findings, each with its evidence and confidence (`references/review-protocol.md`). `ruleViolations` are `<dimension>:<rule>` ids from `meta.states`' `qualityRules` (`quality_rule_unknown` otherwise). |
| `sendBack` (the rest) | `cards.move {status, reviewReturn: {reasons, findings, role}}` | Required on every move from `review` or `deploy` to `refine`, `todo`, `doing` or `ready` (`review_return_required`); refused on any other move (`review_return_without_send_back`). `meta.states` lists the reasons (`reviewReturnReasons`). An agent names `role`, one of the card's `eligibleRoles` (`review_return_role_required`). The findings are posted as your comment, so do not also post them yourself. The card then carries `reviewReturns` (oldest first), OQL has `reviewReturns` (alias `sentBack`) and `returnReason`, and `metrics.get` reports `reviewReturns`. The third send-back from review in a row lands in `refine` instead (card://JAVA-1443): the card carries `reviewRework {streak, cap}`, its findings comment ends in an `## Escalated to refine` block, and a move into review while the streak is at the cap answers `review_rework_cap`. |
| `setRunState(card, state, machine)` | `cards.setRunState` | `running` / `completed`; pass `machine`. |
| `setActivelyWorking(card, bool, machine)` | `cards.setActivelyWorking` | Pass `machine`. |
| `claimCard(card)` | none yet: the `autoloop` skill's local claim (`claim <KEY>...`) | Officium accepts a second session on a card an agent already works, so sessions on ONE machine claim through a directory in the git common dir. Several machines need a server-side claim. |
| `setWorkflow(card, workflow)` / `workflowSchema` | `cards.setWorkflow {projectId, cardId, expectedVersion, workflow}`; the card's `workflow` and `meta.states.workflowSchema` | `workflow` is `{version: 1, phases: {<phase>: {role, mods}}}` over refine, action, ready, review and deploy; a role outside that phase's eligible roles answers `workflow_invalid`, naming the eligible ones. The Refine run is `meta.states` `roleMatrix.runs.workflow.refine`. An epic's workflow also carries `cards: {<category>: {<phase>: {role, mods}}}` (a ux-ui spike's row is `spike/ux-ui`): it is written once and governs the epic's cards in both execution modes (its `phases` work the epic's sweep), and a part's roles are eligible for its category with no signals. A card inside an epic takes none of its own (`epic_workflow`): its `workflow` is its epic's part for its category, and `workflowFrom` names the epic. |
| `setActionPlan(card, markdown)` | `cards.update {actionPlan}` | A separate field from `description`. |
| `reportStatus(card, text, machine)` | `cards.reportStatus` | Pass `machine`. |
| `comment(card, markdown)` | `cards.comment` | |
| `createCards([card...])` | `cards.create {cards: [...]}` | A `clientKey` per card; `category` on each; `sprintId` only when the user asked for this sprint. |
| `linkCards(a, b, kind)` | `cards.link` | `related` or `blocks`. |
| `updateCard(card, fields)` | `cards.update` | `description`, `category`, `tags`, `epic`, ... |
| `requestHuman(...)` | `cards.requestHuman` | `why`, `steps`, `doneWhen`, `unblocks`, `category` and the wall's `form`; see below. |
| `summonPerson(machine)` | `POST /officium/v1/projects/{id}/summons {machine}`, run by `scripts/officium-summons.mjs` | Prints `{pending, open, summary}` for the autoloop's `liaison.command`; the server owns the no-spam rules. |
| `beatAutoloop(machine, state)` | `POST /officium/v1/projects/{id}/autoloop/heartbeat {machine, state, slots, target}`, run by `scripts/officium-autoloop.mjs` | Prints `{command}` for the autoloop's `remoteSwitch.command`: the order the board's Start/Stop Autoloop button queued (`autoloop.start` / `autoloop.stop`), once. Without a beat for 90 s the board shows the loop offline. |
| `requestAction(card, action, detail?, why?)` / `listRequests` / `closeRequest(request)` | `cards.requestAction` / `cards.requests` / `cards.closeRequest` | Wait with `scripts/officium-request-wait.sh <requestId>` in the background; see below. |
| `listCategories` | `meta.states` | Fifteen categories: epic, feature, userStory, enhancement, bug, hotfix, regression, refactor, technicalDebt, infrastructure, security, spike, testing, routine, documentation. |
| `categoryGuide` | `meta.states` | `categoryGuide` (per category: `hint` and the Markdown `description` with Signals, Excludes, Entry contract, Exit contract, Behavior), `classifierPrecedence` and `signals`. |
| `qualityLineage` (the lines of a corrective card) | the card's `description` | `meta.states` serves `lineageLines`, `escapedPhases`, `qualityDimensions` and `qualityRules` (by dimension; ids are `<dimension>:<rule>`). An agent's `bug`, `regression` or `hotfix` leaves `refine`, and ends its run, only stating `Caused by:` (a card key or `legacy`), and with a key also `Escaped in:`, `Quality dimension:` and `Violated rules:` (`contract_unmet` names each missing line); a `refactor`, `technicalDebt` or `enhancement` only when its `Caused by:` names a card. The corrective card's view carries `lineage`; the origin's carries `escapedDefects` and `qualityRegressionTriggered`, and both cards are linked `related`. |
| `logTime(card, minutes)` | `cards.logTime` | **Do not use it for your own work**: time is imputed from the run (below). |
| `listDocChanges` | `docs.changelog.list {status: "pending"}` | Every push to the main branch lands here when the project's CI reports it. |
| `markDocChange(change, mark, pages)` | `docs.changelog.mark` | `updated` with `pages`, or `reviewed`. |
| `recordDocChange(ref, title)` | `docs.changelog.record` | `{ref, title, url?, areas?, mergedAt?}`; answers the existing entry when the pipeline already recorded that commit. |
| `searchDocs(text)` / `upsertDoc(page)` | `docs.search` / `docs.upsert` | The project's Documentation pages. `docs.upsert` answers the page plus `findings`, the lint's: warnings, the page is saved. |
| `docSchema` / `lintDoc(page \| body)` | `docs.schema` / `docs.lint` | The page schema is part of Officium's contract, never a page: no `docs.list` shows it. `docs.lint` takes a `body`, or a `projectId` and `path`. |

## Behavior worth knowing

- **Statuses.** `refine`, `todo`, `doing`, `ready`, `review`, `deploy`, `done`, `rejected`
  (`meta.states` lists them). `done` is shown as **Completed** and has no column on the board: people
  reach it from "View completed". That is why a card left in `deploy` after shipping is visible
  noise, and why moving it to `done` needs the evidence comment. `rejected` has no column either
  ("View rejected"): it is reached from any state but `done` with a `rejection`, leaves only for
  `refine` (`rejected_reopens_to_refine`), which clears it, and a card is never created in it.
- **Phases.** `cards.next` carries `phase` (`refine`, `action` for To do and Doing, `ready`,
  `review`, `deploy`) and `eligibleRoles`, computed from the card's category, phase and `signals`,
  with `runConfigs` (each eligible role's `{model, effort}`) and `runConfig` (the cell's), from the
  project's role matrix (`projects.roleMatrix`, `runs`), and `mods` (`{<role>: [modId]}`: the role's required
  mods plus the matrix's cell and signal mods; `mods.list` / `mods.get` read them). An `ai` card leaves `refine` for `todo` or
  `doing` only with a valid `workflow` AND an `actionPlan`, whoever moves it (`contract_unmet`, one sentence per missing slot);
  a card inside an epic is checked against its epic's part for its category, and the refusal names the epic to write it on.
  The plan opens with `Base: <control branch | main | branch name>` and carries `Role: <id>` as the workflow's refine role.
  Setting the plan before the workflow is refused (`workflow_first`). `routine`, `hotfix` and
  epics are exempt.
  A Review, Ready or Refine card is worked where it stands; only a To do card is moved to `doing`,
  and before any work: `action` covers both columns, but To do is only the plan's re-check. The
  server holds it: an agent's `ai` card leaves `todo` only for `doing` or `refine` (straight to
  `ready`, `review`, `deploy` or `done` answers `contract_unmet`), and `cards.setRunState running`
  on one in `todo` answers `contract_unmet` too; the move to `doing` is what starts the run.
  A Ready card's role is `delivery-analyst`. A Review card that passes goes to `deploy` (a spike to
  `done`: a move of a spike to `deploy` answers `spike_skips_deploy`), one that fails to `todo`; a
  Ready card goes to `review` or `todo`; a Refine card ends in `todo`.
- **Deploy closes itself.** When the project's pipeline or connected GitHub repository records a
  merge into main (`docs.changelog.record`, with the commit's whole `message`), Officium moves every
  `deploy` card whose key the message names to `done`, with a comment naming the merge. Close by hand
  only what it missed.
- **A review creates no cards.** `cards.create` and `cards.requestHuman` take `workingOn`, the key of
  the card this session is working on; while that card is in `review` and the session is live on it
  they answer `review_creates_no_cards`. The worker is judged, not the computer: another session on
  the same machine creates as usual. A session working a card passes it always.
- **Priority.** `superHigh` > `high` > `medium` > `low` > `superLow`, then board order.
- **Precedence.** A project may list rules that come before its other cards (`projects.precedence`,
  the owner's `projects.setPrecedence` with the whole list under `expectedVersion`, and
  `projects.previewPrecedence` for an unsaved rule). A rule matches a card by its `epic`, `tags`,
  `categories` and `signals`, and its defaults (`priority` as a floor, `sprint: join`) apply when a
  card enters it. `cards.next` ranks by the first matching rule's position after hotfix and security;
  a card's `precedence` (`{ruleId, name, reason, position, of}`) names that rule. A stale version
  answers `409` with the current list, and a refused list answers `422` with `ruleIndex` and `field`.
- **Epics.** The `epic` field holds the epic card's label or its key; where several epics share a
  label, give the key. The server holds the rules: an epic is never planned into a sprint
  (`epic_not_plannable`), never set running (`epic_not_workable`) and actively worked only in epic
  execution (below), and with no
  children it can only be refined (`epic_has_no_children`); `cards.get` answers its child count as
  `epicChildren`. An epic WITH children follows them: the server moves it to its lowest open child's
  status (`doing` once any child has started) and to `review` once every child is done. A move of
  its own is refused until then (`epic_children_open` to `done`, `epic_status_derived` otherwise),
  and allowed only among `review`, `deploy` and `done`; `epicChildrenOpen` says how many are left.
  `cards.get` of an epic also answers `checkpoints` (its cards in sweep order, each `{id, key, title,
  status, state: pending|in_progress|completed, category, executor, planned, blocked, ready,
  verification, sweepable, mods}`) and `checkpointProgress {completed, total}`.
- **Epic execution.** `projects.executionMode` is `card` (each card handed out alone, the default) or
  `epic`; the owner sets it with `projects.setExecutionMode {mode, implementerRole?, expectedVersion,
  dryRun?}`, and `dryRun: true` answers the `preview` (each open card's unit) and stores nothing. In
  `epic` mode `cards.next` answers a card of an open epic in To do, In progress or Review as the EPIC,
  with `sweep {phase: action|review, eligibleRoles, runConfig, runConfigs, mods, checkpoints,
  progress, next}`; every other answer carries `sweep: null`. The epic may then be actively worked.
  Every action cell but the spikes' names the implementer (`core-implementer`), with mods for the
  retired roles' specialties per checkpoint. `cards.setCheckpoint {cardId, state, note}` moves a
  checkpoint to `doing` (`in_progress`) or comments its note and moves it to `review` (`completed`),
  through `cards.move`'s contracts, and answers `{checkpoint, epic, progress, next}`. Refused:
  `not_epic_mode`, `not_a_checkpoint` (the epic itself, a spike, a card of no open epic),
  `checkpoint_not_pending`, `checkpoint_not_started`, `note_required`. `cards.resumable` lists a sweep
  left mid-epic as its epic. `cards.unit {key}` answers the unit a card is in, in `cards.next`'s shape
  (an epic with its `sweep`), for a session that resumes a card it holds: work it in `sweep.phase`,
  never in the epic's own `phase` on `cards.get`, which is the epic's column. In `epic` mode a
  checkpoint's `blocked` is what holds it back from the sweep (`!ready`): a sibling the sweep completed
  is on the epic's branch, so the checkpoint a sweep names `next` never reads as blocked. An action
  sweep with no `next` (its open work waits on a person) is not handed out; its Refine cards still are.
- **Run sessions.** Moving a card to `doing` or setting it `running` starts a session; moving it
  on stops it. The session **lapses 10 minutes** after the last `reportStatus` or write to the card,
  so keep `statusReportMinutes` at 10 or less. Your writes show as "<client> (<your nickname in the
  organization>)"; the nickname is set on the Organization page.
- **Time is imputed from the run.** The session above is the time record: a gap longer than the
  lapse is time the card does not get. Do not call `cards.logTime` for agent work.
- **Heartbeat and session time (optional).** Where the project wires an Officium heartbeat hook
  (with the account's token in `~/.config/officium/heartbeat-token`), the harness keeps the card
  alive between your writes at no token cost, on each tool call and every 30 s of a long command,
  and at every Stop reports the whole session's time per card picked up, refinement apart from
  work, with each model's and each subagent's tokens; that replaces the run-imputed time. It covers
  liveness only: milestones are still yours to report.
- **Temporary references at review (optional).** Where the project installs the
  `officium-temporary-refs` hook (the `officium` preset does), an agent's `cards.move` to `review`
  is refused while `scripts/card_refs.py list <KEY>` shows a `[temporary]` reference, with each one
  and the fix in the message. It finds the key from the card's id in the session's earlier Officium
  answers, runs only on this machine, and lets the move through when it cannot tell.
- **Resume detection.** `cards.resumable {projectId, machine}` answers the cards whose last run came
  from this machine (`cards.get` carries no `lastRun`). Step 1 of the protocol reads that list. A unit
  another session works (an epic with any card live on the board) is never listed: it is that session's,
  as `cards.next` reads it (JAVA-2004).
- **The autoloop's two supervisor questions** (JAVA-2004), with the heartbeat token, no session and no
  model: `GET .../autoloop/next-run?machine=<slot>` (`scripts/officium-next-run.mjs`) first ends what that
  slot's machine still shows live (stale: the slot has no session while it asks) and answers the slot's own
  unfinished unit before the pick; `GET .../autoloop/unit?card=<KEY>` (`scripts/officium-done-check.mjs`, the
  autoloop's `doneCheck`) answers `{open, next, reason}`: open while an action sweep names a checkpoint to
  build or a card is still In progress with nothing holding it back, which the pick would hand straight back.
  A sweep that reaches Review is another session's to review, so it closes the builder's unit.
- **Blocked.** A card is blocked while any card blocking it is not in `deploy` or `done`; `cards.next`
  never returns a blocked card, in any phase, so step 4's unblocking pass is what reaches one whose
  blockers are in `review` in this branch. A `rejected` blocker keeps blocking: the move answer's
  `blocks` lists the cards to re-point or unlink.
- **Walls.** `cards.requestHuman` creates the card with `executor: human` and its `category`,
  assigns it to the project owner, and stores one `blocks` edge per card in `unblocks`, shown from
  both ends. `cards.next` skips human cards; the board shows them in the "Needs you" lane.
- **Requests ("Waiting for you").** `cards.requestAction {projectId, cardId, action, detail?, why?}`
  answers the request with its `id`, and the card shows it on the board and in Needs you. Then run
  this skill's `scripts/officium-request-wait.sh <id>` in the background (the account's heartbeat
  token, like the session waiter; `--minutes N` caps the wait, default 10). It ends with one line:
  `OFFICIUM_REQUEST_DONE`, `_DECLINED`, `_CLOSED`, `_TIMEOUT <id>`, or `OFFICIUM_REQUEST_FAILED
  <reason>`. `cards.requests` lists the requests that are not closed, with the person's `note`.
  `cards.next` hands out a card whose request was answered first, until `cards.closeRequest`. One
  request per card (`request_exists`); never on a human card or an epic.
- **Walls with a form.** Pass `form: {title?, questions: [{id, kind, prompt, help?, required?,
  options?, logic?}]}` to `cards.requestHuman` (or to `cards.create` with `executor: human`) and the
  wall is born with the Quaestio form its person fills; `cards.attachForm {keyOrId, questions}` gives
  one to a human card that has none. Draft it with `forms.lint {questions}` first (same rules, saves
  nothing: `doc://contracts/quaestio-form-authoring`); a form that breaks them answers `form_invalid`
  with every problem and its question id, and no card is saved. The person fills it at the card's
  `form.fillPath`; when its assignee completes it the card moves to Ready on its own, and
  `cards.get` returns `form.answers` (`questionId`, `prompt`, `value`) with every earlier answer in
  `form.history`. A card sent back to To do takes a new answer. `humanEditPending` keeps its meaning
  for edits and comments, and an answered form raises it too, so step 2 finds it.
- **Definition of done.** A project may set `definitionOfDone` (`projects.get` shows it; the owner sets it with
  `projects.setDefinitionOfDone`, `[]` removes it). Then the finishing comment answers each item: a line
  `Definition of done:` and a table `| item | met / not applicable | evidence or reason |`, one row per item by its
  number. `met` answers it; `not applicable` needs its reason; `not met` is work left. The move to review is refused
  (`contract_unmet`) naming the items with no answer.
- **Form languages.** A project may set `formLanguages` (`projects.get` shows it; the owner sets it
  with `projects.setFormLanguages`). Then every card form there must offer all of them: pass
  `form.languages` (or leave it out to take the project's) and, on each question,
  `translations: {<lang>: {prompt, help?, options?}}` for every language after the first, options
  index for index. A form missing one answers `form_invalid` naming the question and the language;
  `forms.lint` takes `languages` too. The person filling it switches language on the form, and
  `form.answers` always come back in the default language.
- **Keys.** Each project has its own key prefix; cards imported from another tracker keep their
  original keys, which is what `legacyKeyPrefixes` is for.
- **Markdown.** Descriptions, action plans and comments render as Markdown on the board: headings,
  lists, checklists, code and tables.
