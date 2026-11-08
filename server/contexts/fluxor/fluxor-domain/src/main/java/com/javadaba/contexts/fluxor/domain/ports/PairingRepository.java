package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.FluxorPairing;
import com.javadaba.contexts.fluxor.domain.PairingStatus;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface PairingRepository {

    void save(FluxorPairing pairing);

    Optional<FluxorPairing> findByPairingTokenHash(String pairingTokenHash);

    Optional<FluxorPairing> findByPollTokenHash(String pollTokenHash);

    /** May legitimately return more than one row (PIN collision across concurrent pairings) --
     *  the caller treats anything other than exactly one match as "no match". */
    List<FluxorPairing> findPendingByPinHash(String pinHash);

    void updateStatus(UUID id, PairingStatus status);

    /** Transitions {@code pending -> claimed}, linking the account and the freshly-created device. */
    void markClaimed(UUID id, UUID accountId, UUID deviceId);

    void markExpiredIfPast(UUID id, Instant now);
}
