# Full Business Question Catalog

Use this catalog to generate **non-technical** business questions from Jira tickets.

## Base filtering rule

Ask business questions only when the answer changes one or more of:

- user behavior
- product behavior
- support/backoffice operations
- legal/compliance/privacy obligations
- risk/fraud controls
- pricing/billing/plan behavior
- communications and messaging
- reporting/auditability/traceability
- rollout/migration/rollback
- UX/copy/acceptance criteria

Do **not** ask business users about implementation details (classes, methods, tables, endpoints, frameworks, libraries, architecture patterns, cache/queue internals), unless they have direct visible business impact.

---

## 1) Business Objective
- What business problem are we solving?
- What outcome should improve?
- What metric should move?
- What happens if we do nothing?

## 2) Functional Scope
- Which users/countries/channels/plans/partners are in scope?
- Does it apply to existing operations or only new ones?
- What is explicitly out of scope?

## 3) Actors & Permissions
- Who can trigger, view, override, retry, cancel, or unlock?
- How do permissions differ across user/support/admin/partner?
- What must be auditable by actor?

## 4) Business Rules
- What conditions allow or block the action?
- Which limits/thresholds/expirations/retries apply?
- What happens on duplicate/repeated/concurrent operations?

## 5) State Lifecycle
- Which states exist?
- Which transitions are allowed/blocked?
- What happens on success/error/timeout/expiration/cancelation?

## 6) Edge Cases
- What happens on double submit, refresh, reconnect, multi-device, late callback?
- What happens if data changes mid-flow?

## 7) User Experience
- What does user see before/during/after?
- Which copy is required for success/error/blocked/expired?
- Is retry/cancel/help/countdown needed?

## 8) Messages & Communications
- Which channels are required (email/SMS/push/WhatsApp/in-app)?
- When should communication be sent?
- What happens if communication fails?

## 9) Support & Backoffice
- What must support see and do?
- Are manual actions allowed (retry/cancel/unlock/override)?
- Which reason/history fields are mandatory?

## 10) Risk, Fraud & Abuse
- What is suspicious behavior?
- What limits apply (user/device/IP/account/time window)?
- What happens when risk limits are exceeded?

## 11) Legal, Compliance & Privacy
- Are consent/disclaimer/retention/audit requirements involved?
- What personal/sensitive data is processed?
- Who can access it and for how long?

## 12) Pricing, Billing & Monetization
- Is feature available across all plans?
- Does it affect credits, subscriptions, trial, refund, upsell?
- Is there additional charge or commercial limit?

## 13) Activation & Functional Configuration
- Is feature always on or configurable?
- Is activation segmented by country/user/channel/partner/percentage?
- What is default behavior if config is missing?

## 14) Rollout & Transition
- Is rollout immediate or progressive?
- Is there beta/coexistence with legacy flow?
- What triggers rollback and who approves?

## 15) Compatibility & Backward Compatibility
- What happens for old app versions and old integrations?
- Must legacy behavior remain? For how long?
- Is there minimum supported version?

## 16) Data & Functional Reporting
- What data/events must be stored and visible?
- Which KPI/report/dashboard is affected?
- Which segmentation is required (country/plan/channel/partner)?

## 17) Auditability & Traceability
- Who did what, when, from where, and why?
- Which sequence must be reconstructable?
- What retention is required?

## 18) Functional Error Handling
- Which errors are recoverable vs blocking?
- Which errors require support/manual operation?
- Which message must be shown for each case?

## 19) Business External Dependencies
- Is there dependency on provider/partner/legal/support/operations?
- What happens when dependency is unavailable?
- Is fallback continuation allowed?

## 20) Internationalization & Localization
- Are behavior/texts/formats/timezones country or language-specific?
- Who validates translations?
- Are temporary texts allowed?

## 21) Accessibility & Usability
- Are there accessibility constraints (screen reader, keyboard, contrast)?
- Is mobile/small-screen usability required?
- What level of explanatory guidance is required?

## 22) Perceived Performance
- How long can user wait before frustration?
- Should loading/progress/timeout be visible?
- Is background completion accepted?

## 23) Functional Security
- Is additional confirmation/authentication required?
- Should behavior vary by risk level?
- Is masking/notification/revocation required?

## 24) Data Quality
- Which fields are mandatory and valid?
- How to handle duplicates and conflicts?
- Should invalid data provide corrective guidance?

## 25) Priority, Severity & Criticality
- If it fails, what is business severity?
- Should support/on-call be pre-informed?
- Is low-traffic release window required?

## 26) Reversibility & Rollback
- Can feature be disabled safely?
- What happens to in-flight operations?
- Who decides rollback and on which threshold?

## 27) Migration & Existing Data
- Are existing users/operations/historical records affected?
- Is backfill/cleanup/transformation required?
- Are exceptions expected and how handled?

## 28) Out of Scope
- What is explicitly not part of this ticket?
- What is postponed to next phase?

## 29) Acceptance Criteria
- What minimum success/error/edge cases must QA validate?
- Who provides functional approval?
- What evidence is required for completion?

## 30) Rapid Decision
- Mandatory vs optional?
- Visible vs hidden?
- Automatic vs manual?
- Immediate vs deferred?
- Rollout now vs later phase?

---

## Question generation schema

For every generated question include:

