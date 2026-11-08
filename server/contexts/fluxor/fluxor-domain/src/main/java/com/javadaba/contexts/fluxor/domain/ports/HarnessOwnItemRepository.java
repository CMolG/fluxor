package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;

import java.util.Collection;
import java.util.List;
import java.util.UUID;

/**
 * The items people write (card://JAVA-750), next to the market's catalog in the same table: an own
 * item's key has a dot, which no market id can have, so the two never collide.
 */
public interface HarnessOwnItemRepository {

    /**
     * The newest version of every own item {@code accountId} can see, ordered by key: its own (retired
     * ones included, so it can bring them back), the public ones, the ones of the harness projects it
     * reads and of the organizations it belongs to; optionally of one kind.
     */
    List<HarnessItem> latestVisible(UUID accountId, Collection<UUID> readableProjects,
            Collection<UUID> organizations, HarnessItemKind kind);

    /** Inserts one version. A {@code (key, version)} already taken is {@code FluxorException} 409. */
    void insert(HarnessItem item);

    /** Sets who sees, or the retirement of, every version of the key at once. */
    void updateOwnership(String key, HarnessOwnership ownership);

    /** The active project items that carry the key and follow its newest version. */
    List<HarnessProjectItem> followers(String key);

    /** Which of these sha256 the blob store already holds (card://JAVA-2007): those are never sent again. */
    java.util.Set<String> knownBlobs(Collection<String> sha256s);

    /** Stores a file's bytes under their sha256; one already there is left as it is. */
    void insertBlob(String sha256, byte[] content);
}
