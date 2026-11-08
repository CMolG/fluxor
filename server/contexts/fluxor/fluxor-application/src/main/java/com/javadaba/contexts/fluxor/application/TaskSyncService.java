package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.TaskSource;
import com.javadaba.contexts.fluxor.domain.ports.FluxorTaskRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Device-token-gated incremental sync (plan #19, Task 4 Step 2): {@code GET
 * /fluxor/v1/sync/tasks?since=} (pull, cursor pagination + tombstones) and {@code PUT
 * /fluxor/v1/sync/tasks/{id}} (push, optimistic concurrency -- "if the server is ahead ->
 * 409 + current state (LWW resolved in favor of the SERVER; the IDE re-reads and decides)").
 */
@ApplicationScoped
public class TaskSyncService {

    private static final int NEW_TASK_EXPECTED_VERSION = 0;

    private final FluxorTaskRepository tasks;
    private final RelayBroadcaster relay;
    private final TaskStateValidator states;
    private final Clock clock;

    @Inject
    public TaskSyncService(FluxorTaskRepository tasks, RelayBroadcaster relay, TaskStateValidator states) {
        this(tasks, relay, states, Clock.systemUTC());
    }

    TaskSyncService(FluxorTaskRepository tasks, RelayBroadcaster relay, TaskStateValidator states, Clock clock) {
        this.tasks = tasks;
        this.relay = relay;
        this.states = states;
        this.clock = clock;
    }

    public SyncPage pull(UUID accountId, String sinceCursor, int limit) {
        Optional<SyncCursor.Decoded> since = SyncCursor.decode(sinceCursor);
        List<FluxorTask> page = tasks.findSince(
                accountId,
                since.map(SyncCursor.Decoded::updatedAt).orElse(null),
                since.map(SyncCursor.Decoded::id).orElse(null),
                limit);
        String nextCursor = page.size() < limit || page.isEmpty()
                ? null
                : SyncCursor.encode(page.get(page.size() - 1).updatedAt(), page.get(page.size() - 1).id());
        return new SyncPage(page, nextCursor);
    }

    public PushResult push(UUID accountId, UUID deviceId, UUID id, TaskPush push) {
        Optional<FluxorTask> existingOpt = tasks.findById(id).filter(t -> t.accountId().equals(accountId));
        String updatedBy = "ide:" + deviceId;
        Instant now = Instant.now(clock);

        if (existingOpt.isPresent()) {
            FluxorTask existing = existingOpt.get();
            if (existing.version() != push.expectedVersion()) {
                return PushResult.conflict(existing);
            }
            FluxorTask updated = new FluxorTask(
                    id, accountId, push.title(), push.body(), states.validate(push.state()), push.priority(),
                    push.epicRef(), existing.source(), push.externalRef(), existing.version() + 1, now, updatedBy,
                    push.deleted());
            tasks.upsert(updated);
            publish(updated);
            return PushResult.applied(updated);
        }

        if (push.expectedVersion() != NEW_TASK_EXPECTED_VERSION) {
            // The IDE thinks a task exists at some version, but the server has no such row at all
            // (deleted out from under it, or it never existed) -- surfaced as a conflict with no
            // "current" state to hand back (there is none), same "server wins" resolution.
            return PushResult.conflict(null);
        }
        FluxorTask created = new FluxorTask(
                id, accountId, push.title(), push.body(), states.validate(push.state()), push.priority(),
                push.epicRef(), TaskSource.IDE, push.externalRef(), 1, now, updatedBy, push.deleted());
        tasks.upsert(created);
        publish(created);
        return PushResult.applied(created);
    }

    private void publish(FluxorTask task) {
        relay.publish(task.accountId(), "task.updated", Map.of(
                "id", task.id().toString(),
                "state", task.state(),
                "priority", task.priority(),
                "deleted", task.deleted(),
                "version", task.version()));
    }

    public record SyncPage(List<FluxorTask> tasks, String nextCursor) {
    }

    /** Full-replace push payload -- {@code state} is validated against {@link TaskStateValidator}
     *  just like the console. */
    public record TaskPush(String title, String body, String state, int priority, String epicRef,
            String externalRef, int expectedVersion, boolean deleted) {
    }

    public sealed interface PushResult permits PushResult.Applied, PushResult.Conflict {
        static PushResult applied(FluxorTask task) {
            return new Applied(task);
        }

        static PushResult conflict(FluxorTask current) {
            return new Conflict(Optional.ofNullable(current));
        }

        record Applied(FluxorTask task) implements PushResult {
        }

        record Conflict(Optional<FluxorTask> current) implements PushResult {
        }
    }
}