```json
{
  "category": "Business Rules",
  "question": "How many failed attempts are allowed before blocking the operation?",
  "whyItMatters": "Defines risk policy and avoids product assumptions.",
  "suggestedAnswers": ["3", "5", "10", "Unlimited", "Other"],
  "required": true,
  "blocksImplementation": true,
  "defaultIfUnanswered": null,
  "businessImpact": "risk",
  "affectedActors": ["user", "support"],
  "relatedAcceptanceCriteria": true
}
```

## Prioritization

- **P0 (blocks implementation):** cannot implement safely without answer.
- **P1 (blocks acceptance):** needed for QA/support/operational readiness.
- **P2 (solution quality):** valuable but not mandatory for first base branch.
  Never required and never blocking; each carries the default assumed while it
  is unanswered (`defaultIfUnanswered`).
- **P3 (future phase):** detect and store as optional future decisions.

## Output policy

1. Detect all potentially affected categories.
2. Draft broad internal question set.
3. Deduplicate and remove inferable technical questions.
4. Prioritize P0/P1 first.
5. Publish **5-10 required questions max**.
6. Add optional collapsed future decisions list: the P2 templates whose category the
   ticket touches (it is in `detectedCategories`), then every P3 template.

## Templates the CLI ships

`scripts/jira_pipeline_cli.py` (`question_templates()`) selects from these templates; a test
keeps this table and the script in sync. P0 and P1 templates fill the required questions (`Q<n>`):
`BO-1`, `FS-1`, `BR-1` and `SL-1` are the baseline, the others are picked when their signals
match the ticket's missing decisions. P2 and P3 templates are optional (`O<n>`) and are asked only
with `collect-input --include-optional`. The contract field each category resolves to is listed
in `contracts.md`.

| ID | Priority | Category | Question |
|---|---|---|---|
| AC-1 | P0 | Acceptance Criteria | What minimum success, error, permission, compatibility, and edge cases must QA validate to accept this ticket? |
| BO-1 | P0 | Business Objective | What specific business outcome should improve after this change? |
| BR-1 | P0 | Business Rules | What exact business rules, limits, thresholds, deadlines, or conditions must apply? |
| CP-1 | P0 | Compatibility & Backward Compatibility | What should happen for old clients, old app versions, existing integrations, or consumers that do not support the new behavior? |
| FS-1 | P0 | Functional Scope | Which users, countries, channels, plans, products, or partners are in scope? |
| SL-1 | P0 | State Lifecycle | What should happen when the operation succeeds, fails, is cancelled, expires, or remains pending? |
| CM-1 | P1 | Messages & Communications | Which communication channels must be used, when should they be triggered, and what happens if communication fails? |
| DR-1 | P1 | Data & Functional Reporting | Which business events, statuses, metrics, or reports must be tracked? |
| LC-1 | P1 | Legal, Compliance & Privacy | Are there legal, compliance, privacy, consent, retention, or audit obligations for this flow? |
| RL-1 | P1 | Rollout & Transition | Should rollout be immediate or progressive, and what business condition should trigger rollback? |
| RS-1 | P1 | Risk, Fraud & Abuse | What behavior should be considered suspicious or abusive, and what action should be taken when risk limits are exceeded? |
| SP-1 | P1 | Support & Backoffice | What must support or backoffice be able to view, retry, cancel, override, unlock, or audit? |
| UX-1 | P1 | User Experience | What user-facing messages or screens are required for success, error, pending, blocked, and unavailable states? |
| AF-1 | P2 | Activation & Functional Configuration | Is the behavior always on or configurable, by whom, and what is the default when no configuration exists? |
| AP-1 | P2 | Actors & Permissions | Who can trigger, view, override, or cancel this operation, and does it differ for users, support, admins, and partners? |
| AT-1 | P2 | Auditability & Traceability | Who did what, when, and why: which part of the sequence must be reconstructable later, and for how long? |
| AX-1 | P2 | Accessibility & Usability | Are there accessibility or small-screen requirements beyond the product's usual standard? |
| CR-1 | P2 | Priority, Severity & Criticality | If this fails in production, how severe is it for the business, and should support or on-call be told before release? |
| DQ-1 | P2 | Data Quality | Which inputs are mandatory, how are duplicates or conflicts resolved, and should invalid input show corrective guidance? |
| EC-1 | P2 | Edge Cases | What should happen on a double submit, a refresh, a second device, or when the underlying data changes mid-flow? |
| ED-1 | P2 | Business External Dependencies | Does this depend on a provider, partner, or another team, and what happens while that dependency is unavailable? |
| FE-1 | P2 | Functional Error Handling | Which errors can the user recover from alone, which need support, and what should each one say? |
| FX-1 | P2 | Functional Security | Does this need extra confirmation, re-authentication, masking of sensitive data, or a security notification? |
| IL-1 | P2 | Internationalization & Localization | Do texts, formats, currencies, or time zones vary by country or language, and who validates translations? |
| MG-1 | P2 | Migration & Existing Data | Are existing users, operations, or historical records affected, and do they need a backfill, a cleanup, or an exception? |
| PB-1 | P2 | Pricing, Billing & Monetization | Does this change affect plans, credits, trials, refunds, or charges, or add a commercial limit? |
| PP-1 | P2 | Perceived Performance | How long can the user wait, should progress be visible, and may the operation finish in the background? |
| RV-1 | P2 | Reversibility & Rollback | Can the behavior be switched off safely, what happens to operations in flight, and who decides to roll back? |
| PZ-1 | P3 | Out of Scope | What is explicitly out of scope for this ticket and postponed to a future phase? |
