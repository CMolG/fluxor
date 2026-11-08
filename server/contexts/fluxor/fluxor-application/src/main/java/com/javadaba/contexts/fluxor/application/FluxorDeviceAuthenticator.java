package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.FluxorDeviceAuthException;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;

/**
 * Authenticates the device bearer token ({@code jdbx_device_<secret>}) presented on {@code
 * /fluxor/v1/sync/**} and the WS relay handshake (Task 6) -- plan #19, Task 3. Deliberately its
 * own token family (prefix distinguishable from the platform's {@code jdb_live_*} API keys, per
 * the plan's "auditoria" note), never mixed with {@link
 * com.javadaba.contexts.iam.application.ApiKeyAuthenticationService}: a device token authenticates
 * ONE paired Fluxor installation, not an API-key scope.
 *
 * <p>Mirrors {@code ApiKeyAuthenticationService}'s discipline (a thin, injectable service the JAX-RS
 * filter delegates to, per {@code SeoApiKeyFilter}'s "referencia de disciplina") so the auth logic
 * itself is unit-testable without a real HTTP route.
 */
@ApplicationScoped
public class FluxorDeviceAuthenticator {

    private static final String DEVICE_TOKEN_PREFIX = "jdbx_device_";
    /** {@code last_seen_at} is updated at most once per this window per device, so a chatty
     *  sync/WS client doesn't turn presence tracking into a write-per-request. */
    private static final Duration TOUCH_THROTTLE = Duration.ofMinutes(1);

    private final FluxorDeviceRepository devices;
    private final Clock clock;

    @Inject
    public FluxorDeviceAuthenticator(FluxorDeviceRepository devices) {
        this(devices, Clock.systemUTC());
    }

    FluxorDeviceAuthenticator(FluxorDeviceRepository devices, Clock clock) {
        this.devices = devices;
        this.clock = clock;
    }

    public AuthenticatedDevice authenticate(String presentedToken) {
        if (presentedToken == null || !presentedToken.startsWith(DEVICE_TOKEN_PREFIX)) {
            throw new FluxorDeviceAuthException("Missing or malformed device token");
        }
        FluxorDevice device = devices.findByTokenHash(sha256Hex(presentedToken))
                .orElseThrow(() -> new FluxorDeviceAuthException("Invalid device token"));
        if (device.isRevoked()) {
            throw new FluxorDeviceAuthException("Device token has been revoked");
        }
        Instant now = Instant.now(clock);
        if (device.lastSeenAt() == null || device.lastSeenAt().isBefore(now.minus(TOUCH_THROTTLE))) {
            devices.touchLastSeen(device.id(), now);
        }
        return new AuthenticatedDevice(device.accountId(), device.id());
    }

    private static String sha256Hex(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    public record AuthenticatedDevice(java.util.UUID accountId, java.util.UUID deviceId) {
    }
}
