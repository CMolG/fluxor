package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;
import com.javadaba.contexts.fluxor.domain.HarnessVisibility;
import com.javadaba.contexts.fluxor.domain.ports.HarnessOwnItemRepository;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * The items people write for their harnesses (card://JAVA-750), next to the market's: a directive
 * (a role is one in the {@code role} exclusive group) with one of four visibilities, the owner's
 * decision of 2026-11-03. Every edit is a new version, and the projects that put it with no version
 * move to it in their next revision, so their machines pull it at the next session start.
 */
@ApplicationScoped
public class HarnessOwnItemService {

    /** {@code <namespace>.<name>}: the dot is what no market id has, so the seed never collides with one. */
    static final Pattern KEY = Pattern.compile("[a-z0-9][a-z0-9-]{0,63}\\.[a-z0-9][a-z0-9-]{0,63}");
    private static final List<String> ACTIVATIONS = List.of("always", "on-demand");
    private static final int MAX_BODY = 100_000;

    private final HarnessService harness;
    private final HarnessRepository catalog;
    private final HarnessOwnItemRepository own;
    private final Clock clock;

    @Inject
    public HarnessOwnItemService(HarnessService harness, HarnessRepository catalog, HarnessOwnItemRepository own) {
        this(harness, catalog, own, Clock.systemUTC());
    }

    HarnessOwnItemService(HarnessService harness, HarnessRepository catalog, HarnessOwnItemRepository own,
            Clock clock) {
        this.harness = harness;
        this.catalog = catalog;
        this.own = own;
        this.clock = clock;
    }

    /** What a directive says: its text and how it loads. */
    public record Directive(String title, String description, String body, String activation,
            String exclusiveGroup) {
    }

    /** Who sees an item: a visibility and, for project or organization, which one. */
    public record Sharing(String visibility, UUID harnessProjectId, UUID organizationAccountId) {
    }

    /** The market's newest items and the own items the account can see, ordered by key. */
    public List<HarnessItem> catalog(UUID accountId, HarnessItemKind kind) {
        HarnessAudience audience = harness.audience(accountId);
        List<HarnessItem> items = new ArrayList<>(catalog.latestCatalog(kind));
        items.addAll(own.latestVisible(accountId, audience.readableProjects(), audience.organizations(), kind));
        items.sort(Comparator.comparing(HarnessItem::key));
        return items;
    }

    /** One item, market or own, at a version or its newest; one the account cannot see is 404. */
    public HarnessItem item(UUID accountId, String key, Integer version) {
        HarnessAudience audience = harness.audience(accountId);
        return catalog.findItem(key, version).filter(audience::canSee).orElseThrow(() -> notFound(key, version));
    }

    public HarnessItem createDirective(UUID accountId, String key, Directive directive, Sharing sharing) {
        if (key == null || !KEY.matcher(key).matches()) {
            throw new FluxorException("invalid_harness_item_key", "An own item's key is <namespace>.<name>, lower case "
                    + "letters, digits and dashes, like team.code-review: " + key, 422);
        }
        HarnessItem item = new HarnessItem(key, 1, HarnessItemKind.DIRECTIVE, directive.title(),
                description(directive), body(directive), spec(directive), "written in Fluxor by its author", null,
                null, ownership(accountId, sharing, null));
        own.insert(item);
        return item;
    }

    /** The author's edit as the next version, which every project following the item moves to. */
    public HarnessItem newVersion(UUID accountId, String key, Directive directive) {
        HarnessItem current = requireMine(accountId, key);
        HarnessItem next = new HarnessItem(key, current.version() + 1, current.kind(), directive.title(),
                description(directive), body(directive), spec(directive), current.provenance(), null, null,
                current.ownership());
        own.insert(next);
        for (HarnessProjectItem follower : own.followers(key)) {
            moveTo(follower, next.version());
        }
        return next;
    }

    /**
     * The project's active items saved as a preset of the author's own (card://JAVA-2008): a saved
     * harness to apply to other projects. Each item keeps the version the project pins, and an own item
     * the project follows is saved following it; params travel too. Saving again under the author's
     * key is its next version; applying is a copy, so the projects that applied it keep their items.
     */
    public HarnessItem saveAsPreset(UUID accountId, UUID projectId, String key, String title, String description,
            Sharing sharing) {
        HarnessService.ProjectHarness project = harness.project(accountId, projectId);
        if (project.items().isEmpty()) {
            throw new FluxorException("invalid_harness_item", "This harness has no item to save yet", 422);
        }
        if (key == null || !KEY.matcher(key).matches() || title == null || title.isBlank()) {
            throw new FluxorException("invalid_harness_item_key",
                    "A saved harness needs a title and a key <namespace>.<name>: " + key, 422);
        }
        List<Map<String, Object>> listed = new ArrayList<>();
        for (HarnessService.Entry entry : project.items()) {
            Map<String, Object> item = new java.util.LinkedHashMap<>(Map.of("key", entry.item().itemKey()));
            if (!entry.item().followsLatest()) {
                item.put("version", entry.item().itemVersion());
            }
            if (!entry.item().params().isEmpty()) {
                item.put("params", entry.item().params());
            }
            listed.add(item);
        }
        HarnessItem current = catalog.findItem(key, null).orElse(null);
        if (current != null && (requireMine(accountId, key).kind() != HarnessItemKind.PRESET)) {
            throw new FluxorException("invalid_harness_kind", key + " is not a saved harness", 422);
        }
        Sharing scoped = sharing != null && "project".equals(sharing.visibility()) && sharing.harnessProjectId() == null
                ? new Sharing("project", projectId, null)
                : sharing;
        String text = description == null ? "" : description.trim();
        HarnessItem preset = new HarnessItem(key, current == null ? 1 : current.version() + 1, HarnessItemKind.PRESET,
                title.trim(), text, text, Map.of("items", listed), "saved in Fluxor from a project by its author", null,
                null, current == null ? ownership(accountId, scoped, null) : current.ownership());
        own.insert(preset);
        return preset;
    }

    /** Changes who sees the item, or retires it (hidden from new projects) or brings it back. */
    public HarnessItem share(UUID accountId, String key, Sharing sharing, Boolean retired) {
        HarnessItem current = requireMine(accountId, key);
        HarnessOwnership was = current.ownership();
        Instant retiredAt = retired == null ? was.retiredAt() : retired ? Instant.now(clock) : null;
        HarnessOwnership ownership = sharing == null || sharing.visibility() == null
                ? new HarnessOwnership(was.ownerAccountId(), was.visibility(), was.harnessProjectId(),
                        was.organizationAccountId(), retiredAt)
                : ownership(accountId, sharing, retiredAt);
        own.updateOwnership(key, ownership);
        return item(accountId, key, null);
    }

    /**
     * One more revision of a following project, at the new version. A project changed meanwhile is
     * read again once; still moving, it catches up at the author's next version or its next put.
     */
    void moveTo(HarnessProjectItem follower, int version) {
        for (int attempt = 0; attempt < 2; attempt++) {
            HarnessProject project = catalog.findProject(follower.projectId()).orElse(null);
            if (project == null) {
                return;
            }
            long next = project.revision() + 1;
            if (catalog.commit(project.id(), project.revision(), next, List.of(new HarnessProjectItem(
                    project.id(), follower.itemKey(), version, follower.params(), next, null, true)))) {
                return;
            }
        }
    }

    HarnessOwnership ownership(UUID accountId, Sharing sharing, Instant retiredAt) {
        HarnessVisibility visibility = sharing == null ? null : HarnessVisibility.fromWire(sharing.visibility());
        if (visibility == null) {
            throw new FluxorException("invalid_harness_visibility",
                    "'visibility' is private, project, organization or public", 422);
        }
        return switch (visibility) {
            case PRIVATE, PUBLIC -> new HarnessOwnership(accountId, visibility, null, null, retiredAt);
            case PROJECT -> {
                if (sharing.harnessProjectId() == null || !harness.canEdit(accountId, sharing.harnessProjectId())) {
                    throw new FluxorException("harness_project_not_editable",
                            "A project item belongs to a harness project you can change: name it in 'harnessProjectId'",
                            422);
                }
                yield new HarnessOwnership(accountId, visibility, sharing.harnessProjectId(), null, retiredAt);
            }
            case ORGANIZATION -> {
                UUID organization = sharing.organizationAccountId() == null
                        ? accountId
                        : sharing.organizationAccountId();
                if (!harness.audience(accountId).organizations().contains(organization)) {
                    throw new FluxorException("harness_organization_not_yours",
                            "You can share with your own organization, or one whose Officium projects you work on",
                            422);
                }
                yield new HarnessOwnership(accountId, visibility, null, organization, retiredAt);
            }
        };
    }

    HarnessItem requireMine(UUID accountId, String key) {
        HarnessItem item = item(accountId, key, null);
        if (!item.own() || !item.ownership().ownerAccountId().equals(accountId)) {
            throw new FluxorException("harness_item_not_yours", "Only the author of " + key + " changes it", 403);
        }
        return item;
    }

    private static String body(Directive directive) {
        if (directive == null || directive.title() == null || directive.title().isBlank() || directive.body() == null
                || directive.body().isBlank() || directive.body().length() > MAX_BODY) {
            throw new FluxorException("invalid_harness_item",
                    "A directive needs a title and a body of at most " + MAX_BODY + " characters", 422);
        }
        return directive.body().endsWith("\n") ? directive.body() : directive.body() + "\n";
    }

    private static String description(Directive directive) {
        return directive == null || directive.description() == null ? "" : directive.description().trim();
    }

    private static Map<String, Object> spec(Directive directive) {
        String activation = directive.activation() == null ? "always" : directive.activation();
        if (!ACTIVATIONS.contains(activation)) {
            throw new FluxorException("invalid_harness_item", "'activation' is always or on-demand", 422);
        }
        Map<String, Object> spec = new HashMap<>(Map.of("activation", activation));
        if (directive.exclusiveGroup() != null && !directive.exclusiveGroup().isBlank()) {
            spec.put("exclusiveGroup", directive.exclusiveGroup().trim());
        }
        return spec;
    }

    private static FluxorException notFound(String key, Integer version) {
        return new FluxorException("harness_item_not_found",
                "No catalog item " + key + (version == null ? "" : " at version " + version), 404);
    }
}
