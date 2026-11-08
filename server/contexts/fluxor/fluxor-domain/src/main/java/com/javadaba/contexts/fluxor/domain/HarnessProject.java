package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.UUID;

/** A project's harness. {@code revision} goes up by one on every change to its items, so a client
 *  that knows revision N can ask for only what changed after it. */
public record HarnessProject(
        UUID id,
        UUID accountId,
        String name,
        UUID officiumProjectId,
        long revision,
        Instant updatedAt) {
}
