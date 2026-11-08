package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.FluxorDeviceAuthException;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FluxorDeviceAuthenticatorTest {

    private final FakeDeviceRepository devices = new FakeDeviceRepository();
    private final AtomicReference<Instant> now = new AtomicReference<>(Instant.parse("2026-07-16T10:00:00Z"));
    private FluxorDeviceAuthenticator authenticator;

    @BeforeEach
    void setUp() {
        authenticator = new FluxorDeviceAuthenticator(devices, new MutableClock(now));
    }

    @Test
    void validTokenAuthenticatesAndTouchesLastSeen() {
        UUID accountId = UUID.randomUUID();
        String rawToken = "jdbx_device_abc123";
        devices.save(
                new FluxorDevice(UUID.randomUUID(), accountId, "Laptop", sha256Hex(rawToken), now.get(), null, null));

        FluxorDeviceAuthenticator.AuthenticatedDevice authenticated = authenticator.authenticate(rawToken);
        assertThat(authenticated.accountId()).isEqualTo(accountId);
        assertThat(devices.lastTouchedAt).isEqualTo(now.get());
    }

    @Test
    void touchIsThrottledToOncePerMinute() {
        UUID accountId = UUID.randomUUID();
        String rawToken = "jdbx_device_abc123";
        devices.save(new FluxorDevice(UUID.randomUUID(), accountId, "Laptop", sha256Hex(rawToken), now.get(), now.get(),
                null));

        authenticator.authenticate(rawToken); // last_seen_at is "now" already -> should NOT touch again
        assertThat(devices.touchCount).isZero();

        now.set(now.get().plusSeconds(61));
        authenticator.authenticate(rawToken); // past the throttle window -> touches
        assertThat(devices.touchCount).isEqualTo(1);
    }

    @Test
    void revokedDeviceIsRejected() {
        UUID accountId = UUID.randomUUID();
        String rawToken = "jdbx_device_abc123";
        devices.save(new FluxorDevice(UUID.randomUUID(), accountId, "Laptop", sha256Hex(rawToken), now.get(), null,
                now.get()));

        assertThatThrownBy(() -> authenticator.authenticate(rawToken)).isInstanceOf(FluxorDeviceAuthException.class);
    }

    @Test
    void unknownTokenIsRejected() {
        assertThatThrownBy(() -> authenticator.authenticate("jdbx_device_does-not-exist"))
                .isInstanceOf(FluxorDeviceAuthException.class);
    }

    @Test
    void nonDeviceTokenIsRejected() {
        // A regular platform API key (jdb_live_*) must never authenticate against /fluxor/v1/sync/**.
        assertThatThrownBy(() -> authenticator.authenticate("jdb_live_dev_somesecret"))
                .isInstanceOf(FluxorDeviceAuthException.class);
        assertThatThrownBy(() -> authenticator.authenticate(null)).isInstanceOf(FluxorDeviceAuthException.class);
    }

    private static String sha256Hex(String value) {
        try {
            return HexFormat.of()
                    .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException(ex);
        }
    }

    private static final class MutableClock extends Clock {
        private final AtomicReference<Instant> now;

        MutableClock(AtomicReference<Instant> now) {
            this.now = now;
        }

        @Override
        public java.time.ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(java.time.ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now.get();
        }
    }

    private static final class FakeDeviceRepository implements FluxorDeviceRepository {
        private final Map<UUID, FluxorDevice> byId = new HashMap<>();
        private Instant lastTouchedAt;
        private int touchCount = 0;

        @Override
        public void save(FluxorDevice device) {
            byId.put(device.id(), device);
        }

        @Override
        public Optional<FluxorDevice> findById(UUID id) {
            return Optional.ofNullable(byId.get(id));
        }

        @Override
        public Optional<FluxorDevice> findByTokenHash(String tokenHash) {
            return byId.values().stream().filter(d -> d.tokenHash().equals(tokenHash)).findFirst();
        }

        @Override
        public List<FluxorDevice> findByAccount(UUID accountId) {
            return byId.values().stream().filter(d -> d.accountId().equals(accountId)).toList();
        }

        @Override
        public void revoke(UUID id, UUID accountId, Instant revokedAt) {
            // Not exercised here -- see DevicePairingServiceTest.
        }

        @Override
        public void touchLastSeen(UUID id, Instant lastSeenAt) {
            touchCount++;
            lastTouchedAt = lastSeenAt;
            FluxorDevice d = byId.get(id);
            if (d != null) {
                byId.put(id, new FluxorDevice(d.id(), d.accountId(), d.name(), d.tokenHash(), d.createdAt(),
                        lastSeenAt, d.revokedAt()));
            }
        }
    }
}
