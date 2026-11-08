package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import com.javadaba.contexts.fluxor.domain.ports.FluxorFlowRepository;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

final class FakeFluxorFlowRepository implements FluxorFlowRepository {
    private final Map<UUID, FluxorFlow> byId = new HashMap<>();

    @Override
    public void upsert(FluxorFlow flow) {
        byId.put(flow.id(), flow);
    }

    @Override
    public boolean update(FluxorFlow flow, int expectedVersion) {
        FluxorFlow current = byId.get(flow.id());
        if (current == null || !current.accountId().equals(flow.accountId()) || current.version() != expectedVersion) {
            return false;
        }
        byId.put(flow.id(), flow);
        return true;
    }

    @Override
    public Optional<FluxorFlow> findById(UUID id) {
        return Optional.ofNullable(byId.get(id));
    }

    @Override
    public List<FluxorFlow> findByAccount(UUID accountId) {
        return byId.values().stream().filter(f -> f.accountId().equals(accountId))
                .sorted(Comparator.comparing(FluxorFlow::updatedAt)).toList();
    }

    @Override
    public List<FluxorFlow> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit) {
        List<FluxorFlow> ordered = new ArrayList<>(byId.values().stream()
                .filter(f -> f.accountId().equals(accountId) && f.definition() != null)
                .sorted(Comparator.comparing(FluxorFlow::updatedAt).thenComparing(FluxorFlow::id))
                .toList());
        if (sinceUpdatedAt != null) {
            ordered.removeIf(f -> {
                int cmp = f.updatedAt().compareTo(sinceUpdatedAt);
                if (cmp != 0) {
                    return cmp <= 0;
                }
                return sinceId != null && f.id().compareTo(sinceId) <= 0;
            });
        }
        return ordered.size() > limit ? ordered.subList(0, limit) : ordered;
    }

    @Override
    public void delete(UUID id) {
        byId.remove(id);
    }

    /** Passes every call through, so a test can override one to put another write in its way. */
    static class Delegating implements FluxorFlowRepository {
        private final FluxorFlowRepository target;

        Delegating(FluxorFlowRepository target) {
            this.target = target;
        }

        @Override
        public void upsert(FluxorFlow flow) {
            target.upsert(flow);
        }

        @Override
        public boolean update(FluxorFlow flow, int expectedVersion) {
            return target.update(flow, expectedVersion);
        }

        @Override
        public Optional<FluxorFlow> findById(UUID id) {
            return target.findById(id);
        }

        @Override
        public List<FluxorFlow> findByAccount(UUID accountId) {
            return target.findByAccount(accountId);
        }

        @Override
        public List<FluxorFlow> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit) {
            return target.findSince(accountId, sinceUpdatedAt, sinceId, limit);
        }

        @Override
        public void delete(UUID id) {
            target.delete(id);
        }
    }
}
