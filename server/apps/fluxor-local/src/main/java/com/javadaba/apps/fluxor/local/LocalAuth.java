package com.javadaba.apps.fluxor.local;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.core.HttpHeaders;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Fluxor Local's whole authentication story. There is one owner account. With
 * {@code FLUXOR_LOCAL_TOKEN} set, the MCP endpoint needs {@code Authorization: Bearer <token>};
 * with it unset there is no authentication and the server binds to the loopback.
 *
 * <p>The sync routes keep their own plane: a machine enrolls once with {@code fluxor-sync init}
 * (see {@link LocalEnrollmentService}) and then sends the device token it got back.
 */
@ApplicationScoped
public class LocalAuth {

    private final LocalSettings settings;

    public LocalAuth(LocalSettings settings) {
        this.settings = settings;
    }

    /** The owner account, or a 401 when a token is required and the request does not carry it. */
    public UUID authenticate(String authorizationHeader) {
        Optional<String> required = settings.requiredToken();
        if (required.isPresent() && !matches(required.get(), bearer(authorizationHeader))) {
            throw new WebApplicationException(Response.status(Response.Status.UNAUTHORIZED)
                    .header(HttpHeaders.WWW_AUTHENTICATE, "Bearer realm=\"fluxor-local\"")
                    .type(MediaType.APPLICATION_JSON)
                    .entity(Map.of("error", "unauthorized",
                            "message", "This Fluxor Local server needs 'Authorization: Bearer <FLUXOR_LOCAL_TOKEN>'"))
                    .build());
        }
        return settings.accountId();
    }

    static String bearer(String authorizationHeader) {
        if (authorizationHeader == null || !authorizationHeader.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return "";
        }
        return authorizationHeader.substring(7).trim();
    }

    static boolean matches(String expected, String presented) {
        return MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8),
                presented.getBytes(StandardCharsets.UTF_8));
    }
}
