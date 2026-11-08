package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessAccess;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Fluxor online's per-project harness (JAVA-157): the catalog, the projects of an account, and the
 * items each project carries. Every change that alters a project bumps its revision exactly once,
 * guarded by the revision the caller last read, so two clients editing the same project never
 * overwrite each other silently.
 */
@ApplicationScoped
public class HarnessService {

    private final HarnessRepository harness;
    private final OfficiumProjects officium;
    private final Clock clock;

    @Inject
    public HarnessService(HarnessRepository harness, OfficiumProjects officium) {
        this(harness, officium, Clock.systemUTC());
    }

    HarnessService(HarnessRepository harness, OfficiumProjects officium, Clock clock) {
        this.harness = harness;
        this.officium = officium;
        this.clock = clock;
    }

    public List<HarnessItem> catalog(HarnessItemKind kind) {
        return harness.latestCatalog(kind);
    }

    public HarnessItem catalogItem(String key, Integer version) {
        return harness.findItem(key, version).orElseThrow(() -> new FluxorException("harness_item_not_found",
                "No catalog item " + key + (version == null ? "" : " at version " + version), 404));
    }

    /**
     * The catalog item an Officium project reads under {@code key} (JAVA-404): the version its linked harness
     * project pins, else the catalog's newest; an explicit {@code version} is exactly that row. {@code linked} says
     * the harness project carries the version returned. Trusted: the caller checks the Officium project.
     */
    public Optional<PinnedItem> pinnedItem(UUID officiumProjectId, String key, Integer version) {
        Integer pinned = harness.findByOfficiumProject(officiumProjectId)
                .map(project -> harness.findProjectItems(project.id()).stream()
                        .filter(item -> item.active() && item.itemKey().equals(key))
                        .map(HarnessProjectItem::itemVersion)
                        .findFirst().orElse(null))
                .orElse(null);
        return harness.findItem(key, version != null ? version : pinned)
                .map(item -> new PinnedItem(item, pinned != null && pinned == item.version()));
    }

    /** A catalog item as one project reads it; {@code linked} when that project's harness pins this version. */
    public record PinnedItem(HarnessItem item, boolean linked) {
    }

    public HarnessProject createProject(UUID accountId, String name, UUID officiumProjectId) {
        if (name == null || name.isBlank()) {
            throw new FluxorException("invalid_harness_project_name", "'name' is required", 422);
        }
        if (officiumProjectId != null) {
            requireLinkable(accountId, officiumProjectId);
        }
        HarnessProject project = new HarnessProject(UUID.randomUUID(), accountId, name.trim(), officiumProjectId,
                0, Instant.now(clock));
        harness.insertProject(project);
        return project;
    }

    /**
     * Only an Officium project's owner links a harness project to it, and only one is linked
     * (JAVA-406): the linked project decides which role version the board's agents read. A project
     * the caller cannot see is 404, one they can see but do not own is 403.
     */
    private void requireLinkable(UUID accountId, UUID officiumProjectId) {
        switch (officium.accessOf(accountId, officiumProjectId)) {
            case NONE -> throw new FluxorException("officium_project_not_found", "No such Officium project", 404);
            case VIEWER, EDITOR -> throw new FluxorException("officium_project_owner_required",
                    "Only the Officium project's owner can link a harness project to it", 403);
            case OWNER -> {
                if (harness.findByOfficiumProject(officiumProjectId).isPresent()) {
                    throw new FluxorException("officium_project_already_linked",
                            "A harness project is already linked to this Officium project", 409);
                }
            }
        }
    }

    /**
     * The account's own harness projects, then the ones linked to an Officium project it can see
     * (card://JAVA-2006), each with what the account may do with it and, for a shared one, the
     * Officium project it is shared through.
     */
    public List<SharedProject> projects(UUID accountId) {
        List<SharedProject> result = new ArrayList<>();
        for (HarnessProject own : harness.findProjects(accountId)) {
            result.add(new SharedProject(own, HarnessAccess.OWNER, null));
        }
        Map<UUID, String> boards = officium.accessibleProjects(accountId).stream()
                .collect(Collectors.toMap(OfficiumProjects.Board::id, OfficiumProjects.Board::name, (a, b) -> a));
        for (HarnessProject linked : harness.findByOfficiumProjects(boards.keySet())) {
            if (!linked.accountId().equals(accountId)) {
                accessOf(accountId, linked).ifPresent(access -> result.add(
                        new SharedProject(linked, access, boards.get(linked.officiumProjectId()))));
            }
        }
        return result;
    }

