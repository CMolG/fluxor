package com.javadaba.contexts.fluxor.infrastructure.adapters.inbound;

import com.javadaba.contexts.fluxor.application.HarnessWriter;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.EntityTag;
import jakarta.ws.rs.core.Response;

/**
 * {@code GET /fluxor/v1/writer/fluxor-sync.py}: the writer a machine downloads once to pull a
 * project's harness (JAVA-162, ADR 0019). Public, like any installer: it carries no secret, and the
 * Fluxor MCP's {@code harness.bootstrap} hands the agent its sha256 to check before running it.
 *
 * <p>Served by the API rather than as a static asset of {@code packages/apps/fluxor}: only
 * {@code /fluxor/app/**} reaches that app in production, and the API needs these bytes anyway for
 * every snapshot and for the sha256, so one copy serves all three. Outside {@code /fluxor/v1/sync/},
 * so {@link FluxorDeviceAuthFilter} never sees it.
 */
@Path("/fluxor/v1/writer")
public class FluxorWriterResource {

    private final HarnessWriter writer;

    public FluxorWriterResource(HarnessWriter writer) {
        this.writer = writer;
    }

    @GET
    @Path("/fluxor-sync.py")
    @Produces("text/x-python; charset=utf-8")
    public Response writer() {
        return Response.ok(writer.bytes()).tag(new EntityTag(writer.sha256()))
                .header("Cache-Control", "public, max-age=300").build();
    }
}
