package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** In memory, with {@code JdbcFluxorDeviceRepository}'s semantics: revoke is a no-op for another account. */
final class FakeDeviceRepository implements FluxorDeviceRepository {
    private final Map<UUID, FluxorDevice> byId = new HashMap<>();

    @Override
    public void save(FluxorDevice device) {
        byId.put(device.id(), device);
    }

    @Override
    public Optional<FluxorDevice> findById(UUID id) {
        return Optional.ofNullable(byId.get(id));
    }

    @Override
    public Optional<FluxorDevice> findByTokenHash(String tokenHash) {
        return byId.values().stream().filter(d -> d.tokenHash().equals(tokenHash)).findFirst();
    }

    @Override
    public List<FluxorDevice> findByAccount(UUID accountId) {
        return byId.values().stream().filter(d -> d.accountId().equals(accountId)).toList();
    }

    @Override
    public void revoke(UUID id, UUID accountId, Instant revokedAt) {
        FluxorDevice d = byId.get(id);
        if (d != null && d.accountId().equals(accountId) && d.revokedAt() == null) {
            byId.put(id, new FluxorDevice(d.id(), d.accountId(), d.name(), d.tokenHash(), d.createdAt(),
                    d.lastSeenAt(), revokedAt));
        }
    }

    @Override
    public void touchLastSeen(UUID id, Instant lastSeenAt) {
        FluxorDevice d = byId.get(id);
        if (d != null) {
            byId.put(id, new FluxorDevice(d.id(), d.accountId(), d.name(), d.tokenHash(), d.createdAt(),
                    lastSeenAt, d.revokedAt()));
        }
    }
}
