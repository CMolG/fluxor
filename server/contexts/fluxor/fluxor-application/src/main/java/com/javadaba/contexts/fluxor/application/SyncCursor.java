package com.javadaba.contexts.fluxor.application;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Optional;
import java.util.UUID;

/**
 * Opaque incremental-sync cursor -- {@code (updated_at, id)} tuple, shared by {@code
 * TaskSyncService} (Task 4) and {@code FlowSyncService} (Task 5): both {@code GET
 * /fluxor/v1/sync/{tasks,flows}?since=} pull endpoints page the exact same way. Callers must treat
 * the encoded string as opaque (it is NOT a stable format across versions) -- decode failures are
 * treated as "from the beginning", never a 400 (a device with a stale/corrupt cursor simply
 * re-syncs everything, which is always correct, just less efficient).
 */
final class SyncCursor {

    private SyncCursor() {
    }

    static String encode(Instant updatedAt, UUID id) {
        String raw = updatedAt.toEpochMilli() + ":" + id;
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    static Optional<Decoded> decode(String cursor) {
        if (cursor == null || cursor.isBlank()) {
            return Optional.empty();
        }
        try {
            String raw = new String(Base64.getUrlDecoder().decode(cursor), StandardCharsets.UTF_8);
            int sep = raw.indexOf(':');
            if (sep <= 0) {
                return Optional.empty();
            }
            Instant updatedAt = Instant.ofEpochMilli(Long.parseLong(raw.substring(0, sep)));
            UUID id = UUID.fromString(raw.substring(sep + 1));
            return Optional.of(new Decoded(updatedAt, id));
        } catch (RuntimeException ex) {
            return Optional.empty();
        }
    }

    record Decoded(Instant updatedAt, UUID id) {
    }
}
