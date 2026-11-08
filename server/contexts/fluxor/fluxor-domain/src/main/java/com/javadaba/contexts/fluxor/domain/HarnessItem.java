package com.javadaba.contexts.fluxor.domain;

import java.util.Map;

/**
 * One version of a catalog entry (JAVA-157). {@code body} is the Markdown a client writes to disk;
 * {@code spec} is the kind's neutral shape (a hook's event, tools and per-OS scripts plus its
 * mandatory {@code fallback}; a preset's {@code items}), per decision 4 of the Fluxor online spike.
 * {@code marketVersion} and {@code contentHash} name the Fluxor market atom the row was seeded from
 * (card://JAVA-272); both are null when no market atom backs it. {@code ownership} is null on a market
 * item, and says whose an own item is and who sees it (card://JAVA-750).
 */
public record HarnessItem(
        String key,
        int version,
        HarnessItemKind kind,
        String title,
        String description,
        String body,
        Map<String, Object> spec,
        String provenance,
        String marketVersion,
        String contentHash,
        HarnessOwnership ownership) {

    /** A market item: it belongs to nobody (card://JAVA-750). */
    public HarnessItem(String key, int version, HarnessItemKind kind, String title, String description, String body,
            Map<String, Object> spec, String provenance, String marketVersion, String contentHash) {
        this(key, version, kind, title, description, body, spec, provenance, marketVersion, contentHash, null);
    }

    /** Whether a person wrote it: an own item, never one the market seeded. */
    public boolean own() {
        return ownership != null;
    }
}
