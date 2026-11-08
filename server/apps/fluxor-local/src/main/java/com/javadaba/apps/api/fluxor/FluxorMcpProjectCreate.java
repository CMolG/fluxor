package com.javadaba.apps.api.fluxor;

import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessService;
import com.javadaba.platform.mcp.McpOperation;
import com.javadaba.platform.mcp.McpSchemas;
import com.javadaba.platform.shared.JsonSchema;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Creates a harness project. Fluxor Cloud does it from its web page, which Fluxor Local does not
 * have, so here it is one more MCP operation, on the same {@link HarnessService#createProject}.
 */
final class FluxorMcpProjectCreate {

    private FluxorMcpProjectCreate() {
    }

    static McpOperation<UUID> operation(HarnessService harness) {
        return new McpOperation<>("harness.project.create",
                "Creates an empty harness project, named after the repository it will serve. Then add "
                        + "items with harness.project.update (or a preset with harness.preset.apply) and "
                        + "set it up on a machine with harness.bootstrap.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(Map.of("name", JsonSchema.ordered("type", "string", "description",
                        "The project's name, at most 80 characters.")), List.of("name")),
                Map.of("name", "my-web-app"),
                (owner, params) -> FluxorJson.HarnessProjectView
                        .of(harness.createProject(owner, params.get("name").asText(), null)));
    }
}
