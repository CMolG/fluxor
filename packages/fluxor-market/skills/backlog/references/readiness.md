# Is the card ready?

Step 5 of the session. A card is ready when every decision below is **answered**: written on the
card (description, a person's comment, an answered wall), or derivable from the code, a recorded
decision or the project's rules, with that source named in the action plan. Anything else is
**open**, and an open business decision is never guessed.

## Always (P0: no safe plan without them)

| Decision | Answered when the card says |
| --- | --- |
| **Objective** | What outcome improves, for whom; what happens if nothing is done. |
| **Scope** | Which users, products, plans or surfaces it covers, and what it leaves out. |
| **Rules** | The conditions, limits, thresholds and deadlines that apply. |
| **Lifecycle** | What happens on success, failure, cancellation, expiry, or while pending. |
| **Acceptance** | The cases that prove it done: success, error, edge, and how anyone sees them. |
| **Compatibility** | When the card changes existing behavior: what happens to current users, clients and stored data. |

## When the card touches it (P1: no safe acceptance without them)

User-facing states and copy · messages (channel, timing, failure) · reporting and events ·
legal, consent, privacy or retention · rollout and rollback trigger · abuse and limits ·
what support must see or do.

## Who answers

- **Technical choices are not questions for a person**: classes, tables, endpoints, libraries. The
  agent infers them from the code and the project's patterns, and the plan says where from.
- **Business decisions are**: what the product does, for whom, and what counts as done. When one
  is open, raise a wall (`requestHuman`): `why` names the open decisions, `steps` are the
  questions (one per decision, with the options you see), `doneWhen` is "each question answered
  on the card", `unblocks` is the card. No action plan is written while the wall stands.
- **Five to ten questions at most**, P0 first. A card that needs more is two cards, or an epic:
  say so on the card instead of asking.

## With the requirements pipeline

When the `jira-agentic-requirements-pipeline` skill is installed, it does the selection: write
the card as its `TicketSnapshot`, run `discovery`, `generate-questions` and `request-human`, and
send the draft it writes as the wall. Its catalog has thirty categories and their P2 questions,
which are never blocking. Once answered, its `resolve-contract` gives the decisions to post on
the card as one comment, and the action plan cites that comment.
