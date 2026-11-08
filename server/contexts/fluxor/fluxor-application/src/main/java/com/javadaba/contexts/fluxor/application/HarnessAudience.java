package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;

import java.util.Set;
import java.util.UUID;

/**
 * What one account can see of the items people write (card://JAVA-750, the owner's decision of
 * 2026-11-03), worked out once per read: a market item and its own items always; a public one; a
 * project one when it reads that harness project (JAVA-2006); an organization one when it belongs to
 * that organization, that is, it is the organization's account or has access to one of its Officium
 * projects; a private one never.
 *
 * <p>Retirement does not hide an item here: a project that carries a retired item keeps it.
 */
public record HarnessAudience(UUID accountId, Set<UUID> readableProjects, Set<UUID> organizations) {

    public HarnessAudience {
        readableProjects = Set.copyOf(readableProjects);
        organizations = Set.copyOf(organizations);
    }

    public boolean canSee(HarnessItem item) {
        HarnessOwnership own = item.ownership();
        if (own == null || own.ownerAccountId().equals(accountId)) {
            return true;
        }
        return switch (own.visibility()) {
            case PUBLIC -> true;
            case PROJECT -> readableProjects.contains(own.harnessProjectId());
            case ORGANIZATION -> organizations.contains(own.organizationAccountId());
            case PRIVATE -> false;
        };
    }
}
