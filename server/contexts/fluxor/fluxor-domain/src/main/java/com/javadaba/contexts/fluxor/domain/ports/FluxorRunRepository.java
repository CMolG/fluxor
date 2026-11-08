package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.FluxorRun;
import com.javadaba.contexts.fluxor.domain.RunStatus;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FluxorRunRepository {

    void save(FluxorRun run);

    /** No-op if the run is already terminal -- {@code RunMonitorService#close} enforces
     *  immutability, this only persists. */
    void updateStatus(FluxorRun run);

    Optional<FluxorRun> findById(UUID id);

    List<FluxorRun> findByAccount(UUID accountId, UUID flowId, RunStatus status);
}