    /** The project's active items the account can see: another person's private item is not one (JAVA-750). */
    public ProjectHarness project(UUID accountId, UUID projectId) {
        Readable readable = requireReadable(accountId, projectId);
        HarnessAudience audience = audience(accountId);
        return new ProjectHarness(readable.project(), entries(harness.findProjectItems(projectId).stream()
                .filter(HarnessProjectItem::active).toList()).stream().filter(e -> audience.canSee(e.catalog()))
                .toList(), readable.access());
    }

    /**
     * What the account can see of the items people write (card://JAVA-750): the harness projects it
     * reads, and the organizations it belongs to (its own, and every owner of a board it can see).
     */
    public HarnessAudience audience(UUID accountId) {
        Set<UUID> organizations = new HashSet<>(Set.of(accountId));
        officium.accessibleProjects(accountId).stream().map(OfficiumProjects.Board::ownerAccountId)
                .filter(java.util.Objects::nonNull).forEach(organizations::add);
        return new HarnessAudience(accountId,
                projects(accountId).stream().map(s -> s.project().id()).collect(Collectors.toSet()), organizations);
    }

    /** Whether the account may change the project's items: false for a viewer and for a stranger alike. */
    public boolean canEdit(UUID accountId, UUID projectId) {
        return harness.findProject(projectId).flatMap(p -> accessOf(accountId, p)).map(HarnessAccess::canEdit)
                .orElse(false);
    }

    /**
     * Adds or re-versions the {@code put} items and removes the {@code remove} keys. An item put
     * with a null version takes the catalog's newest. Nothing that changes nothing bumps the
     * revision: re-putting an item as it already is, or removing one the project does not carry.
     */
    public ProjectHarness update(UUID accountId, UUID projectId, long expectedRevision, List<ItemChange> put,
            List<String> remove) {
        HarnessProject project = requireEditable(accountId, projectId);
        if (project.revision() != expectedRevision) {
            throw conflict(project);
        }
        List<ItemChange> puts = put == null ? List.of() : put;
        List<String> removes = remove == null ? List.of() : remove;
        Set<String> seen = new HashSet<>();
        for (String key : puts.stream().map(ItemChange::key).toList()) {
            requireUnique(seen, key);
        }
        for (String key : removes) {
            requireUnique(seen, key);
        }

        Map<String, HarnessProjectItem> current = harness.findProjectItems(projectId).stream()
                .collect(Collectors.toMap(HarnessProjectItem::itemKey, Function.identity()));
        long next = project.revision() + 1;
        List<HarnessProjectItem> writes = new ArrayList<>();
        HarnessAudience audience = audience(accountId);
        for (ItemChange change : puts) {
            // An own item the editor cannot see is answered like one that does not exist (JAVA-750).
            HarnessItem item = harness.findItem(change.key(), change.version()).filter(audience::canSee)
                    .orElseThrow(() -> new FluxorException("unknown_harness_item",
                            "No catalog item " + change.key()
                                    + (change.version() == null ? "" : " at version " + change.version()),
                            422));
            if (item.kind() == HarnessItemKind.PRESET) {
                throw new FluxorException("harness_item_is_preset",
                        item.key() + " is a preset: apply it instead of adding it", 422);
            }
            Map<String, Object> params = change.params() == null ? Map.of() : change.params();
            HarnessProjectItem existing = current.get(item.key());
            boolean carried = existing != null && existing.active();
            if (item.own() && item.ownership().retired() && !carried) {
                throw new FluxorException("harness_item_retired",
                        item.key() + " is retired: the projects carrying it keep it, no new one adds it", 422);
            }
            // An own item put with no version follows its author's next versions (JAVA-750).
            boolean follows = item.own() && change.version() == null;
            if (carried && existing.itemVersion() == item.version() && existing.params().equals(params)
                    && existing.followsLatest() == follows) {
                continue;
            }
            writes.add(new HarnessProjectItem(projectId, item.key(), item.version(), params, next, null, follows));
        }
        for (String key : removes) {
            HarnessProjectItem existing = current.get(key);
            if (existing != null && existing.active()) {
                writes.add(existing.removedAt(next));
            }
        }

        if (!writes.isEmpty() && !harness.commit(projectId, expectedRevision, next, writes)) {
            throw conflict(requireEditable(accountId, projectId));
        }
        return project(accountId, projectId);
    }

