package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/** A flow execution, run by the IDE and mirrored here (plan #19, Task 5) -- the server never
 *  executes; {@code startedAt}/{@code finishedAt}/{@code summary} are what the device reports. */
public record FluxorRun(
        UUID id,
        UUID accountId,
        UUID flowId,
        UUID deviceId,
        RunStatus status,
        Instant startedAt,
        Instant finishedAt,
        Map<String, Object> summary) {
}
