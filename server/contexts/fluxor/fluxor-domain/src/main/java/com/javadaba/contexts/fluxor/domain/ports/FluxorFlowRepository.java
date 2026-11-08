package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.FluxorFlow;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FluxorFlowRepository {

    /** Insert-or-full-overwrite by {@code id} -- same "concurrency decided by the caller" shape
     *  as {@code FluxorTaskRepository#upsert}. */
    void upsert(FluxorFlow flow);

    /** Overwrites the flow only while it is still at {@code expectedVersion} and belongs to the same
     *  account; {@code false} when another write got there first. The designer's save goes through
     *  here, so two saves from the same read cannot both win (JAVA-163). */
    boolean update(FluxorFlow flow, int expectedVersion);

    Optional<FluxorFlow> findById(UUID id);

    List<FluxorFlow> findByAccount(UUID accountId);

    /** Incremental pull for the IDE ({@code GET /fluxor/v1/sync/flows?since=}): every flow since the
     *  cursor that HAS a definition. A drawing that does not compile yet is left out, because the
     *  IDE needs a document to run (JAVA-163). */
    List<FluxorFlow> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit);

    /** Removes the flow and its runs (their events first). */
    void delete(UUID id);
}
