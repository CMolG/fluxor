package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessEnrollment;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;
import com.javadaba.contexts.fluxor.domain.ports.HarnessEnrollmentRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

/**
 * Enrolls a local writer ({@code fluxor-sync}) as a Fluxor device without a PIN (JAVA-555, ADR 0019
 * decision 3). The Fluxor MCP already knows the account from its OAuth token, so it mints a code
 * here; the writer trades that code, once and within {@link #TTL}, for a device token. The MCP's
 * own token never leaves the client.
 *
 * <p>The code is 24 random bytes, so a wrong guess simply matches no row, as with a pairing token:
 * there is no lockout to keep, only the per-IP rate limit on the anonymous route. Every failure is
 * the same error, never saying whether the code was unknown, spent or expired.
 */
@ApplicationScoped
public class HarnessEnrollmentService {

    static final Duration TTL = Duration.ofMinutes(10);
    private static final String DEVICE_NAME = "fluxor-sync on ";

    private final HarnessEnrollmentRepository enrollments;
    private final FluxorDeviceRepository devices;
    private final Clock clock;
    private final SecureRandom random = new SecureRandom();

    @Inject
    public HarnessEnrollmentService(HarnessEnrollmentRepository enrollments, FluxorDeviceRepository devices) {
        this(enrollments, devices, Clock.systemUTC());
    }

    HarnessEnrollmentService(HarnessEnrollmentRepository enrollments, FluxorDeviceRepository devices, Clock clock) {
        this.enrollments = enrollments;
        this.devices = devices;
        this.clock = clock;
    }

    /**
     * A new code for {@code accountId}. The plaintext exists only in the return value. Minting also
     * sweeps every code that already lapsed, so the table only ever holds live ones.
     */
    public Minted mint(UUID accountId) {
        Instant now = Instant.now(clock);
        enrollments.deleteExpired(now);
        String code = DeviceTokens.randomToken(random, 24);
        Instant expiresAt = now.plus(TTL);
        enrollments.save(new HarnessEnrollment(UUID.randomUUID(), DeviceTokens.sha256Hex(code), accountId, expiresAt,
                null, null, now));
        return new Minted(code, expiresAt);
    }

    /** {@code POST /fluxor/v1/sync/enrollments} with {@code {code, hostname}}: anonymous, rate-limited by IP. */
    public Enrolled redeem(String code, String hostname) {
        Instant now = Instant.now(clock);
        HarnessEnrollment enrollment = (code == null || code.isBlank()
                ? Optional.<HarnessEnrollment>empty()
                : enrollments.findByCodeHash(DeviceTokens.sha256Hex(code)))
                .filter(e -> e.consumedAt() == null && now.isBefore(e.expiresAt()))
                .orElseThrow(HarnessEnrollmentService::invalid);
        DeviceTokens.Issued issued = DeviceTokens.issue(enrollment.accountId(), DEVICE_NAME + host(hostname), now,
                random);
        devices.save(issued.device());
        if (!enrollments.consume(enrollment.id(), issued.device().id(), now)) {
            // Another redemption spent the code between the read and here: this device never counts.
            devices.revoke(issued.device().id(), enrollment.accountId(), now);
            throw invalid();
        }
        return new Enrolled(issued.device(), issued.rawToken());
    }

    private static String host(String hostname) {
        String clean = hostname == null ? "" : hostname.replaceAll("\\p{Cntrl}", "").trim();
        return clean.isEmpty() ? "an unnamed machine" : clean;
    }

    private static FluxorException invalid() {
        return new FluxorException("enrollment_invalid",
                "This enrollment code is not valid: codes work once, for 10 minutes. Ask the Fluxor MCP for a new one",
                401);
    }

    public record Minted(String code, Instant expiresAt) {
    }

    public record Enrolled(FluxorDevice device, String deviceToken) {
    }
}
