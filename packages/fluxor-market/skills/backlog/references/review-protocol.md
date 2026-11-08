# The review protocol

How a session that did not write the work reviews it. SKILL.md's "Work a card by its phase" (the
Review row) points here; the review roles (`code-reviewer`, `security-reviewer`, and the rest of the
`phase-review` roles) repeat the order, never the bar.

## 1. Order: the evidence before the author's words

1. **Take the card**: its description, its criteria, its category, its signals and its
   `eligibleRoles`. The comments and the commit bodies are the author's claims. Do not reason from
   them yet.
2. **Evidence pass**: read the diff and its tests, run the checks that cover them, and walk each
   criterion and the category's exit contract as `met`, `not met` or `not verified`, quoting the
   evidence. Pick the lenses (section 3). Draft the findings.
3. **Then read the author's comments and commit bodies**, and check each claim against the evidence.
   A contradicted claim is a finding. A named untested path is either verified or stays `not
   verified`. An explanation never lowers a finding; only new evidence does.
4. **Score the pillars and post** the comment (section 4), then approve or send back.

Report step 2 with `reportStatus` while it runs, so the evidence is on the card before the claims are.

## 2. Confidence: a number anchored on evidence, not on feeling

Each finding carries a confidence from 0 to 100:

- **80 to 100**: reproduced (quoted output or a capture), or traced to a concrete input.
- **50 to 79**: real but minor, rare, or not provable here. Non-blocking.
- **25 to 49**: plausible and unverified. Post it as a `question`.
- **0 to 24**: suspicion, or it predates the change. Dropped.

**The blocking threshold is 80, stated here and nowhere else.** A blocking finding (`issue (blocking)`,
an entry in a send-back's findings, a `violated` row) carries `Evidence:` and `Confidence:` at or
above it. A rule that cannot be established at the threshold is `not verified`, never `violated`.
Before settling under the threshold, try once to raise it: run the check, trace the path. An unmet
criterion is verified by quoting it against the diff.

## 3. Lenses: what the diff shows, applied by this table

A lens is a checklist, not a second persona: a session works as the one role it took. For a lens
with a specialist role, read that role's prompt (eligible or not) and walk its Expertise as the
checklist. Label each finding it produces `[lens]` and score the pillar the finding harms.

| Trigger | Lens and checklist | Role | Pillar |
| --- | --- | --- | --- |
| signal `touches-auth-permissions-or-personal-data` | security: authz at every entry, no secret in the diff | security-reviewer | runtime_guardrails |
| signal `touches-ui` | rendered screens at both viewports, every state | ux-ui-accessibility-reviewer | ux_and_polish |
| signal `touches-hot-paths-or-heavy-queries` | performance: the path measured, queries bounded | performance-reviewer | runtime_guardrails |
| signal `touches-data-schema` | migrations safe, nulls and time zones | code-reviewer (Data domain) | clean_code |
| signal `touches-infrastructure` | declarative, idempotent, pinned, rollback path | code-reviewer (Infrastructure domain) | architecture |
| diff: tests added or changed | fails without the change, asserts behaviour, covers the edges, deterministic | code-reviewer (Tests as code) | testing_rigor |
| diff: error handling changed (catch, fallback, default on failure, retry, log-only) | no empty catch, no success-shaped result on failure, the failure has a test | code-reviewer | runtime_guardrails |
| diff: new or changed type, schema, DTO, wire field or public signature | invalid states unrepresentable, no `any` or unchecked cast, nullability explicit, `Public contracts:` true | code-reviewer | architecture, clean_code |
| diff: new dependency, cross-context import or package | the edge between modules | architecture-reviewer | architecture |
| diff: docs, README, llms.txt, harness rules or Officium pages | the document says what the code does | documentation-reviewer | clean_code |

## 4. The comment's shape

One comment, in this order, the tracker reads the lines by their labels:

- `Evidence:` what was run, read and seen (commands, outputs, files).
- `Lenses:` each lens applied, with the signal or the diff fact that chose it.
- `Author's comment:` each claim checked, confirmed, contradicted or not verified.
- `Rules checked:` followed on the next line by the table `| rule | verdict | evidence |`, with no
  blank line between them: the board reads that table exactly this way.
- `Screens:` on a `touches-ui` card, naming the captures.
- `Findings:` a table `| # | label | file:line | finding | evidence | confidence |`.

The `Rules checked:` part, as the board reads it:

```
Rules checked:
| rule | verdict | evidence |
| --- | --- | --- |
| the criterion or rule | pass | the quoted evidence |
```

Each `Known failure modes:` line of the plan is one row of that table, with the failure as its rule:
`pass` when the check the plan names for it ran and held, `violated` when the failure happened again
(a send-back, with that rule in `ruleViolations`). A plan with no such line, or one written before
this rule, gets its row as `not applicable`, with the reason; `Known failure modes: none found` is a
row of its own.

## 5. Sources

The confidence scale and the threshold follow claude-plugins-official `code-review` (issues scored
0 to 100 against anchors at 0, 25, 50, 75 and 100, and those under 80 dropped), and addyosmani's
`agent-skills` `doubt-driven-development` (strip the reasoning first: handing over conclusions gets
back validation of them).
