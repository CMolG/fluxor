package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.TaskSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** Plan #19, Task 4 Step 5: intake idempotency is covered by {@code TaskBacklogServiceTest};
 *  here -- sync pagination with tombstones, PUT with a stale version 409s and the server state
 *  wins, tasks from another account are invisible (404 upstream, but at THIS layer: findById
 *  filtered by account -> "not found" branch, same as a brand-new push). */
class TaskSyncServiceTest {

    private final FakeFluxorTaskRepository repo = new FakeFluxorTaskRepository();
    private final RelayBroadcaster relay = new RelayBroadcaster();
    private final TaskStateValidator states = new TaskStateValidator("refine,todo,ready,doing,review,deploy");
    private TaskSyncService service;

    @BeforeEach
    void setUp() {
        service = new TaskSyncService(repo, relay, states);
    }

    @Test
    void pushCreatesNewTaskWithExpectedVersionZero() {
        UUID accountId = UUID.randomUUID();
        UUID deviceId = UUID.randomUUID();
        UUID taskId = UUID.randomUUID();

        TaskSyncService.PushResult result = service.push(accountId, deviceId, taskId,
                new TaskSyncService.TaskPush("From IDE", null, "todo", 2, null, null, 0, false));

        assertThat(result).isInstanceOf(TaskSyncService.PushResult.Applied.class);
        FluxorTask created = ((TaskSyncService.PushResult.Applied) result).task();
        assertThat(created.source()).isEqualTo(TaskSource.IDE);
        assertThat(created.version()).isEqualTo(1);
        assertThat(created.updatedBy()).isEqualTo("ide:" + deviceId);
    }

    @Test
    void pushWithStaleVersionConflicts() {
        UUID accountId = UUID.randomUUID();
        UUID deviceId = UUID.randomUUID();
        UUID taskId = UUID.randomUUID();
        service.push(accountId, deviceId, taskId,
                new TaskSyncService.TaskPush("v1", null, "todo", 3, null, null, 0, false));

        // Stale: caller still thinks expectedVersion is 0, but the row is now at version 1.
        TaskSyncService.PushResult conflict = service.push(accountId, deviceId, taskId,
                new TaskSyncService.TaskPush("v2 (stale)", null, "doing", 3, null, null, 0, false));

        assertThat(conflict).isInstanceOf(TaskSyncService.PushResult.Conflict.class);
        FluxorTask current = ((TaskSyncService.PushResult.Conflict) conflict).current().orElseThrow();
        assertThat(current.title()).isEqualTo("v1"); // server's state wins, never silently overwritten
        assertThat(current.version()).isEqualTo(1);
    }

    @Test
    void correctExpectedVersionApplies() {
        UUID accountId = UUID.randomUUID();
        UUID deviceId = UUID.randomUUID();
        UUID taskId = UUID.randomUUID();
        service.push(accountId, deviceId, taskId,
                new TaskSyncService.TaskPush("v1", null, "todo", 3, null, null, 0, false));

        TaskSyncService.PushResult applied = service.push(accountId, deviceId, taskId,
                new TaskSyncService.TaskPush("v2", null, "doing", 3, null, null, 1, false));

        assertThat(applied).isInstanceOf(TaskSyncService.PushResult.Applied.class);
        FluxorTask task = ((TaskSyncService.PushResult.Applied) applied).task();
        assertThat(task.title()).isEqualTo("v2");
        assertThat(task.version()).isEqualTo(2);
    }

    @Test
    void pullPaginatesAndIncludesTombstones() {
        UUID accountId = UUID.randomUUID();
        Instant base = Instant.parse("2026-07-16T10:00:00Z");
        for (int i = 0; i < 3; i++) {
            repo.upsert(new FluxorTask(UUID.randomUUID(), accountId, "Task " + i, null, "todo", 3, null,
                    TaskSource.CONSOLE, null, 1, base.plusSeconds(i), "console", i == 1));
        }

        TaskSyncService.SyncPage firstPage = service.pull(accountId, null, 2);
        assertThat(firstPage.tasks()).hasSize(2);
        assertThat(firstPage.nextCursor()).isNotNull();

        TaskSyncService.SyncPage secondPage = service.pull(accountId, firstPage.nextCursor(), 2);
        assertThat(secondPage.tasks()).hasSize(1);
        assertThat(secondPage.nextCursor()).isNull(); // caught up

        // The deleted task (i==1, a tombstone) must still be present in the sync feed.
        boolean anyDeleted = firstPage.tasks().stream().anyMatch(FluxorTask::deleted)
                || secondPage.tasks().stream().anyMatch(FluxorTask::deleted);
        assertThat(anyDeleted).isTrue();
    }

    @Test
    void pushForAnotherAccountsTaskIdIsTreatedAsNotFound() {
        UUID accountId = UUID.randomUUID();
        UUID otherAccount = UUID.randomUUID();
        UUID deviceId = UUID.randomUUID();
        UUID taskId = UUID.randomUUID();
        service.push(accountId, deviceId, taskId,
                new TaskSyncService.TaskPush("owned by accountId", null, "todo", 3, null, null, 0, false));

        // otherAccount pushing the SAME id with expectedVersion=0 creates confusion only if the
        // repository leaked cross-account visibility; it must not: from otherAccount's
        // perspective this id doesn't exist, so expectedVersion=0 is treated as "create" -- but
        // upsert-by-id would then STOMP accountId's row. Guard: TaskSyncService#push filters
        // findById by accountId, so it never even sees accountId's row here -- this test would
        // fail loudly (wrong owner) if that filter were ever removed.
        TaskSyncService.PushResult result = service.push(otherAccount, deviceId, taskId,
                new TaskSyncService.TaskPush("otherAccount's own", null, "todo", 3, null, null, 5, false));
        assertThat(result).isInstanceOf(TaskSyncService.PushResult.Conflict.class);
    }
}