    /** Adds every item the preset lists, with the preset's default params, as one revision. */
    public ProjectHarness applyPreset(UUID accountId, UUID projectId, String presetKey, long expectedRevision) {
        requireEditable(accountId, projectId);
        HarnessAudience audience = audience(accountId);
        List<ItemChange> visible = PresetItems.of(requireVisiblePreset(presetKey, audience)).stream()
                .filter(c -> harness.findItem(c.key(), c.version()).map(audience::canSee).orElse(false)).toList();
        return update(accountId, projectId, expectedRevision, visible, List.of());
    }

    /**
     * The keys of a preset the account cannot see, or that no longer exist: applying it skips them
     * and says so (card://JAVA-2008), since a saved harness can list another person's private item.
     */
    public List<String> presetSkips(UUID accountId, String presetKey) {
        HarnessAudience audience = audience(accountId);
        return PresetItems.of(requireVisiblePreset(presetKey, audience)).stream()
                .filter(c -> !harness.findItem(c.key(), c.version()).map(audience::canSee).orElse(false))
                .map(ItemChange::key).toList();
    }

    private HarnessItem requireVisiblePreset(String presetKey, HarnessAudience audience) {
        HarnessItem preset = requirePreset(presetKey);
        if (!audience.canSee(preset)) {
            throw new FluxorException("harness_item_not_found", "No catalog item " + presetKey, 404);
        }
        return preset;
    }

    /**
     * Adds only the preset's items the project does not carry (Officium's {@code harness.setup},
     * JAVA-563): one already there keeps the version and params its owner chose in Fluxor, so
     * setting a machine up never re-versions what someone pinned. Nothing missing, no revision.
     */
    public ProjectHarness ensurePreset(UUID accountId, UUID projectId, String presetKey) {
        HarnessItem preset = requirePreset(presetKey);
        requireEditable(accountId, projectId);
        ProjectHarness current = project(accountId, projectId);
        Set<String> carried = current.items().stream().map(e -> e.item().itemKey()).collect(Collectors.toSet());
        List<ItemChange> missing = PresetItems.of(preset).stream().filter(c -> !carried.contains(c.key())).toList();
        return missing.isEmpty()
                ? current
                : update(accountId, projectId, current.project().revision(), missing, List.of());
    }

    private HarnessItem requirePreset(String presetKey) {
        HarnessItem preset = catalogItem(presetKey, null);
        if (preset.kind() != HarnessItemKind.PRESET) {
            throw new FluxorException("harness_item_not_preset", presetKey + " is not a preset", 422);
        }
        return preset;
    }

    /**
     * A preset with the catalog items it lists, at the versions it pins (the newest where it pins
     * none): exactly what applying it adds. Read by the public page of what a setup installs
     * (JAVA-676), so only a preset answers: any other key is 404, like one that does not exist.
     */
    public PresetContents preset(String key) {
        HarnessItem preset = harness.findItem(key, null)
                .filter(item -> item.kind() == HarnessItemKind.PRESET)
                .orElseThrow(() -> new FluxorException("harness_preset_not_found", "No preset " + key, 404));
        List<HarnessItem> items = PresetItems.of(preset).stream()
                .map(change -> harness.findItem(change.key(), change.version()).orElseThrow(
                        () -> new IllegalStateException("Preset " + key + " lists " + change.key()
                                + (change.version() == null ? "" : "@" + change.version())
                                + ", which the catalog does not have")))
                .toList();
        return new PresetContents(preset, items);
    }

