# PRD — Admin 2FA enrollment

## Problem

Two incidents in the last 18 months traced back to phished admin
credentials reused without a second factor. SOC2 auditors have
flagged the gap. The cost of a third incident is no longer
hypothetical: it is a customer-facing data exposure plus a SOC2
opinion downgrade.

## Scope

This iteration delivers mandatory TOTP-based 2FA for the 4,000 admin
accounts on the web flow. Mandatory means: after the cutover date,
admin login without an enrolled second factor is rejected. Recovery
codes are issued at enrollment and are the only supported recovery
path inside this iteration.

## Out of scope

- Mobile admin flows. The web cutover happens first; mobile follows
  in a separate iteration.
- Customer (non-admin) accounts. Different threat model, different
  willingness-to-pay, different SLA — out of scope deliberately.
- WebAuthn / hardware keys. Worth doing later, but TOTP delivers the
  SOC2 finding faster with smaller surface area.
- SCIM-managed enrollment. Customers using IdP-pushed accounts will
  be handled in a follow-up after we observe the first wave.
- Admin-assisted reset. Recovery codes only in v1, to keep the
  operational surface small.

## Success metrics

- Primary: 100% of admin accounts enrolled by mandatory cutover
  date. Tracked as `admin_2fa_enrollment_ratio`.
- Audit: SOC2 finding closed at next quarterly review. Verification
  artifact agreed with auditor: enrollment ratio query plus the
  admin-rejection-on-missing-2fa log signal.
- Operational: zero customer-organization lockouts in the first
  4 weeks. A "lockout" is an org with no remaining 2FA-enrolled
  admin and no successful recovery within 24 hours.

## Rollout

Three stages, gated by a feature flag at the auth layer:

1. Internal dogfood for one week. Engineering and ops admins enroll.
2. Opt-in for external admins for two weeks. The flag enables the
   2FA path; admins choose when to enroll. We measure friction and
   support load.
3. Mandatory cutover. Flag flips for all admins. Pre-announced two
   weeks ahead, with reminder emails and an in-app banner.

The fail-fast criterion is a 2x increase in
`admin_login_failure_ratio` sustained over 30 minutes during stage
2 or 3. The on-call playbook flips the flag back without a deploy.

## Risks

- **Adoption.** Some admins will refuse to enroll. The mitigation is
  a hard cutover date with named executive sponsorship; without
  that, the rollout drags and the SOC2 finding stays open.
- **Lockout.** If recovery codes are misplaced, the customer loses
  the only path back. We mitigate by requiring recovery codes to be
  generated at enrollment, displayed once, and acknowledged with a
  checkbox. Admin-assisted reset is the v2 mitigation.
- **Recovery-as-bypass.** A recovery code is functionally a second
  password; if attackers obtain it, the entire feature is moot. We
  rate-limit recovery attempts, require a verification email, and
  log every recovery to the audit trail the auditor consumes.

## Capacity

Three weeks with 2 backend + 1 frontend. Backend implements TOTP
verification, recovery codes, and the audit signal; frontend
implements the enrollment screen and the recovery flow. No work in
flight blocks this; the auth team owns the relevant code path.
