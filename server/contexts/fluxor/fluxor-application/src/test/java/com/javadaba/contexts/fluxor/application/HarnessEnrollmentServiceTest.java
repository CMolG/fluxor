package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessEnrollment;
import com.javadaba.contexts.fluxor.domain.ports.HarnessEnrollmentRepository;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** JAVA-555: a one-time code the Fluxor MCP mints enrolls a local writer as a device, once, for 10 minutes. */
class HarnessEnrollmentServiceTest {

    private static final Instant NOW = Instant.parse("2026-10-01T10:00:00Z");

    private final FakeEnrollmentRepository enrollments = new FakeEnrollmentRepository();
    private final FakeDeviceRepository devices = new FakeDeviceRepository();
    private final UUID account = UUID.randomUUID();

    @Test
    void aCodeEnrollsOneDeviceNamedAfterTheMachine() {
        var minted = at(NOW).mint(account);

        var enrolled = at(NOW.plusSeconds(30)).redeem(minted.code(), "carlos-laptop");

        assertThat(minted.expiresAt()).isEqualTo(NOW.plus(Duration.ofMinutes(10)));
        assertThat(enrolled.deviceToken()).startsWith("jdbx_device_");
        assertThat(enrolled.device().name()).isEqualTo("fluxor-sync on carlos-laptop");
        assertThat(devices.findByAccount(account)).extracting(FluxorDevice::id).containsExactly(enrolled.device().id());
        assertThat(new FluxorDeviceAuthenticator(devices).authenticate(enrolled.deviceToken()).accountId())
                .as("the token is a device token like any other").isEqualTo(account);
        assertThat(enrollments.byHash.values()).singleElement().satisfies(e -> {
            assertThat(e.codeHash()).isEqualTo(DeviceTokens.sha256Hex(minted.code())).isNotEqualTo(minted.code());
            assertThat(e.deviceId()).isEqualTo(enrolled.device().id());
        });
    }

    @Test
    void aCodeWorksOnce() {
        var minted = at(NOW).mint(account);
        at(NOW).redeem(minted.code(), "one");

        assertInvalid(() -> at(NOW).redeem(minted.code(), "two"));
        assertThat(devices.findByAccount(account)).hasSize(1);
    }

    @Test
    void aCodeExpiresAtTenMinutes() {
        var minted = at(NOW).mint(account);

        assertInvalid(() -> at(NOW.plus(Duration.ofMinutes(10))).redeem(minted.code(), "late"));
        assertThat(devices.findByAccount(account)).isEmpty();
        assertThat(at(NOW.plus(Duration.ofMinutes(10)).minusSeconds(1)).redeem(minted.code(), "just in time"))
                .isNotNull();
    }

    @Test
    void anUnknownOrEmptyCodeIsTheSameError() {
        assertInvalid(() -> at(NOW).redeem("nope", "x"));
        assertInvalid(() -> at(NOW).redeem("", "x"));
        assertInvalid(() -> at(NOW).redeem(null, "x"));
    }

    @Test
    void losingARaceToTheSameCodeRevokesTheDeviceItMade() {
        var minted = at(NOW).mint(account);
        enrollments.loseNextConsume = true;

        assertInvalid(() -> at(NOW).redeem(minted.code(), "racer"));
        assertThat(devices.findByAccount(account)).singleElement().satisfies(d -> assertThat(d.isRevoked()).isTrue());
    }

    @Test
    void aMissingOrHostileHostnameStillNamesTheDevice() {
        assertThat(at(NOW).redeem(at(NOW).mint(account).code(), null).device().name())
                .isEqualTo("fluxor-sync on an unnamed machine");
        assertThat(at(NOW).redeem(at(NOW).mint(account).code(), "a\nb\u0007" + "x".repeat(80)).device().name())
                .startsWith("fluxor-sync on abx").hasSize(60);
    }

    @Test
    void mintingSweepsTheCodesThatLapsed() {
        var spent = at(NOW).mint(account);
        at(NOW).redeem(spent.code(), "used");
        at(NOW).mint(account);
        var live = at(NOW.plus(Duration.ofMinutes(5))).mint(account);

        at(NOW.plus(Duration.ofMinutes(10))).mint(account);

        assertThat(enrollments.byHash).hasSize(2).containsKey(DeviceTokens.sha256Hex(live.code()));
        assertThat(devices.findByAccount(account)).as("the device a spent code made is not the code's to remove")
                .hasSize(1);
    }

    private HarnessEnrollmentService at(Instant now) {
        return new HarnessEnrollmentService(enrollments, devices, Clock.fixed(now, ZoneOffset.UTC));
    }

    private static void assertInvalid(org.assertj.core.api.ThrowableAssert.ThrowingCallable call) {
        assertThatThrownBy(call).isInstanceOfSatisfying(FluxorException.class, ex -> {
            assertThat(ex.code()).isEqualTo("enrollment_invalid");
            assertThat(ex.httpStatus()).isEqualTo(401);
        });
    }

    /** {@code JdbcHarnessEnrollmentRepository}'s semantics: consume is a guarded, single update. */
    private static final class FakeEnrollmentRepository implements HarnessEnrollmentRepository {
        private final Map<String, HarnessEnrollment> byHash = new HashMap<>();
        private boolean loseNextConsume;

        @Override
        public void save(HarnessEnrollment enrollment) {
            byHash.put(enrollment.codeHash(), enrollment);
        }

        @Override
        public Optional<HarnessEnrollment> findByCodeHash(String codeHash) {
            return Optional.ofNullable(byHash.get(codeHash));
        }

        @Override
        public boolean consume(UUID id, UUID deviceId, Instant now) {
            if (loseNextConsume) {
                loseNextConsume = false;
                return false;
            }
            for (HarnessEnrollment e : byHash.values()) {
                if (e.id().equals(id) && e.consumedAt() == null && e.expiresAt().isAfter(now)) {
                    byHash.put(e.codeHash(), new HarnessEnrollment(e.id(), e.codeHash(), e.accountId(), e.expiresAt(),
                            now, deviceId, e.createdAt()));
                    return true;
                }
            }
            return false;
        }

        @Override
        public void deleteExpired(Instant now) {
            byHash.values().removeIf(e -> !e.expiresAt().isAfter(now));
        }
    }
}
