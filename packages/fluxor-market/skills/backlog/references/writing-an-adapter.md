# Writing an adapter for another tracker

An adapter is one Markdown file, `references/adapter-<provider>.md`, that tells the agent how to run
the protocol's abstract operations against one tracker's MCP server. Use
`adapter-officium.md` as the template. It needs:

1. **Connection:** the default `mcpServer` name, the endpoint (or how to find it), how auth works
   (OAuth, a token in a header, a local server), and the resulting `claude mcp add` /
   `codex mcp add` commands.
2. **The mapping table:** every abstract operation in `SKILL.md`, the tracker's MCP tool (with the
   parameters that matter), and a note. An operation the tracker cannot do gets an **emulation**
   or the word **degraded** plus what the agent does instead. Never leave a row out: a missing row
   reads as "supported".
3. **Statuses:** the tracker's names for `backlog`, `doing`, `review`, `deploy`, `done`, which
   become the default `statuses` in `backlog.json`.
4. **Behavior worth knowing:** lapses, rate limits, what renders as Markdown, how concurrency is
   detected.

Keep project facts (project IDs, prefixes, URLs of one installation) out of the adapter: they go in
the project's `.harness/config/backlog.json`.

## What degrades when the tracker lacks a feature

General-purpose trackers were built for people, so some of the protocol has to be emulated with
labels, comments and markers. Emulate when it is cheap and reliable; otherwise degrade and say so
once per session, never silently.

| Protocol feature | Needs from the tracker | Emulation / degradation |
| --- | --- | --- |
| Resume before pick (step 1) | Run state with the reporting machine | Emulate: on `setRunState running`, post a comment ending in a marker like `<!-- agent-run machine=<name> state=running -->` and apply an `agent:running` label; a stranded card is one in `doing` whose latest marker names this machine with state `running`. Degraded without it: list `doing` cards assigned to the agent's account and ask the user before resuming. |
| `listResumable` | A query for stranded runs | Emulate: the cards in `doing` whose latest run marker (row above) names this machine, minus `listWorking`. |
| `listBlocked` (step 4) | Blocking links readable per card | Emulate: list the sprint's open cards and keep those with a blocker not in `deploy`/`done`. Degraded without links: step 4's unblocking pass is skipped; say so. |
| `listWorking` / `setActivelyWorking` | A live "being worked" flag | Emulate with a label (`agent:working`) plus the last `reportStatus` time; treat a label older than the lapse as stale. Stale labels are the failure mode: always clear it at the end. |
| `listHumanEdited` / `acknowledgeHumanEdit` | Detecting who edited last | Emulate from history: GitHub issue timeline events, Linear issue history, Jira changelog, compared with the agent's own account; acknowledge by posting (or updating) a marker comment `<!-- agent-ack <timestamp> -->`. Degraded: read comments newer than the agent's last comment. |
| `listNeedsHuman` / `requestHuman` | Cards for a person that block others | A `needs-human` label, the person as assignee, and a blocking link (GitHub issue dependencies, Linear "blocks" relations, Jira "is blocked by" links). `nextCard` must filter the label out. |
| Sprints (step 4) | Sprints and an active one | GitHub Projects iterations or milestones, Linear cycles, Jira sprints. Without them set `sprints: false`: step 4 skips the pull into the sprint and `nextCard` takes the top of the ready column. |
| `setActionPlan` | A field apart from the description | A single comment starting with a marker (`<!-- action-plan -->`) that is edited in place; never a section appended to the description, which would let a rewritten plan overwrite the request. |
| `reportStatus` | A lightweight live status | Edit one marker comment in place (`<!-- agent-status -->`) rather than posting a new comment per milestone, which buries the discussion. Degraded: report only at milestones that matter. |
| `createCards` with `clientKey` | Idempotent creation | Put `<!-- clientKey: <key> -->` in the body and search for it before creating; skip the ones that exist. |
| `expectedVersion` | Optimistic concurrency | Re-read right before writing and compare `updated_at` (or the version field); on mismatch, merge and retry. Prefer append-only writes (comments) over rewriting fields. |
| `deploy` before `done` | A distinct "shipped, waiting" stage | Map `deploy` to the same status as `done` (or a label); the evidence comment is still required before closing. |
| `sendBack` | A recorded return from review to work, with classified reasons | Emulate: move the issue back to its work status and post one comment that opens with `Sent back: <reason ids>` and carries the findings; count them by reading those comments. Degraded without it: the same comment, no counting. |
| `rejectCard` | A terminal state for discarded work, apart from done | Emulate: close the issue as "not planned" (GitHub), move it to Linear's Canceled or Jira's "Won't do", and post the reason and note in a marker comment (`<!-- rejected reason=<id> card=<key> -->`); it must never count as delivered. Degraded without it: leave the card where it is with a comment naming the reason; never delete it and never close it as done. |
| Workflow session (Refine row) | A per-card role and mods for each phase | None of the three has it: the workflow session is skipped and the card is planned as before. |
| Documentation changelog (step 9) | A record of merged changes awaiting a docs answer | None of the three has it: step 9 is skipped. |
| Time from runs | Time imputed from sessions | None of the three has it: log time explicitly at the end if the project tracks time, else skip `logTime`. |

State in the adapter which rows are emulated and which are degraded, so the agent can tell the user
exactly what it cannot guarantee (for example "two agents on this tracker can take the same card:
it has no live working flag").
