package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;
import com.javadaba.contexts.fluxor.domain.ports.HarnessOwnItemRepository;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
import jakarta.enterprise.context.ApplicationScoped;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * A person's skills, hooks and files published from a local folder with {@code fluxor-sync item
 * publish} (card://JAVA-2007), as own items with the visibility JAVA-750 gives them. Files travel by
 * sha256: the writer asks which ones the blob store lacks and sends only those, so publishing again
 * an unchanged folder uploads nothing. Every publish of a key the author already has is its next
 * version, which the projects following it move to.
 */
@ApplicationScoped
public class HarnessPublishService {

    /** Per file and per item: the item travels base64 in one request, under the API's body limit. */
    static final int MAX_FILE = 1_048_576;
    static final int MAX_ITEM = 6 * 1_048_576;
    private static final int MAX_FILES = 2_000;
    private static final Set<String> EVENTS = Set.of("sessionStart", "promptSubmit", "preTool", "postTool",
            "postToolFailure", "stop", "notification", "statusLine");
    private static final List<String> HOOK_FIELDS = List.of("tools", "notifications", "timeoutMs", "sends");

    private final HarnessOwnItemService items;
    private final HarnessRepository catalog;
    private final HarnessOwnItemRepository own;

    public HarnessPublishService(HarnessOwnItemService items, HarnessRepository catalog, HarnessOwnItemRepository own) {
        this.items = items;
        this.catalog = catalog;
        this.own = own;
    }

    /** One file as sent: its bytes only when the blob store lacks them. */
    public record PublishedFile(String path, String sha256, long size, boolean executable, byte[] content) {

        /** A file sent whole, as the MCP sends one: its sha256 and size are the bytes' own. */
        public static PublishedFile of(String path, boolean executable, byte[] content) {
            return new PublishedFile(path, DeviceTokens.sha256Hex(content), content.length, executable, content);
        }
    }

    /**
     * What a folder publishes: a skill, a hook (its manifest's fields in {@code hook}), files, or a
     * directive, which may be an atom (JAVA-2011: {@code atom} and its inventory {@code card}, rendered
     * by the writer as Python renders it) for a project with the atoms skill.
     */
    public record Publication(String kind, String title, String description, Map<String, Object> hook,
            List<PublishedFile> files, String atom, String card) {

        public Publication(String kind, String title, String description, Map<String, Object> hook,
                List<PublishedFile> files) {
            this(kind, title, description, hook, files, null, null);
        }
    }

    /** The sha256 of these the blob store lacks: the files the writer must send. */
    public List<String> missing(List<String> sha256s) {
        Set<String> known = own.knownBlobs(sha256s == null ? List.of() : sha256s);
        return (sha256s == null ? List.<String>of() : sha256s).stream().filter(s -> !known.contains(s)).distinct()
                .toList();
    }

    public HarnessItem publish(UUID accountId, String key, Publication publication,
            HarnessOwnItemService.Sharing sharing) {
        HarnessItemKind kind = kind(publication.kind());
        if (key == null || !HarnessOwnItemService.KEY.matcher(key).matches()) {
            throw new FluxorException("invalid_harness_item_key", "An own item's key is <namespace>.<name>: " + key,
                    422);
        }
        List<PublishedFile> files = checkedFiles(kind, publication.files());
        storeBlobs(files);
        HarnessItem current = catalog.findItem(key, null).orElse(null);
        if (current != null && current.kind() != kind) {
            throw new FluxorException("invalid_harness_kind", key + " is a " + current.kind().toDb() + ", not a "
                    + kind.toDb(), 422);
        }
        if (current != null) {
            items.requireMine(accountId, key);
        }
        Map<String, Object> spec = switch (kind) {
            case HOOK -> hookSpec(publication.hook(), files);
            case DIRECTIVE -> directiveSpec(publication, files);
            default -> fileSpec(files);
        };
        String title = publication.title() == null || publication.title().isBlank() ? key : publication.title().trim();
        String description = publication.description() == null ? "" : publication.description().trim();
        HarnessItem item = new HarnessItem(key, current == null ? 1 : current.version() + 1, kind, title, description,
                body(kind, files, spec, description, current), spec, "published with fluxor-sync by its author", null,
                null, current == null ? items.ownership(accountId, sharing, null) : current.ownership());
        own.insert(item);
        if (current != null) {
            for (HarnessProjectItem follower : own.followers(key)) {
                items.moveTo(follower, item.version());
            }
        }
        return item;
    }

    private static HarnessItemKind kind(String kind) {
        return switch (kind == null ? "" : kind) {
            case "skill" -> HarnessItemKind.SKILL;
            case "hook" -> HarnessItemKind.HOOK;
            case "files" -> HarnessItemKind.FILES;
            case "directive" -> HarnessItemKind.DIRECTIVE;
            default -> throw new FluxorException("invalid_harness_kind",
                    "fluxor-sync publishes a skill, a hook or files: " + kind, 422);
        };
    }

    /** Paths that stay where the kind may write, sizes in bounds, and bytes that are what they claim. */
    private List<PublishedFile> checkedFiles(HarnessItemKind kind, List<PublishedFile> files) {
        if (files == null || files.isEmpty() || files.size() > MAX_FILES) {
            throw new FluxorException("invalid_harness_item", "An item publishes 1 to " + MAX_FILES + " files", 422);
        }
        long total = 0;
        Set<String> paths = new HashSet<>();
        for (PublishedFile file : files) {
            boolean placed = kind == HarnessItemKind.FILES
                    ? OwnFiles.placeable(file.path())
                    : OwnFiles.safe(file.path());
            if (!placed || !paths.add(file.path())) {
                throw new FluxorException("harness_path_refused", "A " + kind.toDb() + " cannot write " + file.path()
                        + (kind == HarnessItemKind.FILES ? ": files go under .harness/ or .claude/rules/" : ""), 422);
            }
            if (file.sha256() == null || !file.sha256().matches("[0-9a-f]{64}")) {
                throw new FluxorException("harness_blob_mismatch", file.path() + " names no sha256", 422);
            }
            if (file.content() != null && (file.content().length != file.size()
                    || !DeviceTokens.sha256Hex(file.content()).equals(file.sha256()))) {
                throw new FluxorException("harness_blob_mismatch", file.path() + " is not the bytes its sha256 names",
                        422);
            }
            total += file.size();
            if (file.size() > MAX_FILE || total > MAX_ITEM) {
                throw new FluxorException("harness_item_too_large",
                        "At most " + MAX_FILE / 1_048_576 + " MB a file and "
                                + MAX_ITEM / 1_048_576 + " MB an item: " + file.path(),
                        413);
            }
        }
        return files;
    }

    /** The bytes sent are stored; a file sent without them must already be in the store. */
    private void storeBlobs(List<PublishedFile> files) {
        List<String> absent = missing(files.stream().filter(f -> f.content() == null).map(PublishedFile::sha256)
                .toList());
        if (!absent.isEmpty()) {
            throw new FluxorException("harness_blob_missing", "Send the bytes of " + absent.size() + " file(s) the "
                    + "store lacks, starting with " + absent.getFirst(), 422);
        }
        for (PublishedFile file : files) {
            if (file.content() != null) {
                own.insertBlob(file.sha256(), file.content());
            }
        }
    }

    private static Map<String, Object> fileSpec(List<PublishedFile> files) {
        List<Map<String, Object>> listed = new ArrayList<>();
        for (PublishedFile f : files) {
            listed.add(Map.of("path", f.path(), "sha256", f.sha256(), "size", f.size(), "executable", f.executable()));
        }
        return Map.of("files", listed);
    }

    /**
     * A hook as the snapshot renders a market one (JAVA-556): its scripts and fallback inline, so the
     * manifest whose sha256 the user consents to names exactly those bytes.
     */
    private static Map<String, Object> hookSpec(Map<String, Object> hook, List<PublishedFile> files) {
        Map<String, Object> manifest = hook == null ? Map.of() : hook;
        if (!(manifest.get("event") instanceof String event) || !EVENTS.contains(event)) {
            throw new FluxorException("invalid_harness_item", "A hook names its event, one of " + EVENTS, 422);
        }
        Map<String, Object> spec = new LinkedHashMap<>(Map.of("event", event));
        for (PublishedFile file : files) {
            String name = switch (file.path()) {
                case "fallback.md" -> "fallback";
                case "hook.sh" -> "sh";
                case "hook.ps1" -> "ps1";
                default -> throw new FluxorException("harness_path_refused",
                        "A hook publishes fallback.md, hook.sh and hook.ps1, not " + file.path(), 422);
            };
            if (file.content() == null) {
                throw new FluxorException("harness_blob_missing", "A hook sends its " + file.path() + " inline", 422);
            }
            spec.put(name, new String(file.content(), StandardCharsets.UTF_8));
        }
        if (!(spec.get("fallback") instanceof String) || !(spec.containsKey("sh") || spec.containsKey("ps1"))) {
            throw new FluxorException("invalid_harness_item",
                    "A hook publishes its fallback.md and at least one of hook.sh and hook.ps1", 422);
        }
        HOOK_FIELDS.forEach(field -> {
            if (manifest.get(field) != null) {
                spec.put(field, manifest.get(field));
            }
        });
        return spec;
    }

    /**
     * A directive from a folder holding its one Markdown file; an atom also carries its kind and card,
     * so the atoms layout writes it like a market atom (JAVA-2011).
     */
    private static Map<String, Object> directiveSpec(Publication publication, List<PublishedFile> files) {
        if (files.size() != 1 || !files.getFirst().path().endsWith(".md") || files.getFirst().content() == null) {
            throw new FluxorException("invalid_harness_item", "A directive publishes its one .md file, inline", 422);
        }
        Map<String, Object> spec = new LinkedHashMap<>(Map.of("activation", "always"));
        if (publication.atom() != null) {
            if (!List.of("role", "mod", "step", "flow").contains(publication.atom()) || publication.card() == null
                    || !publication.card().startsWith("{\n  \"name\": ")) {
                throw new FluxorException("invalid_harness_item",
                        "An atom is a role, mod, step or flow with its inventory card", 422);
            }
            spec.put("atom", publication.atom());
            spec.put("card", publication.card());
            if ("role".equals(publication.atom())) {
                spec.put("exclusiveGroup", "role");
            }
        }
        return spec;
    }

    /** A skill's body is its SKILL.md; a hook's its fallback; files carry their description. */
    private static String body(HarnessItemKind kind, List<PublishedFile> files, Map<String, Object> spec,
            String description, HarnessItem current) {
        return switch (kind) {
            case HOOK -> (String) spec.get("fallback");
            case DIRECTIVE -> new String(files.getFirst().content(), StandardCharsets.UTF_8);
            case SKILL -> files.stream().filter(f -> f.path().equals("SKILL.md") && f.content() != null).findFirst()
                    .map(f -> new String(f.content(), StandardCharsets.UTF_8))
                    .orElse(current == null ? description : current.body());
            default -> description;
        };
    }
}
