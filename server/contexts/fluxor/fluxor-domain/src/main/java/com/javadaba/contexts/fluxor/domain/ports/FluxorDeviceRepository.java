package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FluxorDeviceRepository {

    void save(FluxorDevice device);

    Optional<FluxorDevice> findById(UUID id);

    Optional<FluxorDevice> findByTokenHash(String tokenHash);

    List<FluxorDevice> findByAccount(UUID accountId);

    /** No-op if the device does not belong to {@code accountId} (never reveal existence). */
    void revoke(UUID id, UUID accountId, Instant revokedAt);

    /** Throttled by the caller to ~1/min per device -- see {@code FluxorDeviceAuthFilter}. */
    void touchLastSeen(UUID id, Instant lastSeenAt);
}
