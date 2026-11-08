package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * A CEET pack a person rendered on their own machine and published to Fluxor online (card://JAVA-286):
 * its shared files exactly as {@code pack.json} hashed them, kept per account and delivered to the
 * projects it is attached to. {@code packId} is {@code <role>-<person>}, so it names a person: it is
 * personal data, like the pack.
 */
public record Pack(
        UUID id,
        UUID accountId,
        String packId,
        String role,
        String formVersion,
        String profileVersion,
        String statementVersion,
        Instant publishedAt,
        List<File> files) {

    public Pack {
        files = List.copyOf(files);
    }

    /** One shared file, its path relative to the pack's folder. */
    public record File(String path, String sha256, String content) {
    }
}
