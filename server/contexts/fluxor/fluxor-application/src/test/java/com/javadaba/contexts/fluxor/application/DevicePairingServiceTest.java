package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.FluxorPairing;
import com.javadaba.contexts.fluxor.domain.PairingClaimException;
import com.javadaba.contexts.fluxor.domain.PairingStatus;
import com.javadaba.contexts.fluxor.domain.ports.PairingRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Ports the behavioral properties of the local bridge's {@code auth.ts} (see
 * DevicePairingService javadoc) onto the server-side, DB-hash-lookup design. FAIL-first per the
 * plan's Task 2 Step 1: written against fakes before {@code JdbcPairingRepository}/{@code
 * JdbcFluxorDeviceRepository} existed to prove the service's OWN logic (lockout, single-use,
 * generic errors) independent of persistence.
 */
class DevicePairingServiceTest {

    private final FakePairingRepository pairings = new FakePairingRepository();
    private final FakeDeviceRepository devices = new FakeDeviceRepository();
    private final AtomicReference<Instant> now = new AtomicReference<>(Instant.parse("2026-07-16T10:00:00Z"));
    private DevicePairingService service;

    @BeforeEach
    void setUp() {
        service = new DevicePairingService(pairings, devices, new MutableClock(now),
                "https://javadaba.com/fluxor/connect");
    }

    @Test
    void happyPath_createClaimPoll() {
        DevicePairingService.PairingCreated created = service.create();
        assertThat(created.pin()).hasSize(6);
        assertThat(created.expiresIn()).isEqualTo(120);

        UUID accountId = UUID.randomUUID();
        FluxorDevice device = service.claim(accountId, created.pairingToken(), null, "My Laptop", "1.2.3.4");
        assertThat(device.accountId()).isEqualTo(accountId);
        assertThat(device.name()).isEqualTo("My Laptop");

        DevicePairingService.PollOutcome outcome = service.poll(created.pollToken());
        assertThat(outcome.kind()).isEqualTo(DevicePairingService.PollOutcome.Kind.CLAIMED);
        assertThat(outcome.deviceToken()).startsWith("jdbx_device_");
        assertThat(outcome.accountId()).isEqualTo(accountId);
    }

    @Test
    void pollAfterConsumed_returnsExpired() {
        DevicePairingService.PairingCreated created = service.create();
        service.claim(UUID.randomUUID(), created.pairingToken(), null, "Device", "1.2.3.4");
        service.poll(created.pollToken()); // first poll: consumes it (CLAIMED -> CONSUMED)

        DevicePairingService.PollOutcome second = service.poll(created.pollToken());
        assertThat(second.kind()).isEqualTo(DevicePairingService.PollOutcome.Kind.EXPIRED);
    }

    @Test
    void pollPending_returnsPending() {
        DevicePairingService.PairingCreated created = service.create();
        DevicePairingService.PollOutcome outcome = service.poll(created.pollToken());
        assertThat(outcome.kind()).isEqualTo(DevicePairingService.PollOutcome.Kind.PENDING);
    }

    @Test
    void pollUnknownToken_returnsNotFound() {
        DevicePairingService.PollOutcome outcome = service.poll("does-not-exist");
        assertThat(outcome.kind()).isEqualTo(DevicePairingService.PollOutcome.Kind.NOT_FOUND);
    }

    @Test
    void claimedTokenCannotBeClaimedAgain() {
        DevicePairingService.PairingCreated created = service.create();
        service.claim(UUID.randomUUID(), created.pairingToken(), null, "First", "1.2.3.4");

        assertThatThrownBy(() -> service.claim(UUID.randomUUID(), created.pairingToken(), null, "Second", "9.9.9.9"))
                .isInstanceOf(PairingClaimException.class);
    }

    @Test
    void expiredPairing_cannotBeClaimed() {
        DevicePairingService.PairingCreated created = service.create();
        now.set(now.get().plusSeconds(200)); // past the 120s TTL

        assertThatThrownBy(() -> service.claim(UUID.randomUUID(), created.pairingToken(), null, "Late", "1.2.3.4"))
                .isInstanceOf(PairingClaimException.class);
    }

