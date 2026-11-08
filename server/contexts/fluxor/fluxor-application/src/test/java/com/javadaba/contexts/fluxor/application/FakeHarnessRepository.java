package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;
import com.javadaba.contexts.fluxor.domain.ports.HarnessOwnItemRepository;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.UUID;

/** Both the market's catalog and the items people write (card://JAVA-750), in one list like the table. */
final class FakeHarnessRepository implements HarnessRepository, HarnessOwnItemRepository {
    private final List<HarnessItem> catalog = new ArrayList<>();
    private final Map<UUID, HarnessProject> projects = new HashMap<>();
    private final Map<UUID, Map<String, HarnessProjectItem>> items = new HashMap<>();
    private final Map<String, byte[]> blobs = new HashMap<>();
    int commits;

    void addItem(HarnessItem item) {
        catalog.add(item);
    }

    void addBlob(String sha256, byte[] content) {
        blobs.put(sha256, content);
    }

    @Override
    public Optional<byte[]> findBlob(String sha256) {
        return findItemsListing(sha256).isEmpty() ? Optional.empty() : Optional.ofNullable(blobs.get(sha256));
    }

    @Override
    public List<HarnessItem> findItemsListing(String sha256) {
        return catalog.stream().filter(i -> java.util.stream.Stream.of("files", "marketFiles")
                .anyMatch(key -> i.spec().get(key) instanceof List<?> files
                        && files.stream().anyMatch(f -> f instanceof Map<?, ?> m && sha256.equals(m.get("sha256")))))
                .toList();
    }

    @Override
    public java.util.Set<String> knownBlobs(java.util.Collection<String> sha256s) {
        return sha256s.stream().filter(blobs::containsKey).collect(java.util.stream.Collectors.toSet());
    }

    @Override
    public void insertBlob(String sha256, byte[] content) {
        blobs.putIfAbsent(sha256, content);
    }

    @Override
    public List<HarnessItem> latestCatalog(HarnessItemKind kind) {
        Map<String, HarnessItem> latest = new TreeMap<>();
        catalog.stream().filter(i -> !i.own() && (kind == null || i.kind() == kind))
                .forEach(i -> latest.merge(i.key(), i, (a, b) -> a.version() >= b.version() ? a : b));
        return List.copyOf(latest.values());
    }

    @Override
    public List<HarnessItem> latestVisible(UUID accountId, java.util.Collection<UUID> readableProjects,
            java.util.Collection<UUID> organizations, HarnessItemKind kind) {
        HarnessAudience audience = new HarnessAudience(accountId, java.util.Set.copyOf(readableProjects),
                java.util.Set.copyOf(organizations));
        Map<String, HarnessItem> latest = new TreeMap<>();
        catalog.stream().filter(i -> i.own() && (kind == null || i.kind() == kind))
                .forEach(i -> latest.merge(i.key(), i, (a, b) -> a.version() >= b.version() ? a : b));
        return latest.values().stream().filter(i -> i.ownership().ownerAccountId().equals(accountId)
                || (!i.ownership().retired() && audience.canSee(i))).toList();
    }

    @Override
    public void insert(HarnessItem item) {
        if (findItem(item.key(), item.version()).isPresent()) {
            throw new com.javadaba.contexts.fluxor.domain.FluxorException("harness_item_key_taken",
                    "The key " + item.key() + " is taken", 409);
        }
        catalog.add(item);
    }

    @Override
    public void updateOwnership(String key, HarnessOwnership ownership) {
        catalog.replaceAll(i -> i.key().equals(key) && i.own()
                ? new HarnessItem(i.key(), i.version(), i.kind(),
                        i.title(), i.description(), i.body(), i.spec(), i.provenance(), i.marketVersion(),
                        i.contentHash(),
                        ownership)
                : i);
    }

    @Override
    public List<HarnessProjectItem> followers(String key) {
        return items.values().stream().flatMap(rows -> rows.values().stream())
                .filter(i -> i.itemKey().equals(key) && i.followsLatest() && i.active()).toList();
    }

    @Override
    public Optional<HarnessItem> findItem(String key, Integer version) {
        return catalog.stream()
                .filter(i -> i.key().equals(key) && (version == null || i.version() == version))
                .max(Comparator.comparingInt(HarnessItem::version));
    }

    @Override
    public void insertProject(HarnessProject project) {
        projects.put(project.id(), project);
    }

    @Override
    public Optional<HarnessProject> findByOfficiumProject(UUID officiumProjectId) {
        return projects.values().stream().filter(p -> officiumProjectId.equals(p.officiumProjectId())).findFirst();
    }

    @Override
    public List<HarnessProject> findByOfficiumProjects(java.util.Collection<UUID> officiumProjectIds) {
        return projects.values().stream().filter(p -> officiumProjectIds.contains(p.officiumProjectId()))
                .sorted(Comparator.comparing(HarnessProject::name)).toList();
    }

    @Override
    public Optional<HarnessProject> findProject(UUID id) {
        return Optional.ofNullable(projects.get(id));
    }

    @Override
    public List<HarnessProject> findProjects(UUID accountId) {
        return projects.values().stream().filter(p -> p.accountId().equals(accountId)).toList();
    }

    @Override
    public List<HarnessProjectItem> findProjectItems(UUID projectId) {
        return List.copyOf(items.getOrDefault(projectId, Map.of()).values().stream()
                .sorted(Comparator.comparing(HarnessProjectItem::itemKey)).toList());
    }

    @Override
    public boolean commit(UUID projectId, long expectedRevision, long newRevision, List<HarnessProjectItem> writes) {
        HarnessProject project = projects.get(projectId);
        if (project.revision() != expectedRevision) {
            return false;
        }
        projects.put(projectId, new HarnessProject(project.id(), project.accountId(), project.name(),
                project.officiumProjectId(), newRevision, project.updatedAt()));
        Map<String, HarnessProjectItem> rows = items.computeIfAbsent(projectId, id -> new HashMap<>());
        writes.forEach(w -> rows.put(w.itemKey(), w));
        commits++;
        return true;
    }

    /** Another client moved the project on between our read and our write. */
    void bumpBehindTheServicesBack(UUID projectId) {
        HarnessProject p = projects.get(projectId);
        projects.put(projectId, new HarnessProject(p.id(), p.accountId(), p.name(), p.officiumProjectId(),
                p.revision() + 1, p.updatedAt()));
    }
}
