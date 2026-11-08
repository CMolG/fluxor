# resilient-backend: Failure-Safe Server Code Modifier

When this modifier is active, server code is written to fail safely: errors are explicit and consumable, outbound calls are bounded, retries cannot duplicate work, and what must change together changes together.

## Rules

1. **HTTP errors are Problem Details.** Every error response is an RFC 9457 Problem Details object with a stable `type` URI per error class, the right status and a `detail` a caller can act on. No stack trace, SQL, host name or other internal reaches the response.
2. **Every outbound call has a timeout.** A call to another service, a store or a third party without an explicit timeout is a defect.
3. **Retry only transient failures, and bounded.** Retries use exponential backoff with jitter and a cap. A client error, a validation failure or a non-idempotent call is never retried.
4. **A repeatable write is idempotent.** Where a client retry or a message redelivery could repeat a write, an idempotency key or a natural key makes the second attempt a no-op.
5. **One transaction around what must change together.** A constraint or validation that guards an invariant is never skipped "for now"; the safe version ships, or nothing does.
6. **Fail loudly.** An error is raised or logged with context and surfaced through rule 1; it is never swallowed.

## Behavioral Overrides

- Before finishing a server change, the agent lists each outbound call it added with its timeout and retry policy, and each write with its idempotency or transaction boundary.
- If a requirement asks to skip a constraint or a transaction, the agent reports the risk and the safe alternative instead of silently choosing either.
- Pre-existing violations are fixed only on the lines the change already touches; the rest are reported.
