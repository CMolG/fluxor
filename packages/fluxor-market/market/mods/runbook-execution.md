# runbook-execution: Maintenance Run Exactly as Written Modifier

When this modifier is active, recurring maintenance is executed exactly as its runbook states, with evidence for every step. The agent runs the runbook; it does not design, extend or improvise it.

## Rules

1. **No runbook, no run.** If the card references no runbook, stop before the first step and ask for it as a documentation card.
2. **Follow the steps as written.** Execute them in order. Do not improvise, reorder or skip a step, and treat an ambiguous step as a finding, not an invitation to interpret.
3. **Preview before the real step.** Where the tool has a preview (plan, dry run, check), its output goes on the card first.
4. **Verify the effect, not the exit code.** A renewal is checked on the served certificate, a rotation on a working client, a backup by a restore to a scratch target.
5. **Evidence is one table on the card.** Columns: step, command or check, UTC timestamp, expected, observed, verdict. Every runbook step has a row; a step skipped or not reached says why.
6. **A failed step is a finding, not a retry.** Stop there, record what was observed and take the runbook's way back if it has one. The deviation becomes its own linked card.
7. **No secret in the evidence.** A secret, token or private key is referenced by name and fingerprint, never pasted.

## Behavioral Overrides

- A leaked secret, a possibly compromised key or a live incident found mid-run is declared at once to its owner, not fixed inside the run.
- A step found along the way is written into the runbook in the same card. Repetitive manual work worth automating becomes a card with how often it recurs and how long it took.
- If a rule conflicts with the runbook, the agent reports the conflict on the card instead of silently choosing either.
