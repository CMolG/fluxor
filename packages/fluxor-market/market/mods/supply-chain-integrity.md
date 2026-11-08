# supply-chain-integrity: Verifiable Builds & Dependencies Modifier

When this modifier is active, what is built and deployed can be verified: its provenance is checked, its dependencies are inventoried and free of known exploited flaws, and no secret travels with it.

## Rules

1. **Provenance is verified before deploy.** Every artifact deployed carries signed build provenance that the pipeline verifies, and is referenced by digest, never by a mutable tag.
2. **A dependency change regenerates the SBOM.** Adding, removing or upgrading a dependency or a base image updates the SBOM in the same change.
3. **No known exploited vulnerability ships.** New versions carry no entry in the CISA Known Exploited Vulnerabilities Catalog. A suppressed advisory carries a written reason and an expiry date.
4. **No secret in the repository, logs or image layers.** The pipeline scans for secrets. An exposed secret is rotated and revoked, not only deleted from history.
5. **Hardening is scanned, deviations are written.** The hardening benchmark the project declares for each platform touched runs on what changed. Every deviation is recorded with its reason, and images are minimal and run as non-root.
6. **Third-party signatures are checked.** Where the publisher signs an artifact, the signature is verified before use.

## Behavioral Overrides

- When a rule cannot be met (a publisher that does not sign, a scanner the project does not run), the agent reports it with the reason instead of silently skipping the rule.
- A secret found while working is reported without being printed: referenced by name and fingerprint only.
- Pre-existing findings are fixed only on the lines the change already touches; the rest are reported.
