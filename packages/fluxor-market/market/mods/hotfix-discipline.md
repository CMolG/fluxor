# hotfix-discipline: Smallest Safe Change to Restore Production Modifier

When this modifier is active, the card is a live production problem. Service is restored by the smallest safe change, one variable at a time, and the repair of the root cause is handed to a follow-up card.

## Rules

1. **Mitigate first.** A rollback to the last good revision or a kill switch is tried before any diff. The root cause comes second.
2. **One variable at a time.** Never apply two changes at once. Read the golden signals (latency, traffic, errors, saturation) before and after each change, and record the change, the signals and the way back.
3. **Branch from what production runs.** Cut the fix from the release tag production runs where the project tags, otherwise from the revision production reports (a version endpoint, an image digest, a deploy record), never from an unverified tip. Release it as PATCH+1 of that version.
4. **The diff restores service and nothing else.** No refactor, cleanup or unrelated fix. Each of those becomes its own card.
5. **Keep a UTC timeline on the card.** Detection, each change and recovery carry a timestamp.
6. **Hand over the root cause before leaving.** Open the follow-up card (bug or regression), linked, with the timeline, impact, mitigation and what was ruled out. Open the postmortem with its action items as cards.
7. **Touch production only through the project's declared path.** Where the project forbids an agent opening access, work through the session a person opened or hand them the exact command. A secret never appears on the card.

## Behavioral Overrides

- A security event is contained without wiping logs, images or state, and is handed to the security owner with its evidence.
- Evidence outranks intuition: every mitigation cites the signal that justified it and the signal that confirmed it.
- If a rule conflicts with restoring service, the agent reports the conflict on the card instead of silently dropping either.
