package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.UUID;

/**
 * A one-time code that enrolls a local writer as a Fluxor device (JAVA-555, ADR 0019 decision 3).
 * The Fluxor MCP mints it for an account it already knows; {@code fluxor-sync init --enroll} trades
 * it once, within its lifetime, for a device token. Only the code's sha-256 is kept, like every
 * other credential of this context.
 */
public record HarnessEnrollment(
        UUID id,
        String codeHash,
        UUID accountId,
        Instant expiresAt,
        Instant consumedAt,
        UUID deviceId,
        Instant createdAt) {
}
