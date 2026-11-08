# Task — Product PRD draft

> CEET cluster: product (`ceet-product-manager`).

Use this prompt verbatim. Save the model's reply under
`evals/results/<run-id>/product-prd-draft/<arm>.md`.

---

Draft a one-page PRD for the following feature. Output Markdown only.

**Feature:** Add two-factor authentication to the admin login flow.

**Background:** the platform has 4,000 admin accounts across 600 customer
organizations. We have had two incidents in the last 18 months where an
admin account was reused with a phished password and an attacker
modified user data. SOC2 auditors flagged the lack of admin 2FA as a
medium-severity finding.

**Constraints:**
- Engineering capacity: 2 backend engineers + 1 frontend engineer for
  ~3 weeks.
- Mobile: not in scope for this iteration.
- Recovery: customers will not accept locking themselves out, so a
  recovery flow is mandatory.

Cover scope, out of scope, success metrics, rollout plan, and risks.
Be concrete. No bullet salad — the PRD must be readable as a decision
document, not a checklist.
