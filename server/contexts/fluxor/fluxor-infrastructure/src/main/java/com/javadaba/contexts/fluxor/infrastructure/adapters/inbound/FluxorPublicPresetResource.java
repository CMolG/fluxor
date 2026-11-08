package com.javadaba.contexts.fluxor.infrastructure.adapters.inbound;

import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessService;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

/**
 * {@code GET /fluxor/v1/public/presets/{key}}: a preset and what applying it installs, with no
 * sign-in (JAVA-676). The consent an agent asks for before a setup links a public page of exactly
 * this, so a person can read what they are agreeing to before they have an account. A preset is
 * catalog content, the same for everyone; a project never answers here. Outside
 * {@code /fluxor/v1/sync/}, so {@link FluxorDeviceAuthFilter} never sees it.
 */
@Path("/fluxor/v1/public/presets")
public class FluxorPublicPresetResource {

    private final HarnessService harness;

    public FluxorPublicPresetResource(HarnessService harness) {
        this.harness = harness;
    }

    @GET
    @Path("/{key}")
    @Produces(MediaType.APPLICATION_JSON)
    public Response preset(@PathParam("key") String key) {
        return Response.ok(FluxorJson.PublicPresetView.of(harness.preset(key)))
                .header("Cache-Control", "public, max-age=300").build();
    }
}
