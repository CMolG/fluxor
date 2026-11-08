# Internal contracts

> **Schema version:** every artifact below ships with a top-level
> `schemaVersion` field (currently `1.2.0`, `CONTRACT_SCHEMA_VERSION` in
> `scripts/jira_pipeline_cli.py`). The versioning policy is below.

The pipeline reads one input and emits five JSON artifacts:

| Artifact | Producer | Consumer |
|---|---|---|
| `TicketSnapshot` (input) | `fetch-issue`, or any tracker | `discovery` |
| `TicketAnalysis` | `discovery` | `generate-questions`, `base-branch-plan` |
| `BusinessQuestionSet` | `generate-questions` | `collect-input`, `resolve-contract`, `request-human` |
| `RequestHumanDraft` | `request-human` | the backlog's `requestHuman` |
| `FunctionalContract` | `resolve-contract` | `base-branch-plan`, a card comment |
| `BaseBranchPlan` | `base-branch-plan` | engineer review |

An artifact path left out on the command line lands at the project root: `$CLAUDE_PROJECT_DIR`,
else `git rev-parse --show-toplevel`, else the current directory. A path given is used as given.

## Versioning policy

`schemaVersion` follows [SemVer](https://semver.org/):

- **Patch**: clarifications, additional examples, fixed typos in the
  documentation. No code change is required to consume the artifact.
- **Minor**: backward-compatible additions: new optional fields, new enum
  members, new artifact types. Old consumers continue to work.
- **Major**: a breaking change: a rename, a removal, a type change of an
  existing field, or a change in the meaning of an existing value.
  Generated artifacts record the schema version they were produced under,
  so older runs remain interpretable.

Bumping rules:

1. Update `CONTRACT_SCHEMA_VERSION` in `scripts/jira_pipeline_cli.py` and the
   example payloads in this file.
2. Bump the skill's own version in its manifest: a major contract change is a
   major change of the skill.
3. For a major bump, add a migration note here describing how consumers
   should adapt.

### Changes

- **1.2.0** (no field renamed, removed or retyped; 1.1.0 consumers keep working):
  - New `RequestHumanDraft` artifact (`request-human`).
  - `TicketSnapshot.acceptanceCriteria` is read: its items join the analyzed text, and a
    non-empty list removes `acceptance_criteria` from `missingBusinessDecisions`.
  - `BaseBranchPlan.implementationScope` and `excludedScope` hold what the contract decided, as
    this document's example always showed. 1.1.0 filled them with fixed bullets ("Unrelated UI
    redesign", "Add baseline tests ..."), the same for every ticket.
- **1.1.0** (no field renamed, removed or retyped; 1.0.0 consumers keep working):
  - `TicketAnalysis.ambiguityLevel`: keywords and markers match as whole words, and both
    densities count every occurrence, as "hits per 100 words" always said (1.0.0 counted each
    distinct term once, so a ticket that repeats a term now scores higher; the level
    thresholds are unchanged). The marker `" or "` is now reported as `"or"`. New
    `signals.constraintKeywordCounts` and `signals.ambiguityMarkerCounts`.
  - `BusinessQuestionSet.optionalFutureDecisions`: P2 templates, and an `id` (`O<n>`) on every
    optional question.
  - `FunctionalContract.functionalContract`: one field for every catalog category (the table
    below); answers to optional questions are resolved too.
  - `_llmAugmentation.rejectedKeys` also lists `schemaVersion` and `issueKey` when a patch
    tries to set them.

## TicketSnapshot (input)

`discovery` reads one JSON object, and nothing in it is Jira's own: `fetch-issue` is one producer,
and a card from any tracker is another. An agent working a backlog writes it from the card it
already read (the backlog skill's `getCard`):

| Field | From a Jira issue | From a tracker card |
|---|---|---|
| `issueKey` | the issue key | the card key |
| `title` | `summary` | the title |
| `description` | the description, flattened to text | the description (Markdown is fine) |
| `labels` | `labels` | the tags |
| `epic` | `customfield_10011` | the epic label or key |
| `status` | the status name | the status |
| `comments` | `[{author, body, created}]` | the comments, same shape |
| `acceptanceCriteria` | `[]` (Jira keeps none apart) | the checklist items, when the tracker keeps them apart |

Only `title` and `description` matter to the analysis; a missing field reads as empty. The text
analyzed is title, description, labels, `acceptanceCriteria` and comments together, so criteria
written in the description count as much as a separate list.

## Example Data Policy

All examples in this document must use fictional, generic domains.

Do not use:
- real project names
- real issue keys
- real product flows
- real business rules
- real operational incidents
- real customer, company or domain-specific terminology
- examples derived from internal conversations, tickets, repositories or production systems

Examples should be intentionally neutral and non-identifiable.

Preferred fictional domains include:
- content_publishing
- course_enrollment
- warehouse_reservation
- appointment_booking
- subscription_upgrade
- document_review
- event_registration
- inventory_restock

## TicketAnalysis

```json
{
  "schemaVersion": "1.2.0",
  "issueKey": "APP-4827",
  "title": "Enable approval step for premium content publishing",
  "detectedDomain": "content_publishing",
  "confidence": 0.88,
  "businessGoal": "Reduce accidental publication of premium content before final review",
  "missingBusinessDecisions": [
    "applicable_content_types",
    "approval_deadline",
    "reviewer_roles",
    "rejection_behavior",
    "notification_policy"
  ]
}
```

### `TicketAnalysis.ambiguityLevel`

```json
{
  "level": "MEDIUM",
  "constraintDensity": 4.0,
  "ambiguityMarkers": 2.0,
  "signals": {
    "constraintKeywords": ["only", "expire"],
    "ambiguityMarkers": ["tbd"],
    "constraintKeywordCounts": {"only": 1, "expire": 1},
    "ambiguityMarkerCounts": {"tbd": 1}
  }
}
```

- Keywords and markers match as **whole words**: "only" does not fire on "commonly", and the
  marker `or` is the word "or", not the letters in "order". The last word may carry a regular
  inflection (`expire` matches "expires", "expired", "expiring"; `retry` matches "retries";
  `cancel` matches "cancelled"). The words of a phrase match across spaces and hyphens
  (`double click` matches "double-click"). Punctuation markers (`?`) match every occurrence.
- `constraintDensity` and `ambiguityMarkers` are occurrences per 100 words: a keyword used
  three times counts three times.
- `constraintKeywords` and `ambiguityMarkers` list the distinct terms that fired, in catalog
  order; the `*Counts` objects give the occurrences of each.
- `level` is `HIGH` when constraints are sparse (< 0.4) and markers are not (>= 0.4), `LOW` when
  constraints are dense (>= 1.2) and markers are sparse, and `MEDIUM` otherwise.

### `TicketAnalysis._llmAugmentation`

Present only after `merge-llm-suggestions`:

```json
{
  "acceptedKeys": ["businessGoal", "functionalEntities"],
  "rejectedKeys": ["issueKey", "secretInjection"],
  "ruleBasedSnapshot": {
    "businessGoal": "Reduce requirement ambiguity and improve engineering readiness.",
    "functionalEntities": ["content", "review"]
  },
  "appliedAt": "2026-01-01T00:00:00+00:00"
}
```

- Only `businessGoal`, `functionalEntities`, `userActions`, `possibleAffectedFlows`,
  `explicitRequirements`, `missingBusinessDecisions`, `detectedCategories` and `ambiguityLevel`
  can be patched. Every other key in the patch (the identity fields `schemaVersion` and
  `issueKey` included) is not applied and is listed in `rejectedKeys`, as is a list field whose
  value is not a list.
- List fields become the sorted union of the rule-based and the suggested values; other fields
  are replaced. Either way the rule-based value of every accepted key is kept under
  `ruleBasedSnapshot.<field>`.

## BusinessQuestion

```json
{
  "id": "Q3",
  "priority": "P0",
  "category": "Business Rules",
  "question": "How many reviewers must approve premium content before it can be published?",
  "whyItMatters": "Defines the functional approval threshold and blocks implementation if unknown.",
  "suggestedAnswers": [
    "1 reviewer",
    "2 reviewers",
    "Majority of assigned reviewers",
    "All assigned reviewers",
    "Other"
  ],
  "required": true,
  "blocksImplementation": true,
  "defaultIfUnanswered": null,
  "businessImpact": "workflow_control",
  "affectedActors": ["content_editor", "reviewer", "publisher"],
  "relatedAcceptanceCriteria": true
}
```

## BusinessQuestionSet

```json
{
  "schemaVersion": "1.2.0",
  "issueKey": "APP-4827",
  "status": "WAITING_BUSINESS_INPUT",
  "summary": "Business decisions are missing before a safe base-branch can be prepared for the publishing approval workflow.",
  "questions": [],
  "optionalFutureDecisions": []
}
```

`questions` holds the required P0/P1 questions, with ids `Q1`, `Q2`, ... `optionalFutureDecisions`
holds the P2 templates whose category is in the analysis' `detectedCategories`, then every P3
template, with ids `O1`, `O2`, ... Optional questions are never required; `collect-input
--include-optional` asks them after the required ones, and `resolve-contract` resolves any that
were answered.

### `BusinessQuestionSet.budgets`

```json
{
  "baseline": 4,
  "signal": 6
}
```

Records the budget split the question selector used (`--baseline-budget`,
`--signal-budget`), so downstream tools and later evaluations can reason about
how the question pool was built.

## FunctionalContract

```json
{
  "schemaVersion": "1.2.0",
  "issueKey": "APP-4827",
  "functionalContract": {
    "approvalRequiredFor": "premium_content_before_publication",
    "minimumApprovalsRequired": 2,
    "approvalDeadlineHours": 24,
    "allowSelfApproval": false,
    "rejectionRequiresReason": true,
    "notifyEditorsOnDecision": true,
    "featureToggleRequired": true
  }
}
```

The example shows the kind of decisions a contract records. What `resolve-contract` emits has
one field per catalog category, always present: `businessObjective` and `functionalScope` hold
the first answer (a string, or `null`), and every other field holds the list of answers, in
question order (empty when none):

| Category | Field |
|---|---|
| Business Objective | `businessObjective` (string or `null`) |
| Functional Scope | `functionalScope` (string or `null`) |
| Business Rules | `businessRules` |
| State Lifecycle | `stateLifecycle` |
| User Experience | `userExperience` |
| Compatibility & Backward Compatibility | `compatibility` |
| Rollout & Transition | `rollout` |
| Support & Backoffice | `supportAndBackoffice` |
| Messages & Communications | `communications` |
| Risk, Fraud & Abuse | `riskAndAbuse` |
| Legal, Compliance & Privacy | `legalCompliancePrivacy` |
| Data & Functional Reporting | `reporting` |
| Acceptance Criteria | `acceptanceCriteria` |
| Out of Scope | `outOfScope` |
| Actors & Permissions | `actorsAndPermissions` |
| Edge Cases | `edgeCases` |
| Pricing, Billing & Monetization | `pricingAndBilling` |
| Activation & Functional Configuration | `activationAndConfiguration` |
| Auditability & Traceability | `auditability` |
| Functional Error Handling | `errorHandling` |
| Business External Dependencies | `externalDependencies` |
| Internationalization & Localization | `localization` |
| Accessibility & Usability | `accessibility` |
| Perceived Performance | `perceivedPerformance` |
| Functional Security | `functionalSecurity` |
| Data Quality | `dataQuality` |
| Priority, Severity & Criticality | `criticality` |
| Reversibility & Rollback | `reversibility` |
| Migration & Existing Data | `migration` |
| Rapid Decision | `rapidDecisions` |

The table is `CONTRACT_FIELDS` in `scripts/jira_pipeline_cli.py`; a test keeps them in sync.

### `FunctionalContract.unmappedAnswers`

```json
[
  {"questionId": "Q11", "category": "Partner Onboarding", "answer": "Partners join after a manual review"}
]
```

Captures every answer whose category has no field in the table above: a question added by hand
or by the host model under a category the catalog does not know. Every catalog category has a
field, so for questions the CLI generates this list is empty. Without it such answers would be
silently dropped (see `resolve_contract` in `scripts/jira_pipeline_cli.py`).

### On the card: the contract as a comment

The file is the machine's copy; the record is the ticket. Once resolved, the contract goes on the
card as one comment, so the decisions live where the work is tracked and the action plan can cite
them by comment instead of re-asking:

```markdown
**Functional contract** (schema 1.2.0, from Q1-Q7)

- **businessObjective:** Fewer cancellations from monthly members
- **businessRules:** Up to three months · one pause per year
- **outOfScope:** Annual plans
- **unresolved:** Q4 - State Lifecycle: answer requires clarification
```

One line per non-empty field, list answers joined with ` · `, then `unresolvedItems` if any. An
unresolved item is still an open decision: it goes back to the person as a wall, not into the plan.

## BaseBranchPlan

> Note: `proposedBranchName` is a suggestion. The CLI never creates the
> branch — the engineer creates it manually after reviewing the plan, and is
> free to rename it.

```json
{
  "schemaVersion": "1.2.0",
  "proposedBranchName": "ai/APP-4827-premium-content-approval-base",
  "implementationScope": [
    "businessObjective: No premium content is published before final review",
    "businessRules: Two reviewer approvals before publication",
    "businessRules: Rejection requires a reason",
    "communications: Notify editors when content is approved or rejected"
  ],
  "excludedScope": [
    "editorial dashboard redesign",
    "bulk approval operations"
  ],
  "requiresHumanReview": true
}
```

`implementationScope` is one item per answer in the contract (`<field>: <answer>`), out of scope
apart; `excludedScope` is the contract's `outOfScope`. The plan states what the business decided
and nothing else: how the work is done (tests, branch, report) is the project's own workflow.

## RequestHumanDraft

`request-human --questions questions.json [--answers state.json]` renders the required questions
still unanswered as a wall card for a person, in the shape of the backlog protocol's
`requestHuman` (title, why, steps, doneWhen, unblocks, category), so a tracker adapter sends it as
is:

```json
{
  "schemaVersion": "1.2.0",
  "issueKey": "APP-4827",
  "ready": false,
  "title": "Business decisions for APP-4827: 2 question(s)",
  "why": "APP-4827 cannot be planned without product decisions only a person can make: ...",
  "steps": "Answer on APP-4827 (edit it or comment), one line per question id:\n\n1. **Q1 (P0, Business Objective)** ...",
  "doneWhen": "Every question above (Q1, Q5) has an answer on APP-4827.",
  "unblocks": ["APP-4827"],
  "category": "spike"
}
```

With every required question answered it writes `{"schemaVersion", "issueKey", "ready": true}`
and nothing else: there is no wall to raise. `category` is `spike` because a business decision is
answered knowledge; a project that files walls under another category overrides it.
