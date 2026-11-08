package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.ports.FluxorTaskRepository;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** Shared in-memory fake for {@link TaskBacklogService}/{@link TaskSyncService} unit tests --
 *  same ordering/lookup semantics as {@code JdbcFluxorTaskRepository}. */
final class FakeFluxorTaskRepository implements FluxorTaskRepository {
    private final Map<UUID, FluxorTask> byId = new HashMap<>();

    @Override
    public void upsert(FluxorTask task) {
        byId.put(task.id(), task);
    }

    @Override
    public Optional<FluxorTask> findById(UUID id) {
        return Optional.ofNullable(byId.get(id));
    }

    @Override
    public List<FluxorTask> findByAccount(UUID accountId, boolean includeDeleted) {
        return byId.values().stream()
                .filter(t -> t.accountId().equals(accountId))
                .filter(t -> includeDeleted || !t.deleted())
                .sorted(Comparator.comparing(FluxorTask::updatedAt))
                .toList();
    }

    @Override
    public Optional<FluxorTask> findByExternalRef(UUID accountId, String externalRef) {
        return byId.values().stream()
                .filter(t -> t.accountId().equals(accountId) && externalRef.equals(t.externalRef()))
                .findFirst();
    }

    @Override
    public List<FluxorTask> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit) {
        List<FluxorTask> ordered = new ArrayList<>(byId.values().stream()
                .filter(t -> t.accountId().equals(accountId))
                .sorted(Comparator.comparing(FluxorTask::updatedAt).thenComparing(FluxorTask::id))
                .toList());
        if (sinceUpdatedAt != null) {
            ordered.removeIf(t -> {
                int cmp = t.updatedAt().compareTo(sinceUpdatedAt);
                if (cmp != 0) {
                    return cmp <= 0;
                }
                return sinceId != null && t.id().compareTo(sinceId) <= 0;
            });
        }
        return ordered.size() > limit ? ordered.subList(0, limit) : ordered;
    }
}
