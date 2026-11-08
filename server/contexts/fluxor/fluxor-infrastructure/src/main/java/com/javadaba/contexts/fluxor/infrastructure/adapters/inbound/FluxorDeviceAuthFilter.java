package com.javadaba.contexts.fluxor.infrastructure.adapters.inbound;

import com.javadaba.contexts.fluxor.application.FluxorDeviceAuthenticator;
import com.javadaba.contexts.fluxor.domain.FluxorDeviceAuthException;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.core.HttpHeaders;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.Provider;

import java.util.Map;

/**
 * Guards {@code /fluxor/v1/sync/**} (plan #19, Task 3) with the device bearer token ({@code
 * Authorization: Bearer jdbx_device_<token>}) -- the IDE's own auth plane, never mixed with
 * account sessions or platform API keys. Discipline mirrors {@code SeoApiKeyFilter} (delegates the
 * actual check to an injectable application-layer service, {@link FluxorDeviceAuthenticator}) --
 * this class only owns route matching, header extraction and translating the outcome into
 * request-scoped properties the sync resources (Task 4/5) read via {@code
 * ContainerRequestContext#getProperty}.
 */
@Provider
public class FluxorDeviceAuthFilter implements ContainerRequestFilter {

    /** Read by {@code FluxorSyncResource}/{@code FluxorFlowResource} sync routes via {@code
     *  ContainerRequestContext#getProperty}. */
    public static final String ACCOUNT_ID_PROPERTY = "fluxor.device.accountId";
    public static final String DEVICE_ID_PROPERTY = "fluxor.device.deviceId";

    private static final String SYNC_PREFIX = "fluxor/v1/sync/";
    /**
     * JAVA-555: the enrollment code is this route's credential; a device token is what it hands out.
     * Exempt by exact path, so nothing else under it can slip past the device check.
     */
    private static final String ENROLLMENT_PATH = "fluxor/v1/sync/enrollments";

    private final FluxorDeviceAuthenticator authenticator;

    public FluxorDeviceAuthFilter(FluxorDeviceAuthenticator authenticator) {
        this.authenticator = authenticator;
    }

    @Override
    public void filter(ContainerRequestContext ctx) {
        if ("OPTIONS".equals(ctx.getMethod())) {
            return; // no bloquear preflight CORS
        }
        String path = ctx.getUriInfo().getPath();
        String normalized = path == null ? "" : (path.startsWith("/") ? path.substring(1) : path);
        if (!normalized.startsWith(SYNC_PREFIX)
                || ("POST".equals(ctx.getMethod()) && normalized.equals(ENROLLMENT_PATH))) {
            return;
        }

        try {
            FluxorDeviceAuthenticator.AuthenticatedDevice device = authenticator.authenticate(extractToken(ctx));
            ctx.setProperty(ACCOUNT_ID_PROPERTY, device.accountId());
            ctx.setProperty(DEVICE_ID_PROPERTY, device.deviceId());
        } catch (FluxorDeviceAuthException ex) {
            ctx.abortWith(Response.status(Response.Status.UNAUTHORIZED)
                    .type(MediaType.APPLICATION_JSON)
                    .entity(Map.of("error", "unauthorized", "message", ex.getMessage()))
                    .build());
        }
    }

    private String extractToken(ContainerRequestContext ctx) {
        String auth = ctx.getHeaderString(HttpHeaders.AUTHORIZATION);
        if (auth != null && auth.regionMatches(true, 0, "Bearer ", 0, "Bearer ".length())) {
            return auth.substring("Bearer ".length()).trim();
        }
        return null;
    }
}
