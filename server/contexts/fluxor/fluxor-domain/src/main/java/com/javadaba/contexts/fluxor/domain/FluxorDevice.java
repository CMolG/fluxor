package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * A Fluxor IDE installation paired to a Javadaba account (plan
 * 2026-07-09-fluxor-bridge-servidor-y-landing.md, #19, Task 2). {@code tokenHash} is the sha-256
 * hex digest of the bearer device token ({@code jdbx_device_<secret>}, see {@code
 * FluxorDeviceAuthFilter}) -- the plaintext value only ever exists at issuance time (returned once
 * by {@code GET /fluxor/v1/pairings/{pollToken}} on the claimed transition), never persisted.
 *
 * <p>{@code signInFamily} is the native app's sign-in that claimed the pairing, which the device ends
 * with (JAVA-1425); null when a browser's session or an enrollment code made it.
 */
public record FluxorDevice(
        UUID id,
        UUID accountId,
        String name,
        String tokenHash,
        Instant createdAt,
        Instant lastSeenAt,
        Instant revokedAt,
        UUID signInFamily) {

    public FluxorDevice(UUID id, UUID accountId, String name, String tokenHash, Instant createdAt,
            Instant lastSeenAt, Instant revokedAt) {
        this(id, accountId, name, tokenHash, createdAt, lastSeenAt, revokedAt, null);
    }

    public boolean isRevoked() {
        return revokedAt != null;
    }
}
