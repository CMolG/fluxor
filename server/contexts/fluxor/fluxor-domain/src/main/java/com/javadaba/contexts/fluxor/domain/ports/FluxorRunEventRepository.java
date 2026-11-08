package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.FluxorRunEvent;

import java.util.List;
import java.util.UUID;

public interface FluxorRunEventRepository {

    /** Batch-append -- the caller (RunMonitorService) has already validated strict {@code seq}
     *  ordering against {@link #maxSeq} before calling this. */
    void appendAll(List<FluxorRunEvent> events);

    List<FluxorRunEvent> findAfterSeq(UUID runId, int afterSeq);

    /** {@code -1} if the run has no events yet. */
    int maxSeq(UUID runId);
}
