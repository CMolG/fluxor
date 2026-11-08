package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.util.LinkedHashSet;
import java.util.List;

/**
 * Validates {@code fluxor_task.state} against a CONFIGURABLE allow-list -- shared by {@link
 * TaskBacklogService} (console CRUD) and {@link TaskSyncService} (IDE push), so the two never
 * drift out of sync on what a valid state is. {@code javadaba.fluxor.task-states}, default the
 * satellite's current 6 workflow states ({@code refine, todo, ready, doing, review, deploy} --
 * cited from
 * {@code ../fluxor/fluxor-ide/docs/superpowers/backlog/2026-07-08-backlog-bento-redesign-launchers.md}
 * line 61, READ-ONLY reference). Deliberately NOT a hard enum -- see {@code FluxorTask} javadoc.
 */
@ApplicationScoped
public class TaskStateValidator {

    private final List<String> orderedStates;

    @Inject
    public TaskStateValidator(
            @ConfigProperty(name = "javadaba.fluxor.task-states", defaultValue = "refine,todo,ready,doing,review,deploy") String taskStatesCsv) {
        this.orderedStates = List.copyOf(new LinkedHashSet<>(List.of(taskStatesCsv.split(","))).stream()
                .map(String::trim).filter(s -> !s.isEmpty()).toList());
    }

    public List<String> validStates() {
        return orderedStates;
    }

    /** First configured state -- used as the default for newly-created tasks. */
    public String defaultState() {
        return orderedStates.isEmpty() ? "backlog" : orderedStates.get(0);
    }

    public String validate(String state) {
        if (state == null || !orderedStates.contains(state)) {
            throw new FluxorException("invalid_state", "'state' must be one of " + orderedStates, 422);
        }
        return state;
    }
}
