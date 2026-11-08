package com.javadaba.apps.fluxor.local;

import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.container.PreMatching;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.Provider;

import java.util.List;
import java.util.Map;

/**
 * The routes Fluxor Local does not serve answer {@code 501 feature_unavailable_in_local}, naming
 * Fluxor Cloud, instead of a bare 404: QR/PIN device pairing for the desktop app, support tickets
 * and the desktop app's releases. Pre-matching, so it is one rule and not one resource per prefix.
 */
@Provider
@PreMatching
public class CloudOnlyFilter implements ContainerRequestFilter {

    static final String ERROR = "feature_unavailable_in_local";

    private static final List<String> CLOUD_ONLY = List.of("fluxor/v1/pairings", "fluxor/v1/ticket",
            "fluxor/v1/releases");

    @Override
    public void filter(ContainerRequestContext ctx) {
        if ("OPTIONS".equals(ctx.getMethod())) {
            return;
        }
        String path = ctx.getUriInfo().getPath();
        String normalized = path == null ? "" : (path.startsWith("/") ? path.substring(1) : path);
        if (CLOUD_ONLY.stream().anyMatch(prefix -> normalized.equals(prefix) || normalized.startsWith(prefix + "/"))) {
            ctx.abortWith(Response.status(Response.Status.NOT_IMPLEMENTED).type(MediaType.APPLICATION_JSON)
                    .entity(Map.of("error", ERROR,
                            "message", "This feature is only available in Fluxor Cloud, not in Fluxor Local."))
                    .build());
        }
    }
}
