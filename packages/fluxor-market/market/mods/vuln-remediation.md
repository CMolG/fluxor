# vuln-remediation: Proven, Quiet Vulnerability Fixes Modifier

When this modifier is active, a vulnerability fix is proven by a test that drives the attack, fixes the cause rather than one input, and discloses nothing about the hole before it is deployed.

## Rules

1. **The exploit's test comes first.** Write a regression test that drives the attack vector. It fails before the fix and passes after, in the same change. Where no test can reach the vector, the card says how it was verified instead.
2. **Name the weakness.** The card states the CWE id, the ASVS requirement the fix satisfies and the severity (CVSS v4.0).
3. **Fix the cause, then the class.** Close the root cause (parameterise, encode, authorize server-side), not one input. The same weakness elsewhere in the touched code is fixed, or opened as its own card.
4. **The card is the only place for the exploit.** Until the fix is deployed, payloads, reproduction steps and the vulnerable path stay on the restricted card. Commits, branch names, pull requests, changelogs and docs name the control, never the hole.
5. **Exploited first.** An entry in the CISA Known Exploited Vulnerabilities Catalog is fixed before anything ranked only by score.
6. **Fix forward to a supported release.** A vendored patch or a suppressed advisory carries a written reason and an expiry date.

## Behavioral Overrides

- Before committing, the agent rereads the commit message and branch name for anything that describes how to exploit the hole, and rewrites it to name the control.
- If a fix conflicts with a feature requirement, the agent reports the conflict and the risk instead of silently dropping either.
- A new finding becomes a new card; it is not folded into this fix.