    @Test
    void wrongPinFiveTimes_locksOutAndRejectsEvenTheCorrectPinAfterward() {
        DevicePairingService.PairingCreated created = service.create();
        UUID accountId = UUID.randomUUID();

        for (int i = 0; i < 5; i++) {
            assertThatThrownBy(
                    () -> service.claim(accountId, null, "000000".equals(created.pin()) ? "111111" : "000000",
                            "Device", "5.5.5.5"))
                    .isInstanceOf(PairingClaimException.class);
        }

        // 6th attempt, even with the CORRECT pin, is locked out -- generic error either way.
        assertThatThrownBy(() -> service.claim(accountId, null, created.pin(), "Device", "5.5.5.5"))
                .isInstanceOf(PairingClaimException.class);
    }

    @Test
    void correctPinClaimsSuccessfully() {
        DevicePairingService.PairingCreated created = service.create();
        UUID accountId = UUID.randomUUID();
        FluxorDevice device = service.claim(accountId, null, created.pin(), "Phone-paired", "6.6.6.6");
        assertThat(device.accountId()).isEqualTo(accountId);
    }

    @Test
    void listAndRevokeDevices() {
        DevicePairingService.PairingCreated created = service.create();
        UUID accountId = UUID.randomUUID();
        FluxorDevice device = service.claim(accountId, created.pairingToken(), null, "Device", "1.2.3.4");

        assertThat(service.listDevices(accountId)).hasSize(1);
        service.revokeDevice(accountId, device.id());
        assertThat(service.listDevices(accountId)).extracting(FluxorDevice::isRevoked).containsExactly(true);
    }

    @Test
    void revokeIsNoOpForAnotherAccount() {
        DevicePairingService.PairingCreated created = service.create();
        UUID accountId = UUID.randomUUID();
        FluxorDevice device = service.claim(accountId, created.pairingToken(), null, "Device", "1.2.3.4");

        service.revokeDevice(UUID.randomUUID(), device.id()); // different account: no-op
        assertThat(service.listDevices(accountId)).extracting(FluxorDevice::isRevoked).containsExactly(false);
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

    /** In-memory fake -- exact same lookup semantics as {@code JdbcPairingRepository} (exact hash
     *  match; PIN lookup can return >1 row). */
    private static final class FakePairingRepository implements PairingRepository {
        private final Map<UUID, FluxorPairing> byId = new HashMap<>();

        @Override
        public void save(FluxorPairing pairing) {
            byId.put(pairing.id(), pairing);
        }

        @Override
        public Optional<FluxorPairing> findByPairingTokenHash(String pairingTokenHash) {
            return byId.values().stream().filter(p -> p.pairingTokenHash().equals(pairingTokenHash)).findFirst();
        }

        @Override
        public Optional<FluxorPairing> findByPollTokenHash(String pollTokenHash) {
            return byId.values().stream().filter(p -> p.pollTokenHash().equals(pollTokenHash)).findFirst();
        }

        @Override
        public List<FluxorPairing> findPendingByPinHash(String pinHash) {
            List<FluxorPairing> result = new ArrayList<>();
            for (FluxorPairing p : byId.values()) {
                if (p.pinHash().equals(pinHash) && p.status() == PairingStatus.PENDING) {
                    result.add(p);
                }
            }
            return result;
        }

        @Override
        public void updateStatus(UUID id, PairingStatus status) {
            FluxorPairing p = byId.get(id);
            if (p != null) {
                byId.put(id, new FluxorPairing(p.id(), p.pairingTokenHash(), p.pinHash(), p.pollTokenHash(), status,
                        p.accountId(), p.deviceId(), p.deviceNameHint(), p.expiresAt(), p.createdAt()));
            }
        }

        @Override
        public void markClaimed(UUID id, UUID accountId, UUID deviceId) {
            FluxorPairing p = byId.get(id);
            if (p != null && p.status() == PairingStatus.PENDING) {
                byId.put(id, new FluxorPairing(p.id(), p.pairingTokenHash(), p.pinHash(), p.pollTokenHash(),
                        PairingStatus.CLAIMED, accountId, deviceId, p.deviceNameHint(), p.expiresAt(), p.createdAt()));
            }
        }

        @Override
        public void markExpiredIfPast(UUID id, Instant now) {
            FluxorPairing p = byId.get(id);
            if (p != null && p.status() == PairingStatus.PENDING && p.isExpired(now)) {
                updateStatus(id, PairingStatus.EXPIRED);
            }
        }
    }
}