    /**
     * What changed after {@code since}: the items added or changed, and the keys removed. A client
     * with no revision (0) or one this project never reached (it was recreated, or the client is
     * confused) gets the whole harness, marked {@code full}, and replaces what it has.
     */
    public Changes changes(UUID accountId, UUID projectId, long since) {
        HarnessProject project = requireReadable(accountId, projectId).project();
        HarnessAudience audience = audience(accountId);
        List<HarnessProjectItem> items = harness.findProjectItems(projectId).stream()
                .filter(i -> harness.findItem(i.itemKey(), i.itemVersion()).map(audience::canSee).orElse(true))
                .toList();
        boolean full = since <= 0 || since > project.revision();
        List<HarnessProjectItem> changed = items.stream()
                .filter(i -> i.active() && (full || i.changedRevision() > since))
                .toList();
        List<String> removed = full
                ? List.of()
                : items.stream()
                        .filter(i -> !i.active() && i.removedRevision() > since)
                        .map(HarnessProjectItem::itemKey)
                        .toList();
        return new Changes(project, full, entries(changed), removed);
    }

    private List<Entry> entries(List<HarnessProjectItem> items) {
        return items.stream()
                .map(i -> new Entry(i, harness.findItem(i.itemKey(), i.itemVersion()).orElseThrow(
                        () -> new IllegalStateException("Catalog item " + i.itemKey() + "@" + i.itemVersion()
                                + " is gone, but the foreign key keeps it"))))
                .toList();
    }

    private static void requireUnique(Set<String> seen, String key) {
        if (key == null || !seen.add(key)) {
            throw new FluxorException("invalid_harness_change",
                    "Each item key may appear once per change, and never empty: " + key, 422);
        }
    }

    private static FluxorException conflict(HarnessProject project) {
        return new FluxorException("harness_revision_conflict",
                "The project is at revision " + project.revision() + ": read it again and retry", 409);
    }

    /**
     * Its owner holds a project; the people of the Officium project it is linked to read it, and that
     * project's owners and editors also change it (card://JAVA-2006). Empty for anyone else.
     */
    private Optional<HarnessAccess> accessOf(UUID accountId, HarnessProject project) {
        if (project.accountId().equals(accountId)) {
            return Optional.of(HarnessAccess.OWNER);
        }
        if (project.officiumProjectId() == null) {
            return Optional.empty();
        }
        return switch (officium.accessOf(accountId, project.officiumProjectId())) {
            case OWNER, EDITOR -> Optional.of(HarnessAccess.EDITOR);
            case VIEWER -> Optional.of(HarnessAccess.VIEWER);
            case NONE -> Optional.empty();
        };
    }

    /** A project the account cannot read is 404, exactly as one that does not exist. */
    private Readable requireReadable(UUID accountId, UUID projectId) {
        return harness.findProject(projectId)
                .flatMap(p -> accessOf(accountId, p).map(access -> new Readable(p, access)))
                .orElseThrow(() -> new FluxorException("harness_project_not_found",
                        "Harness project not found: " + projectId, 404));
    }

    /** A reader who may not change it gets 403: they already know the project exists. */
    private HarnessProject requireEditable(UUID accountId, UUID projectId) {
        Readable readable = requireReadable(accountId, projectId);
        if (!readable.access().canEdit()) {
            throw new FluxorException("harness_project_read_only",
                    "Viewers of the linked Officium project read this harness but cannot change it", 403);
        }
        return readable.project();
    }

    private record Readable(HarnessProject project, HarnessAccess access) {
    }

    public record ItemChange(String key, Integer version, Map<String, Object> params) {
    }

    /** A project item with the catalog version it points at. */
    public record Entry(HarnessProjectItem item, HarnessItem catalog) {
    }

    /** A project's active items, with what the reading account may do with it. */
    public record ProjectHarness(HarnessProject project, List<Entry> items, HarnessAccess access) {
    }

    /**
     * A project an account can read: {@code sharedThrough} names the Officium project it is shared
     * through, null for the account's own.
     */
    public record SharedProject(HarnessProject project, HarnessAccess access, String sharedThrough) {
    }

    public record PresetContents(HarnessItem preset, List<HarnessItem> items) {
    }

    public record Changes(HarnessProject project, boolean full, List<Entry> changed, List<String> removed) {
    }
}
