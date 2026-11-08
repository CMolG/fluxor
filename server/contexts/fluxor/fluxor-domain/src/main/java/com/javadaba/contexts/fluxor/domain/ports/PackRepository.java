package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.Pack;

import java.util.List;
import java.util.UUID;

/** The CEET packs an account published to Fluxor online, and the projects each one is attached to (card://JAVA-286). */
public interface PackRepository {

    /**
     * Stores the pack as the account's {@code packId} (replacing its files when it was published
     * before, keeping its other attachments) and attaches it to {@code projectId}, together.
     */
    void publish(Pack pack, UUID projectId);

    /** Detaches the account's pack from the project. False when it was not attached there. */
    boolean detach(UUID accountId, String packId, UUID projectId);

    /** Deletes the account's pack, its files and its attachments. False when there was none. */
    boolean delete(UUID accountId, String packId);

    /** Deletes every pack the account published for the role (an interview erased, or its consent withdrawn). */
    void deleteRole(UUID accountId, String role);

    /** The packs attached to the project, each with its files, ordered by pack id. */
    List<Pack> findAttached(UUID projectId);
}
