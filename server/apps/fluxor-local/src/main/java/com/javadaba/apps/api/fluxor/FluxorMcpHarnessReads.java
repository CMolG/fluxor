package com.javadaba.apps.api.fluxor;

import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessOwnItemService;
import com.javadaba.contexts.fluxor.application.HarnessService;
import com.javadaba.contexts.fluxor.application.HarnessSnapshotService;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.platform.mcp.McpOperation;
import com.javadaba.platform.mcp.McpParams;
import com.javadaba.platform.mcp.McpSchemas;
import com.javadaba.platform.shared.JsonSchema;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * What an agent reads of the account's harness over MCP (card://JAVA-2123): the projects and what
 * each installs, one project's items with their versions and params, the catalog, one item whole
 * (its body and spec, as Fluxor's page reads it) and a skill's file by the sha256 its spec lists.
 * Each read is a REST read's service with the token's account, so its visibility rules are REST's.
 */
final class FluxorMcpHarnessReads {

    static final String KEY_DESCRIPTION = "The item's key, from harness.catalog or harness.project.";

    private FluxorMcpHarnessReads() {
    }

    static List<McpOperation<UUID>> operations(HarnessService harness, HarnessOwnItemService items,
            HarnessSnapshotService snapshots) {
        return List.of(projects(harness), project(harness), catalog(items), item(items), file(snapshots));
    }

    static Map<String, Object> projectId() {
        return JsonSchema.ordered("type", "string", "description", "The harness project's id, from harness.projects.");
    }

    private static McpOperation<UUID> projects(HarnessService harness) {
        return new McpOperation<>("harness.projects",
                "The account's harness projects, each with the rules, hooks and skills it installs "
                        + "(key, kind, title, what it does). Read it to tell the user what "
                        + "harness.bootstrap would install, before asking. harness.item reads one whole.",
                McpOperation.READ, FluxorMcpResource.SCOPE_READ, McpSchemas.schema(Map.of(), List.of()), Map.of(),
                (owner, params) -> harness.projects(owner).stream()
                        .map(p -> HarnessProjectView.of(harness.project(owner, p.project().id()))).toList());
    }

    private static McpOperation<UUID> project(HarnessService harness) {
        return new McpOperation<>("harness.project",
                "One harness project: its revision (pass it as expectedRevision to harness.project.update), "
                        + "your access to it, and each item it carries with the version and params it pins.",
                McpOperation.READ, FluxorMcpResource.SCOPE_READ,
                McpSchemas.schema(Map.of("projectId", projectId()), List.of("projectId")),
                Map.of("projectId", FluxorMcpResource.EXAMPLE_ID),
                (owner, params) -> FluxorJson.HarnessProjectDetailView.of(harness.project(owner,
                        FluxorMcpResource.id(params, "projectId", "harness_project_not_found"))));
    }

    private static McpOperation<UUID> catalog(HarnessOwnItemService items) {
        return new McpOperation<>("harness.catalog",
                "Every item the account can put on a project: the market's newest and the own items it can "
                        + "see, by key, with kind, version, title, description, exclusive group, a hook's "
                        + "event and, on an own item, whose it is.",
                McpOperation.READ, FluxorMcpResource.SCOPE_READ,
                McpSchemas.schema(Map.of("kind", JsonSchema.ordered("type", "string", "enum",
                        Arrays.stream(HarnessItemKind.values()).map(HarnessItemKind::toDb).toList(),
                        "description", "Only items of this kind.")), List.of()),
                Map.of("kind", "skill"),
                (owner, params) -> FluxorJson.HarnessItemSummaryView.of(items.catalog(owner,
                        params.hasNonNull("kind") ? HarnessItemKind.fromDb(params.get("kind").asText()) : null),
                        owner));
    }

    private static McpOperation<UUID> item(HarnessOwnItemService items) {
        return new McpOperation<>("harness.item",
                "One catalog item whole, at a version or its newest: its body (a directive's text, a skill's "
                        + "SKILL.md, a hook's fallback), its spec (how it loads; a skill's or files item's "
                        + "files with their sha256, which harness.file reads; a hook's scripts), provenance "
                        + "and, on an own item, whose it is.",
                McpOperation.READ, FluxorMcpResource.SCOPE_READ,
                McpSchemas.schema(JsonSchema.ordered(
                        "key", JsonSchema.ordered("type", "string", "description", KEY_DESCRIPTION),
                        "version", JsonSchema.ordered("type", "integer", "minimum", 1,
                                "description", "A version; leave it out for the newest.")),
                        List.of("key")),
                Map.of("key", "layout-discipline"),
                (owner, params) -> FluxorJson.HarnessItemView.of(items.item(owner, params.get("key").asText(),
                        McpParams.integer(params, "version", null)), owner));
    }

    private static McpOperation<UUID> file(HarnessSnapshotService snapshots) {
        return new McpOperation<>("harness.file",
                "One file a catalog item lists, by the sha256 harness.item's spec names: its text, or base64 "
                        + "when it is not UTF-8. Only a file of an item the account can see.",
                McpOperation.READ, FluxorMcpResource.SCOPE_READ,
                McpSchemas.schema(Map.of("sha256", JsonSchema.ordered("type", "string", "pattern", "^[0-9a-f]{64}$",
                        "description", "The file's sha256, from harness.item's spec.files.")), List.of("sha256")),
                Map.of("sha256", "0".repeat(64)),
                (owner, params) -> FileView.of(params.get("sha256").asText(),
                        snapshots.blob(owner, params.get("sha256").asText())));
    }

    /** A file's bytes as JSON carries them: text when they decode as UTF-8, base64 otherwise. */
    record FileView(String sha256, long size, String encoding, String content) {
        static FileView of(String sha256, byte[] bytes) {
            try {
                String text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
                return new FileView(sha256, bytes.length, "utf-8", text);
            } catch (CharacterCodingException binary) {
                return new FileView(sha256, bytes.length, "base64", Base64.getEncoder().encodeToString(bytes));
            }
        }
    }

    /** A project and what it installs, worded for the consent the instructions ask for. */
    record HarnessProjectView(String id, String name, long revision, List<Item> items) {
        record Item(String key, String kind, int version, String title, String description) {
        }

        static HarnessProjectView of(HarnessService.ProjectHarness h) {
            return new HarnessProjectView(h.project().id().toString(), h.project().name(), h.project().revision(),
                    h.items().stream().map(e -> new Item(e.catalog().key(), e.catalog().kind().toDb(),
                            e.catalog().version(), e.catalog().title(), e.catalog().description())).toList());
        }
    }
}
