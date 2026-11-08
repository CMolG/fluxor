package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * A flow snapshot (plan #19, Task 5) in the canonical interchange format -- {@code definition} IS
 * the {@code fluxor-flow} document (see {@link FlowDefinitionValidator}): {@code steps[]} with
 * {@code dependsOn[]}, flattened system prompt. A "contract of DATA, not of EXECUTION" (same
 * pattern as {@code SduiDocument}, #6) -- the server never runs a flow, only stores/validates/
 * relays it; the IDE is the only runtime.
 *
 * <p>{@code canvas} is the designer's drawing (JAVA-163, {@link FlowCanvas}); null for a flow that
 * never went through the designer, which {@link FlowLayout} lays out on read. {@code definition}
 * is null while that drawing does not compile ({@link FlowCompiler}); never both null.
 */
public record FluxorFlow(
        UUID id,
        UUID accountId,
        String name,
        Map<String, Object> definition,
        Map<String, Object> canvas,
        FlowOrigin origin,
        FlowStatus status,
        int version,
        Instant updatedAt) {
}
