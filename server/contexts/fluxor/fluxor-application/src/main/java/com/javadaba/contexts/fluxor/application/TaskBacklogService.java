package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.TaskSource;
import com.javadaba.contexts.fluxor.domain.ports.FluxorTaskRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Console CRUD (session-gated, plan #19 Task 4 Step 3) + external intake (Task 4 Step 4) for the
 * Fluxor backlog. {@code state} is validated against a CONFIGURABLE allow-list, never a hard enum
 * (see {@link FluxorTask} javadoc) -- {@code javadaba.fluxor.task-states}, default the satellite's
 * current 6 workflow states.
 */
@ApplicationScoped
public class TaskBacklogService {

    private static final int MIN_PRIORITY = 1;
    private static final int MAX_PRIORITY = 5;
    private static final int DEFAULT_PRIORITY = 3;

    private final FluxorTaskRepository tasks;
    private final RelayBroadcaster relay;
    private final TaskStateValidator states;
    private final Clock clock;

    @Inject
    public TaskBacklogService(FluxorTaskRepository tasks, RelayBroadcaster relay, TaskStateValidator states) {
        this(tasks, relay, states, Clock.systemUTC());
    }

    TaskBacklogService(FluxorTaskRepository tasks, RelayBroadcaster relay, TaskStateValidator states, Clock clock) {
        this.tasks = tasks;
        this.relay = relay;
        this.states = states;
        this.clock = clock;
    }

    public List<String> validStates() {
        return states.validStates();
    }

    public FluxorTask create(UUID accountId, String title, String body, Integer priority, String epicRef,
            TaskSource source, String updatedBy) {
        requireTitle(title);
        Instant now = Instant.now(clock);
        FluxorTask task = new FluxorTask(
                UUID.randomUUID(), accountId, title.trim(), body, states.defaultState(), validatePriority(priority),
                epicRef, source, null, 1, now, updatedBy, false);
        tasks.upsert(task);
        publish(task);
        return task;
    }

    /** {@code POST /v1/fluxor-task-intake} (metered, Task 4 Step 4) -- tasks created OUTSIDE
     *  Fluxor. Idempotent by {@code externalRef}: a repeated call with the same ref returns the
     *  existing task unchanged rather than creating a duplicate. */
    public FluxorTask intake(UUID accountId, String title, String body, Integer priority, String epicRef,
            String externalRef) {
        if (externalRef != null && !externalRef.isBlank()) {
            var existing = tasks.findByExternalRef(accountId, externalRef);
            if (existing.isPresent()) {
                return existing.get();
            }
        }
        requireTitle(title);
        Instant now = Instant.now(clock);
        FluxorTask task = new FluxorTask(
                UUID.randomUUID(), accountId, title.trim(), body, states.defaultState(), validatePriority(priority),
                epicRef, TaskSource.API, blankToNull(externalRef), 1, now, "api", false);
        tasks.upsert(task);
        publish(task);
        return task;
    }

    public List<FluxorTask> list(UUID accountId, boolean includeDeleted) {
        return tasks.findByAccount(accountId, includeDeleted);
    }

    public FluxorTask get(UUID accountId, UUID id) {
        return requireOwned(accountId, id);
    }

    public FluxorTask update(UUID accountId, UUID id, String title, String body, String epicRef, String updatedBy) {
        FluxorTask current = requireOwned(accountId, id);
        requireTitle(title);
        FluxorTask updated = new FluxorTask(current.id(), current.accountId(), title.trim(), body, current.state(),
                current.priority(), epicRef, current.source(), current.externalRef(), current.version() + 1,
                Instant.now(clock), updatedBy, false);
        tasks.upsert(updated);
        publish(updated);
        return updated;
    }

    public FluxorTask changeState(UUID accountId, UUID id, String newState, String updatedBy) {
        FluxorTask current = requireOwned(accountId, id);
        String normalized = states.validate(newState);
        FluxorTask updated = withVersionBump(current, current.title(), current.body(), normalized,
                current.priority(), current.epicRef(), updatedBy, current.deleted());
        tasks.upsert(updated);
        publish(updated);
        return updated;
    }

    public FluxorTask changePriority(UUID accountId, UUID id, int priority, String updatedBy) {
        FluxorTask current = requireOwned(accountId, id);
        int validated = validatePriority(priority);
        FluxorTask updated = withVersionBump(current, current.title(), current.body(), current.state(), validated,
                current.epicRef(), updatedBy, current.deleted());
        tasks.upsert(updated);
        publish(updated);
        return updated;
    }

    public void delete(UUID accountId, UUID id, String updatedBy) {
        FluxorTask current = requireOwned(accountId, id);
        FluxorTask deleted = withVersionBump(current, current.title(), current.body(), current.state(),
                current.priority(), current.epicRef(), updatedBy, true);
        tasks.upsert(deleted);
        publish(deleted);
    }

    private FluxorTask withVersionBump(FluxorTask current, String title, String body, String state, int priority,
            String epicRef, String updatedBy, boolean deleted) {
        return new FluxorTask(current.id(), current.accountId(), title, body, state, priority, epicRef,
                current.source(), current.externalRef(), current.version() + 1, Instant.now(clock), updatedBy,
                deleted);
    }

    private FluxorTask requireOwned(UUID accountId, UUID id) {
        return tasks.findById(id)
                .filter(t -> t.accountId().equals(accountId))
                .orElseThrow(() -> new FluxorException("task_not_found", "Task not found: " + id, 404));
    }

    private void requireTitle(String title) {
        if (title == null || title.isBlank()) {
            throw new FluxorException("invalid_title", "'title' is required", 422);
        }
    }

    private int validatePriority(Integer priority) {
        if (priority == null) {
            return DEFAULT_PRIORITY;
        }
        if (priority < MIN_PRIORITY || priority > MAX_PRIORITY) {
            throw new FluxorException("invalid_priority", "'priority' must be between 1 and 5", 422);
        }
        return priority;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private void publish(FluxorTask task) {
        relay.publish(task.accountId(), "task.updated", Map.of(
                "id", task.id().toString(),
                "state", task.state(),
                "priority", task.priority(),
                "deleted", task.deleted(),
                "version", task.version()));
    }
}
