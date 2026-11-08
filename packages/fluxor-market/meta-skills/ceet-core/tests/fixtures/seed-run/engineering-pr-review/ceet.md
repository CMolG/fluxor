# PR review

This rename ships as one shot under load. That is the headline risk.
On a 50M-row table with 4 services and ~120 call sites still reading
`users.email`, an in-place rename plus a unique-index build is
several distinct operations stacked into a single transaction, none
of which are individually safe at this scale. The review walks
through what to break apart.

## Summary

Reject as written. The same outcome (renamed column, unique index,
lower-cased values) is reachable safely via expand-and-contract over
two or three releases. The current diff conflates four operations:
schema rename, value rewrite, unique index build, and application
cutover — each of which has its own blast radius and rollback path.

## Risks

- **Lock contention.** `CREATE UNIQUE INDEX` without `CONCURRENTLY`
  takes an `ACCESS EXCLUSIVE`-equivalent lock during the build on
  most engines. On 50M rows that lock holds for minutes; every
  reader and writer queues. Burns the SLO error budget instantly.
- **Missing dual-write window.** The four other services still write
  `users.email`. After the rename their inserts fail until they are
  redeployed. There is no feature flag gating the rename, so the
  cutover is a service-wide simultaneous deploy — operationally
  unacceptable under a rolling-deploy assumption.
- **Backfill semantics.** `UPDATE users SET primary_email = LOWER(...)`
  rewrites every row in one statement. WAL pressure, replication
  lag, vacuum behavior — none called out. On the test fixture there
  may be `NULL` rows or rows where `LOWER(x) = LOWER(y)` for
  different `x`/`y`; both produce a unique-index build failure
  *after* the column has already been renamed. There is no path
  back from there inside the same transaction.
- **No blast-radius mitigation.** No mention of progressive rollout
  by tenant, no mention of the error budget the team is willing to
  spend, no mention of what alert fires if the migration starts
  burning latency.

## Rollback

The plan has none. Rolling back inside a transaction is fine while
the transaction is live, but as soon as the migration commits the
column name is the schema's source of truth and there is no toggle
to flip traffic back. Required: a feature flag controlling read
paths, dual-write at the model layer until the flag flips, and a
named on-call runbook step that reverts the flag without a deploy.

## Recommendation

Split into three releases:

1. **Expand.** Add `primary_email` alongside `email`. Backfill in
   batches with checkpoints. Build the unique index with
   `CONCURRENTLY`. Write the lower-cased value at the application
   layer behind a flag. Verify replication lag stays under budget.
2. **Dual-write.** Cut all 4 services to write both columns under
   the flag, then cut reads. Observe parity counters for at least a
   release cycle.
3. **Contract.** Drop `email`, drop the dual-write code path, ship
   the unique constraint as the single source of truth.

Each step has its own rollback toggle. The unique index, the
backfill, and the rename are independent operations and must be
reviewed independently.
