package com.javadaba.apps.api.fluxor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessBootstrapService;
import com.javadaba.contexts.fluxor.application.HarnessService;
import com.javadaba.platform.mcp.McpOperation;
import com.javadaba.platform.mcp.McpParams;
import com.javadaba.platform.mcp.McpSchemas;
import com.javadaba.platform.shared.JsonSchema;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * What an agent changes on a harness project over MCP: set it up on its machine (JAVA-162), and
 * put, re-version or remove its items or apply a preset to it (card://JAVA-2123), with the revision
 * it last read, as Fluxor's page does. Each is {@link HarnessService}'s REST write.
 */
final class FluxorMcpHarnessWrites {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private FluxorMcpHarnessWrites() {
    }

    static List<McpOperation<UUID>> operations(HarnessService harness, HarnessBootstrapService bootstrap,
            String apiBase) {
        return List.of(bootstrap(bootstrap, apiBase), update(harness), applyPreset(harness));
    }

    static Map<String, Object> expectedRevision() {
        return JsonSchema.ordered("type", "integer", "minimum", 0, "description",
                "The project's revision you last read, from harness.project; a stale one is "
                        + "harness_revision_conflict, and you read it again.");
    }

    private static McpOperation<UUID> bootstrap(HarnessBootstrapService bootstrap, String apiBase) {
        return new McpOperation<>("harness.bootstrap",
                "Sets one harness project up on the machine you run on: returns commands to run, in "
                        + "order, from the project's root. They download fluxor-sync (checking its "
                        + "sha256), enroll this machine with a one-time code valid for 10 minutes, and "
                        + "pull the harness. Only after the user said yes (see the server's instructions).",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(Map.of("projectId", FluxorMcpHarnessReads.projectId()), List.of("projectId")),
                Map.of("projectId", FluxorMcpResource.EXAMPLE_ID),
                (owner, params) -> bootstrap.bootstrap(owner,
                        FluxorMcpResource.id(params, "projectId", "harness_project_not_found"), apiBase));
    }

    private static McpOperation<UUID> update(HarnessService harness) {
        Map<String, Object> change = McpSchemas.objectOf(JsonSchema.ordered(
                "key", JsonSchema.ordered("type", "string", "description", FluxorMcpHarnessReads.KEY_DESCRIPTION),
                "version", JsonSchema.ordered("type", "integer", "minimum", 1, "description",
                        "Pin this version; left out, the newest (and an own item then follows its author's next "
                                + "versions)."),
                "params", JsonSchema.ordered("type", "object", "description",
                        "The item's {{NAME}} values for this project.")),
                List.of("key"));
        return new McpOperation<>("harness.project.update",
                "Changes a project's items as one revision: put adds an item or changes its version or "
                        + "params, remove takes keys off. Every machine on the project pulls it at its next "
                        + "session start. Answers the project as harness.project does.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(JsonSchema.ordered("projectId", FluxorMcpHarnessReads.projectId(),
                        "expectedRevision", expectedRevision(),
                        "put", McpSchemas.array(change),
                        "remove", McpSchemas.array(McpSchemas.string())),
                        List.of("projectId", "expectedRevision")),
                JsonSchema.ordered("projectId", FluxorMcpResource.EXAMPLE_ID, "expectedRevision", 7,
                        "put", List.of(Map.of("key", "layout-discipline")), "remove", List.of("dark-mode")),
                (owner, params) -> FluxorJson.HarnessProjectDetailView.of(harness.update(owner,
                        FluxorMcpResource.id(params, "projectId", "harness_project_not_found"),
                        params.get("expectedRevision").asLong(),
                        objects(params.path("put")).stream()
                                .map(c -> new HarnessService.ItemChange(c.get("key").asText(),
                                        McpParams.integer(c, "version", null), map(c.get("params"))))
                                .toList(),
                        McpParams.stringArray(params, "remove"))));
    }

    /** The objects of an array param, none when it is left out. */
    static List<JsonNode> objects(JsonNode array) {
        List<JsonNode> out = new ArrayList<>();
        array.forEach(out::add);
        return out;
    }

    /** An object param as plain maps and lists, as the services keep params and a hook's manifest. */
    @SuppressWarnings("unchecked")
    static Map<String, Object> map(JsonNode node) {
        return node == null || node.isNull() ? Map.of() : MAPPER.convertValue(node, LinkedHashMap.class);
    }

    private static McpOperation<UUID> applyPreset(HarnessService harness) {
        return new McpOperation<>("harness.preset.apply",
                "Adds every item a preset lists to a project, with the preset's params, as one revision. "
                        + "skipped names the items it lists that you cannot see, which it did not add.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(JsonSchema.ordered("projectId", FluxorMcpHarnessReads.projectId(),
                        "key", JsonSchema.ordered("type", "string", "description",
                                "The preset's key, from harness.catalog with kind preset."),
                        "expectedRevision", expectedRevision()),
                        List.of("projectId", "key", "expectedRevision")),
                JsonSchema.ordered("projectId", FluxorMcpResource.EXAMPLE_ID, "key", "team.web-app",
                        "expectedRevision", 7),
                (owner, params) -> {
                    UUID projectId = FluxorMcpResource.id(params, "projectId", "harness_project_not_found");
                    String key = params.get("key").asText();
                    List<String> skipped = harness.presetSkips(owner, key);
                    var detail = FluxorJson.HarnessProjectDetailView.of(harness.applyPreset(owner, projectId, key,
                            params.get("expectedRevision").asLong()));
                    return new AppliedPresetView(detail.project(), detail.items(), skipped);
                });
    }

    /** The project after a preset, and the keys it skipped because the caller cannot see them. */
    record AppliedPresetView(FluxorJson.HarnessProjectView project, List<FluxorJson.HarnessProjectItemView> items,
            List<String> skipped) {
    }
}
