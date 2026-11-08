package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * A backlog task (plan #19, Task 4). {@code state} is deliberately a free string validated at the
 * application layer against a CONFIGURABLE allow-list (the 6 workflow states of the satellite's
 * backlog-bento redesign -- {@code refine, todo, ready, doing, review, deploy}, cited from
 * {@code ../fluxor/fluxor-ide/docs/superpowers/backlog/2026-07-08-backlog-bento-redesign-launchers.md}
 * line 61 -- READ-ONLY reference), NOT a hard enum: the plan explicitly calls out the satellite may
 * still rename them before it ships its own rebranding. {@code version} increments on every write
 * (optimistic concurrency for the device sync PUT, Task 4 Step 2).
 */
public record FluxorTask(
        UUID id,
        UUID accountId,
        String title,
        String body,
        String state,
        int priority,
        String epicRef,
        TaskSource source,
        String externalRef,
        int version,
        Instant updatedAt,
        String updatedBy,
        boolean deleted) {
}
