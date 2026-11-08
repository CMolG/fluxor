package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface HarnessRepository {

    /** The newest version of every catalog key, optionally of one kind, ordered by key. */
    List<HarnessItem> latestCatalog(HarnessItemKind kind);

    /** One catalog item; a null {@code version} means its newest. */
    Optional<HarnessItem> findItem(String key, Integer version);

    /** Throws {@code FluxorException} 409 {@code officium_project_already_linked} when another project won the link. */
    void insertProject(HarnessProject project);

    Optional<HarnessProject> findProject(UUID id);

    List<HarnessProject> findProjects(UUID accountId);

    /** The harness project linked to an Officium project, whoever's it is: at most one exists. */
    Optional<HarnessProject> findByOfficiumProject(UUID officiumProjectId);

    /** The harness projects linked to any of these Officium projects, whoever's they are, ordered by name. */
    List<HarnessProject> findByOfficiumProjects(Collection<UUID> officiumProjectIds);

    /** Every item row of the project, tombstones included, ordered by key. */
    List<HarnessProjectItem> findProjectItems(UUID projectId);

    /**
     * Moves the project from {@code expectedRevision} to {@code newRevision} and writes {@code
     * items} (insert or overwrite by key), in one transaction. Returns false, writing nothing, when
     * the project is no longer at {@code expectedRevision}.
     */
    boolean commit(UUID projectId, long expectedRevision, long newRevision, List<HarnessProjectItem> items);

    /** The bytes of a skill file by sha256 (JAVA-555), only when some catalog item lists it. */
    Optional<byte[]> findBlob(String sha256);

    /** Every item, market or own, that lists this sha256 among its files (card://JAVA-2007). */
    List<HarnessItem> findItemsListing(String sha256);
}
