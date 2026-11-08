package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Everyone owns every Officium project, until a test says what one account is to one project. Only
 * a board a test granted is listed as accessible, so a listing never invents boards.
 */
final class FakeOfficiumProjects implements OfficiumProjects {

    private final Map<String, Access> grants = new HashMap<>();
    private final Map<UUID, String> names = new HashMap<>();
    private final Map<UUID, UUID> owners = new HashMap<>();

    void grant(UUID accountId, UUID officiumProjectId, Access access) {
        grants.put(accountId + ":" + officiumProjectId, access);
        names.putIfAbsent(officiumProjectId, "Board " + officiumProjectId.toString().substring(0, 8));
    }

    void name(UUID officiumProjectId, String name) {
        names.put(officiumProjectId, name);
    }

    /** The account a board belongs to, whose organization its people are in (card://JAVA-750). */
    void owner(UUID officiumProjectId, UUID ownerAccountId) {
        owners.put(officiumProjectId, ownerAccountId);
    }

    @Override
    public Access accessOf(UUID accountId, UUID officiumProjectId) {
        return grants.getOrDefault(accountId + ":" + officiumProjectId, Access.OWNER);
    }

    @Override
    public List<Board> accessibleProjects(UUID accountId) {
        return grants.entrySet().stream()
                .filter(e -> e.getKey().startsWith(accountId + ":") && e.getValue() != Access.NONE)
                .map(e -> UUID.fromString(e.getKey().substring(e.getKey().indexOf(':') + 1)))
                .map(board -> new Board(board, names.get(board), owners.get(board)))
                .toList();
    }
}
