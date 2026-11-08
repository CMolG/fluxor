package com.javadaba.contexts.fluxor.domain.ports;

import java.util.List;
import java.util.UUID;

/**
 * What an account is to an Officium project, answered by Officium itself (its membership rules,
 * teams included), so a harness project is never linked to a board its caller does not own
 * (JAVA-406), and is read only by the people of the board it is linked to (card://JAVA-2006).
 */
public interface OfficiumProjects {

    /** {@link Access#NONE} for a project that does not exist and for one the account cannot see. */
    Access accessOf(UUID accountId, UUID officiumProjectId);

    /** Every Officium project the account can see (owns, is a member of, or is granted through a team). */
    List<Board> accessibleProjects(UUID accountId);

    /**
     * An Officium project as a harness listing names it, with its owner: the account whose
     * organization everyone with access to it belongs to (card://JAVA-750).
     */
    record Board(UUID id, String name, UUID ownerAccountId) {
    }

    /** Officium's roles, plus {@link #NONE} for no access at all. */
    enum Access {
        NONE, VIEWER, EDITOR, OWNER
    }
}
