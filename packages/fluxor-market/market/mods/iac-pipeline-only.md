# iac-pipeline-only: Infrastructure as Code, Applied by the Pipeline Modifier

When this modifier is active, an environment changes only through reviewed code that the pipeline applies. The repository is the environment: what is not in code does not exist.

## Rules

1. **Declared in version control.** Every resource, pipeline and configuration the change adds or alters is declared in code. Nothing is created or edited in an environment by hand.
2. **Plan before apply, on the card.** The tool's preview output (plan, diff, dry run) is attached to the card before the change is applied.
3. **The pipeline is the only hand.** Nothing is applied from a laptop. A step the pipeline cannot run yet is automated first, not worked around.
4. **Drift is a defect.** A difference between code and environment is fixed in the repository. An emergency manual change is recorded and back-ported to code in the same card.
5. **Pinned and promoted.** Tool, action and dependency versions are pinned. The same built artifact is promoted between environments; it is never rebuilt per environment.
6. **Least privilege, short-lived.** Pipeline jobs run with the narrowest credentials that work, and the configuration lives in the environment, not in the build.
7. **Every change names its way back.** Either revert and reconcile, or the irreversible step and its forward-fix are written before it runs. The rollback was exercised, or the card says why it could not be.

## Behavioral Overrides

- Before applying, the agent states in one line what changes and how it is undone.
- If the only way to meet a requirement is a manual change, the agent reports the conflict and the code that would replace it instead of making the change.
- Pre-existing drift is reported, not repaired, unless the change already touches it.
