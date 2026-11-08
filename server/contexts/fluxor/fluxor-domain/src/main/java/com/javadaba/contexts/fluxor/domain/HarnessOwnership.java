package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * Whose an item is and who sees it (card://JAVA-750). A market item has none. {@code harnessProjectId}
 * is set exactly for {@link HarnessVisibility#PROJECT}, {@code organizationAccountId} (the account
 * whose Officium organization it is) exactly for {@link HarnessVisibility#ORGANIZATION}, as the schema
 * also enforces. A retired item is hidden from new projects; the ones carrying it keep it.
 */
public record HarnessOwnership(UUID ownerAccountId, HarnessVisibility visibility, UUID harnessProjectId,
        UUID organizationAccountId, Instant retiredAt) {

    public HarnessOwnership {
        Objects.requireNonNull(ownerAccountId, "ownerAccountId");
        Objects.requireNonNull(visibility, "visibility");
        if ((visibility == HarnessVisibility.PROJECT) != (harnessProjectId != null)
                || (visibility == HarnessVisibility.ORGANIZATION) != (organizationAccountId != null)) {
            throw new IllegalArgumentException("A project item names its project, an organization item its "
                    + "organization, and no other names either");
        }
    }

    public boolean retired() {
        return retiredAt != null;
    }
}
