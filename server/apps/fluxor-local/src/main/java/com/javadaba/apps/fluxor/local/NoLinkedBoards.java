package com.javadaba.apps.fluxor.local;

import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects;
import jakarta.enterprise.context.ApplicationScoped;

import java.util.List;
import java.util.UUID;

/**
 * Fluxor Local has no project boards to link a harness project to, so no account has access to one:
 * the link a harness project may keep to an external board stays empty.
 */
@ApplicationScoped
public class NoLinkedBoards implements OfficiumProjects {

    @Override
    public Access accessOf(UUID accountId, UUID officiumProjectId) {
        return Access.NONE;
    }

    @Override
    public List<Board> accessibleProjects(UUID accountId) {
        return List.of();
    }
}
