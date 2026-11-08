package com.javadaba.apps.api.fluxor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.application.FlowSyncService;
import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessBootstrapService;
import com.javadaba.contexts.fluxor.application.HarnessOwnItemService;
import com.javadaba.contexts.fluxor.application.HarnessPublishService;
import com.javadaba.contexts.fluxor.application.HarnessService;
import com.javadaba.contexts.fluxor.application.HarnessSnapshotService;
import com.javadaba.contexts.fluxor.application.RunMonitorService;
import com.javadaba.apps.fluxor.local.LocalAuth;
import com.javadaba.apps.fluxor.local.LocalSettings;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.RunStatus;
import com.javadaba.platform.mcp.McpJsonRpcServer;
import com.javadaba.platform.mcp.McpOperation;
import com.javadaba.platform.mcp.McpOperationRegistry;
import com.javadaba.platform.mcp.McpOperationView;
import com.javadaba.platform.mcp.McpSchemas;
import com.javadaba.platform.mcp.McpToolException;
import com.javadaba.platform.shared.JsonSchema;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * {@code /fluxor/mcp} in Fluxor Local: the account's Fluxor flows and their runs, and its harness, for
 * any MCP client ({@code discover} + {@code query}, the shared {@link McpJsonRpcServer}).
 *
 * <p>Fluxor Local has one owner account and no OAuth: with {@code FLUXOR_LOCAL_TOKEN} set a request
 * needs {@code Authorization: Bearer <token>}, with it unset the server is open and binds to the
 * loopback ({@link LocalAuth}). The operations are the Cloud edition's, minus the CEET interview,
 * which is a Fluxor Cloud feature.
 *
 * <h2>Flows and runs, read; the harness, read and written</h2>
 * Flows and runs are read through the same services as the sync routes. The harness is the page's whole:
 * every item's content ({@link FluxorMcpHarnessReads}), a project's items ({@link FluxorMcpHarnessWrites})
 * the account's own items ({@link FluxorMcpItemWrites}) and the creation of a project
 * ({@link FluxorMcpProjectCreate}). {@code harness.bootstrap} answers with the
 * commands that set a project's harness up on the agent's disk, which this server cannot touch, and
 * {@code initialize} tells the agent when to run them ({@link HarnessBootstrapService#instructions}).
 */
@Path("/fluxor/mcp")
public class FluxorMcpResource {

    static final String RESOURCE_KEY = "fluxor";
    static final String SCOPE_READ = "fluxor:read";
    static final String SCOPE_WRITE = "fluxor:write";
    static final String EXAMPLE_ID = "3f2c1a9e-7b1d-4c55-9a0e-2d6f8b4c1e70";

    /** Fluxor's own instructions, except that Fluxor Local has no web page: an agent creates the project itself. */
    private static final HarnessBootstrapService.Product INSTRUCTED_PRODUCT = new HarnessBootstrapService.Product(
            HarnessBootstrapService.FLUXOR.name(),
            "Query  (none: create one with , named after the "
                    + "repository; several: ask which). The setup operation is , with that "
                    + "project's id.",
            HarnessBootstrapService.FLUXOR.whatGetsInstalled());

    private final LocalAuth auth;
    private final McpJsonRpcServer server;
    private final McpOperationRegistry<UUID> registry;

    public FluxorMcpResource(FlowSyncService flows, RunMonitorService runs, HarnessService harness,
            HarnessOwnItemService items, HarnessPublishService publish, HarnessSnapshotService snapshots,
            HarnessBootstrapService bootstrap, LocalSettings settings, LocalAuth auth,
            ObjectMapper mapper) {
        this.auth = auth;
        this.server = new McpJsonRpcServer("fluxor-local", "Fluxor", mapper,
                HarnessBootstrapService.instructions(INSTRUCTED_PRODUCT));
        List<McpOperation<UUID>> operations = new ArrayList<>(operations(flows, runs));
        operations.addAll(FluxorMcpHarnessReads.operations(harness, items, snapshots));
        operations.addAll(FluxorMcpHarnessWrites.operations(harness, bootstrap, settings.publicUrl()));
        operations.addAll(FluxorMcpItemWrites.operations(items, publish));
        operations.add(FluxorMcpProjectCreate.operation(harness));
        this.registry = new McpOperationRegistry<>(operations);
    }

    @GET
    public Response getNotAllowed() {
        return Response.status(405).build();
    }

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response handle(@HeaderParam("Authorization") String authorization, JsonNode body) {
        UUID accountId = auth.authenticate(authorization);
        McpJsonRpcServer.Reply reply = server.handle(body, new McpJsonRpcServer.Backend() {
            @Override
            public List<McpOperationView> discover(String filter) {
                return registry.discover(filter).stream().map(McpOperation::view).toList();
            }

            @Override
            public Object query(String operation, JsonNode params) {
                McpOperation<UUID> op = registry.find(operation)
                        .orElseThrow(() -> new McpToolException("unknown_operation",
                                "No such operation: " + operation + ". discover lists them.", "/operation", null));
                try {
                    return registry.query(accountId, operation, params);
                } catch (FluxorException ex) {
                    throw new McpToolException(ex.code(), ex.getMessage());
                }
            }
        });
        return Response.status(reply.status()).entity(reply.body()).build();
    }

    static List<McpOperation<UUID>> operations(FlowSyncService flows, RunMonitorService runs) {
        Map<String, Object> flowId = JsonSchema.ordered("type", "string", "description",
                "The flow's id, from flows.list.");
        Map<String, Object> runId = JsonSchema.ordered("type", "string", "description",
                "The run's id, from runs.list.");
        return List.of(
                new McpOperation<>("flows.list",
                        "The flows this account keeps in Fluxor: name, definition (the steps and what each "
                                + "depends on; null while the flow's design does not compile), whether it is a "
                                + "draft, and when it was last saved.",
                        McpOperation.READ, SCOPE_READ, McpSchemas.schema(Map.of(), List.of()), Map.of(),
                        (owner, params) -> FluxorJson.FlowView.of(flows.list(owner))),
                new McpOperation<>("flows.get",
                        "One of the account's flows with its whole definition, or, while its design does not "
                                + "compile, a null definition and the problems that keep it from compiling.",
                        McpOperation.READ, SCOPE_READ, McpSchemas.schema(Map.of("id", flowId), List.of("id")),
                        Map.of("id", EXAMPLE_ID),
                        (owner, params) -> FluxorJson.FlowDetailView
                                .of(flows.detail(owner, id(params, "id", "flow_not_found")), false)),
                new McpOperation<>("runs.list",
                        "The account's runs, newest first: which flow, which device ran it, its status and "
                                + "summary. Narrow it to one flow or one status.",
                        McpOperation.READ, SCOPE_READ,
                        McpSchemas.schema(JsonSchema.ordered(
                                "flowId", flowId,
                                "status", JsonSchema.ordered("type", "string", "enum",
                                        Arrays.stream(RunStatus.values()).map(RunStatus::toDb).toList(),
                                        "description", "Only runs in this status.")),
                                List.of()),
                        Map.of("status", "failed"),
                        (owner, params) -> FluxorJson.RunView.of(runs.list(owner,
                                params.hasNonNull("flowId") ? id(params, "flowId", "flow_not_found") : null,
                                status(params)))),
                new McpOperation<>("runs.get",
                        "One of the account's runs: its flow, status, start and end, and summary.",
                        McpOperation.READ, SCOPE_READ, McpSchemas.schema(Map.of("id", runId), List.of("id")),
                        Map.of("id", EXAMPLE_ID),
                        (owner, params) -> FluxorJson.RunView.of(runs.get(owner, id(params, "id", "run_not_found")))),
                new McpOperation<>("runs.events",
                        "What happened during one of the account's runs, step by step, in order. Pass the "
                                + "last seq you read as afterSeq to get only what came after it.",
                        McpOperation.READ, SCOPE_READ,
                        McpSchemas.schema(JsonSchema.ordered("id", runId, "afterSeq", JsonSchema.ordered(
                                "type", "integer", "minimum", -1,
                                "description", "Only events after this seq; leave it out for all of them.")),
                                List.of("id")),
                        JsonSchema.ordered("id", EXAMPLE_ID, "afterSeq", 10),
                        (owner, params) -> FluxorJson.RunEventView.of(runs.eventsAfterSeq(owner,
                                id(params, "id", "run_not_found"),
                                params.hasNonNull("afterSeq") ? params.get("afterSeq").asInt() : -1))));
    }

    private static RunStatus status(JsonNode params) {
        if (!params.hasNonNull("status")) {
            return null;
        }
        try {
            return RunStatus.fromDb(params.get("status").asText());
        } catch (IllegalArgumentException ex) {
            throw McpToolException.invalid("status is one of running, passed, failed, cancelled.", "/params/status");
        }
    }

    /** A malformed id is answered like a missing one, as the cookie-gated routes' 404 does. */
    static UUID id(JsonNode params, String field, String notFoundCode) {
        String raw = params.get(field).asText();
        try {
            return UUID.fromString(raw);
        } catch (IllegalArgumentException ex) {
            throw new FluxorException(notFoundCode, "Not found: " + raw, 404);
        }
    }
}
