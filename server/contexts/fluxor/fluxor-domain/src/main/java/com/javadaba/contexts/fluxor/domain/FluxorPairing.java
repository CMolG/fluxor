package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * A one-time QR/PIN pairing challenge (plan #19, Task 2), server-side port of the local bridge's
 * {@code auth.ts} challenge: TTL 120s, single-use. Unlike the local single-instance in-memory
 * design (one global challenge compared in-process), this is one row per concurrently-pairing IDE
 * installation, looked up by the sha-256 hash of the presented credential -- {@code
 * pairingTokenHash}/{@code pollTokenHash} are unique (24 random bytes, effectively unguessable, so
 * an exact-hash DB lookup IS the "single use" check: a wrong guess simply matches no row). {@code
 * pinHash} is NOT unique (a 6-digit PIN has only 1e6 values; two concurrently pending pairings can
 * collide) -- {@link com.javadaba.contexts.fluxor.application.DevicePairingService} treats more
 * than one match as ambiguous/failed, same as zero matches.
 */
public record FluxorPairing(
        UUID id,
        String pairingTokenHash,
        String pinHash,
        String pollTokenHash,
        PairingStatus status,
        UUID accountId,
        UUID deviceId,
        String deviceNameHint,
        Instant expiresAt,
        Instant createdAt) {
    public boolean isExpired(Instant now) {
        return now.isAfter(expiresAt);
    }
}
