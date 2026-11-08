package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.TaskSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** FAIL-first per plan Task 4 Step 1: state validated against the configurable allow-list,
 *  priority 1-5, soft-delete, version increments on every write. */
class TaskBacklogServiceTest {

    private final FakeFluxorTaskRepository repo = new FakeFluxorTaskRepository();
    private final RelayBroadcaster relay = new RelayBroadcaster();
    private final TaskStateValidator states = new TaskStateValidator("refine,todo,ready,doing,review,deploy");
    private TaskBacklogService service;

    @BeforeEach
    void setUp() {
        service = new TaskBacklogService(repo, relay, states);
    }

    @Test
    void createDefaultsToFirstConfiguredStateAndVersionOne() {
        UUID accountId = UUID.randomUUID();
        FluxorTask task = service.create(accountId, "Fix the bug", null, null, null, TaskSource.CONSOLE, "console");
        assertThat(task.state()).isEqualTo("refine");
        assertThat(task.priority()).isEqualTo(3);
        assertThat(task.version()).isEqualTo(1);
        assertThat(task.deleted()).isFalse();
    }

    @Test
    void blankTitleIsRejected() {
        assertThatThrownBy(() -> service.create(UUID.randomUUID(), "  ", null, null, null, TaskSource.CONSOLE, "x"))
                .isInstanceOf(FluxorException.class);
    }

    @Test
    void priorityOutOfRangeIsRejected() {
        UUID accountId = UUID.randomUUID();
        assertThatThrownBy(() -> service.create(accountId, "Task", null, 6, null, TaskSource.CONSOLE, "x"))
                .isInstanceOf(FluxorException.class);
        assertThatThrownBy(() -> service.create(accountId, "Task", null, 0, null, TaskSource.CONSOLE, "x"))
                .isInstanceOf(FluxorException.class);
    }

    @Test
    void stateTransitionValidatesAgainstAllowList() {
        UUID accountId = UUID.randomUUID();
        FluxorTask task = service.create(accountId, "Task", null, null, null, TaskSource.CONSOLE, "x");

        assertThatThrownBy(() -> service.changeState(accountId, task.id(), "not-a-real-state", "x"))
                .isInstanceOf(FluxorException.class);

        FluxorTask moved = service.changeState(accountId, task.id(), "doing", "x");
        assertThat(moved.state()).isEqualTo("doing");
        assertThat(moved.version()).isEqualTo(2);
    }

    @Test
    void deleteIsSoftAndBumpsVersion() {
        UUID accountId = UUID.randomUUID();
        FluxorTask task = service.create(accountId, "Task", null, null, null, TaskSource.CONSOLE, "x");
        service.delete(accountId, task.id(), "x");

        assertThat(service.list(accountId, false)).isEmpty();
        List<FluxorTask> withDeleted = service.list(accountId, true);
        assertThat(withDeleted).hasSize(1);
        assertThat(withDeleted.get(0).deleted()).isTrue();
        assertThat(withDeleted.get(0).version()).isEqualTo(2);
    }

    @Test
    void tasksFromAnotherAccountAreInvisible() {
        UUID accountId = UUID.randomUUID();
        UUID otherAccount = UUID.randomUUID();
        FluxorTask task = service.create(accountId, "Task", null, null, null, TaskSource.CONSOLE, "x");

        assertThatThrownBy(() -> service.get(otherAccount, task.id())).isInstanceOf(FluxorException.class);
    }

    @Test
    void intakeIsIdempotentByExternalRef() {
        UUID accountId = UUID.randomUUID();
        FluxorTask first = service.intake(accountId, "From CI", "build failed", 4, "epic-1", "ci-run-42");
        FluxorTask second = service.intake(accountId, "From CI (different title, ignored)", null, 1, null, "ci-run-42");

        assertThat(second.id()).isEqualTo(first.id());
        assertThat(second.title()).isEqualTo("From CI"); // unchanged, not overwritten by the "duplicate" call
        assertThat(service.list(accountId, false)).hasSize(1);
        assertThat(first.source()).isEqualTo(TaskSource.API);
    }
}
