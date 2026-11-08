package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorRun;
import com.javadaba.contexts.fluxor.domain.FluxorRunEvent;
import com.javadaba.contexts.fluxor.domain.RunStatus;
import com.javadaba.contexts.fluxor.domain.ports.FluxorRunEventRepository;
import com.javadaba.contexts.fluxor.domain.ports.FluxorRunRepository;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

final class FakeFluxorRunRepositories {

    private FakeFluxorRunRepositories() {
    }

    static final class Runs implements FluxorRunRepository {
        private final Map<UUID, FluxorRun> byId = new HashMap<>();

        @Override
        public void save(FluxorRun run) {
            byId.put(run.id(), run);
        }

        @Override
        public void updateStatus(FluxorRun run) {
            byId.put(run.id(), run);
        }

        @Override
        public Optional<FluxorRun> findById(UUID id) {
            return Optional.ofNullable(byId.get(id));
        }

        @Override
        public List<FluxorRun> findByAccount(UUID accountId, UUID flowId, RunStatus status) {
            return byId.values().stream()
                    .filter(r -> r.accountId().equals(accountId))
                    .filter(r -> flowId == null || flowId.equals(r.flowId()))
                    .filter(r -> status == null || status == r.status())
                    .sorted(Comparator.comparing(FluxorRun::startedAt))
                    .toList();
        }
    }

    static final class Events implements FluxorRunEventRepository {
        private final List<FluxorRunEvent> all = new ArrayList<>();

        @Override
        public void appendAll(List<FluxorRunEvent> events) {
            all.addAll(events);
        }

        @Override
        public List<FluxorRunEvent> findAfterSeq(UUID runId, int afterSeq) {
            return all.stream().filter(e -> e.runId().equals(runId) && e.seq() > afterSeq)
                    .sorted(Comparator.comparingInt(FluxorRunEvent::seq)).toList();
        }

        @Override
        public int maxSeq(UUID runId) {
            return all.stream().filter(e -> e.runId().equals(runId)).mapToInt(FluxorRunEvent::seq).max().orElse(-1);
        }
    }
}
