package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.HarnessEnrollment;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public interface HarnessEnrollmentRepository {

    void save(HarnessEnrollment enrollment);

    Optional<HarnessEnrollment> findByCodeHash(String codeHash);

    /**
     * Spends the code for {@code deviceId}, only if it is unspent and not expired at {@code now}.
     * Returns false, writing nothing, when another redemption got there first.
     */
    boolean consume(UUID id, UUID deviceId, Instant now);

    /**
     * Deletes every code that lapsed before {@code now}, spent or not: nothing reads one after its
     * expiry, and the device a spent one made is kept in {@code fluxor_device}.
     */
    void deleteExpired(Instant now);
}
