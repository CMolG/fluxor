package com.javadaba.contexts.fluxor.domain;

import java.util.Map;
import java.util.UUID;

/** A catalog item in a project, at one version. A removed item keeps its row with {@code
 *  removedRevision} set, so a client that last synced before the removal learns about it. An own item
 *  put without a version {@code followsLatest}: its author's next version reaches the project
 *  (card://JAVA-750). */
public record HarnessProjectItem(
        UUID projectId,
        String itemKey,
        int itemVersion,
        Map<String, Object> params,
        long changedRevision,
        Long removedRevision,
        boolean followsLatest) {

    /** An item pinned to its version: every market item, and an own item put with a version. */
    public HarnessProjectItem(UUID projectId, String itemKey, int itemVersion, Map<String, Object> params,
            long changedRevision, Long removedRevision) {
        this(projectId, itemKey, itemVersion, params, changedRevision, removedRevision, false);
    }

    public boolean active() {
        return removedRevision == null;
    }

    public HarnessProjectItem removedAt(long revision) {
        return new HarnessProjectItem(projectId, itemKey, itemVersion, params, changedRevision, revision,
                followsLatest);
    }
}
