package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.FluxorTask;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FluxorTaskRepository {

    /** Insert-or-full-overwrite by {@code id} -- concurrency (expected-version checks) is decided
     *  by the application layer BEFORE calling this, never here. */
    void upsert(FluxorTask task);

    /** Regardless of account -- callers check ownership themselves and answer 404 (not 403) on a
     *  mismatch, same "never reveal existence" rule as every other manage API in this codebase. */
    Optional<FluxorTask> findById(UUID id);

    List<FluxorTask> findByAccount(UUID accountId, boolean includeDeleted);

    Optional<FluxorTask> findByExternalRef(UUID accountId, String externalRef);

    /** Incremental pull for the IDE ({@code GET /fluxor/v1/sync/tasks?since=}), ordered by
     *  {@code (updated_at, id)} -- includes soft-deleted rows (tombstones). {@code sinceUpdatedAt}
     *  null means "from the beginning". */
    List<FluxorTask> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit);
}
