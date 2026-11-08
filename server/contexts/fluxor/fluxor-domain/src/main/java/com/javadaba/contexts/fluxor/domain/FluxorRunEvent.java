package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/** A single run event (plan #19, Task 5) -- {@code type} is one of {@code step-started, step-
 *  output, step-passed, step-failed, metric} (documented, not enforced -- "free-form but
 *  documented types" per the plan). {@code seq} is strictly increasing per run; out-of-order events
 *  are rejected (see {@code RunMonitorService}). {@code payload} is capped at 8KB (no file
 *  contents). */
public record FluxorRunEvent(UUID runId, int seq, String stepId, String type, Map<String, Object> payload, Instant at) {
}
