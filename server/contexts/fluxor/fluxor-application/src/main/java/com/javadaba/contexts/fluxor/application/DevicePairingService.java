package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.FluxorPairing;
import com.javadaba.contexts.fluxor.domain.PairingClaimException;
import com.javadaba.contexts.fluxor.domain.PairingStatus;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;
import com.javadaba.contexts.fluxor.domain.ports.PairingRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Server-side port of the local bridge's one-time QR/PIN pairing challenge (plan
 * 2026-07-09-fluxor-bridge-servidor-y-landing.md, #19, Task 2). Ported properties, cited from
 * {@code ../fluxor/fluxor-ide/src/main/bridge/auth.ts} (READ-ONLY reference, never edited by this
 * plan):
 * <ul>
 *   <li>Challenge = 6-digit unbiased PIN (manual entry) + 24-byte base64url pairing token (QR,
 *   carried in the URL FRAGMENT by the caller, never a query param -- never hits server logs).</li>
 *   <li>TTL 120s ({@link #PAIRING_TTL}).</li>
 *   <li>Lockout: 5 attempts / 60s, tracked per-IP AND globally (auth.ts's "global" was already
 *   process-wide, not per-challenge -- faithfully ported as a single JVM-wide counter here; see
 *   the multi-instance caveat below).</li>
 *   <li>Generic, constant error on ANY failure ({@link PairingClaimException}) -- never reveals
 *   whether the credential was wrong, expired, replayed, or locked out.</li>
 *   <li>Hashes at rest (sha-256): the plaintext pairingToken/pin/pollToken/deviceToken only ever
 *   exist at issuance, never persisted.</li>
 * </ul>
 *
 * <h2>Where this deliberately diverges from the local design (and why)</h2>
 * <p>The local bridge held ONE global in-memory challenge, compared byte-for-byte against every
 * incoming attempt in-process -- "burn the pairing token on the first attempt, success or
 * failure" existed there because a wrong guess was compared against a live secret held in the
 * same process. Here, MANY IDE installations pair concurrently against a shared server, so each
 * challenge is its own row, looked up by the exact sha-256 hash of the presented credential.
 * A wrong guess of a 24-byte token then simply matches no row (192 bits of entropy makes guessing
 * it computationally infeasible) -- there is nothing to "burn" on a miss, and a correct token only
 * works once anyway because {@link #claim} requires {@code status == PENDING} and immediately
 * transitions it to {@code CLAIMED}. The PIN keeps its local behavior of tolerating mistyped
 * retries up to the lockout cap, but since a 6-digit PIN has only 1e6 values, two concurrently
 * pending pairings could -- vanishingly rarely -- share the same {@code pin_hash}; {@link
 * PairingRepository#findPendingByPinHash} can return more than one row, and this service treats
 * that exactly like zero matches (ambiguous = failed, never guesses which one the caller meant).
 *
 * <p><strong>Multi-instance caveat (BACKLOG, same class as the scheduler single-instance-lock
 * caveat already tracked in the README, decision 10):</strong> the lockout counters ({@link
 * #ipAttempts}/{@link #globalAttempts}) and the claimed-device-token handoff ({@link
 * #pendingDeviceTokens}) are in-process state. A single app-api instance (today's deployment) is
 * exact; if app-api ever runs multi-instance, both need a shared backing store (Redis, like {@code
 * RedisRateLimitCounter}) -- registered in BACKLOG.md by this plan's Task 8, not solved here.
 */
@ApplicationScoped
public class DevicePairingService {

    private static final int PIN_DIGITS = 6;
    private static final int PIN_BOUND = 1_000_000;
    private static final Duration PAIRING_TTL = Duration.ofSeconds(120);
    private static final int MAX_AUTH_ATTEMPTS = 5;
    private static final Duration LOCKOUT = Duration.ofSeconds(60);
    private static final Duration ATTEMPT_STATE_IDLE = Duration.ofMinutes(15);
    private static final String DUMMY_COMPARAND = "0".repeat(64);

    private final PairingRepository pairings;
    private final FluxorDeviceRepository devices;
    private final Clock clock;
    private final SecureRandom random = new SecureRandom();
    private final String claimUrl;

    private final ConcurrentHashMap<String, AttemptTracker> ipAttempts = new ConcurrentHashMap<>();
    private final AttemptTracker globalAttempts = new AttemptTracker();
    /** Claimed-but-not-yet-polled device tokens, keyed by pairing id -- see the multi-instance
     *  caveat in the class javadoc. Consumed (removed) by the first successful {@link #poll}. */
    private final ConcurrentHashMap<UUID, String> pendingDeviceTokens = new ConcurrentHashMap<>();

    @Inject
    public DevicePairingService(
            PairingRepository pairings,
            FluxorDeviceRepository devices,
            @ConfigProperty(name = "javadaba.fluxor.connect-url", defaultValue = "https://javadaba.com/fluxor/connect") String claimUrl) {
        this(pairings, devices, Clock.systemUTC(), claimUrl);
    }

    DevicePairingService(PairingRepository pairings, FluxorDeviceRepository devices, Clock clock, String claimUrl) {
        this.pairings = pairings;
        this.devices = devices;
        this.clock = clock;
        this.claimUrl = claimUrl;
    }

    /** {@code POST /fluxor/v1/pairings} -- anonymous, IP-rate-limited by the caller. */
    public PairingCreated create() {
        Instant now = Instant.now(clock);
        Instant expiresAt = now.plus(PAIRING_TTL);
        String pairingToken = randomToken(24);
        String pin = generatePin();
        String pollToken = randomToken(24);

        FluxorPairing pairing = new FluxorPairing(
                UUID.randomUUID(),
                sha256Hex(pairingToken),
                sha256Hex(pin),
                sha256Hex(pollToken),
                PairingStatus.PENDING,
                null,
                null,
                null,
                expiresAt,
                now);
        pairings.save(pairing);
        return new PairingCreated(pairingToken, pin, pollToken, (int) PAIRING_TTL.toSeconds(), claimUrl);
    }

    /**
     * {@code POST /fluxor/v1/pairings/claim} -- account-session gated (the resource resolves
     * {@code accountId} from {@code AccountSessionCodec} BEFORE calling this). Exactly one of
     * {@code pairingToken}/{@code pin} should be non-blank; if both are, pairingToken wins (it's
     * the higher-entropy credential).
     */
    public FluxorDevice claim(UUID accountId, String pairingToken, String pin, String deviceName, String clientIp) {
        return claim(accountId, pairingToken, pin, deviceName, clientIp, null);
    }

    /**
     * @param signInFamily the native app's sign-in that claims it (JAVA-1425): the device ends when
     *                     the app signs out; null from a browser's session
     */
    public FluxorDevice claim(UUID accountId, String pairingToken, String pin, String deviceName, String clientIp,
            UUID signInFamily) {
        Instant now = Instant.now(clock);
        String ip = (clientIp == null || clientIp.isBlank()) ? "unknown" : clientIp;
        AttemptTracker ipState = ipAttempts.computeIfAbsent(ip, key -> new AttemptTracker());

        // Always pay the comparison cost, even on paths that short-circuit below, so locked-out
        // and not-locked-out requests take comparable time (auth.ts secureCompare discipline).
        secureCompare(pairingToken != null ? pairingToken : (pin != null ? pin : ""), DUMMY_COMPARAND);

        if (ipState.isLockedOut(now) || globalAttempts.isLockedOut(now)) {
            throw new PairingClaimException();
        }

        Optional<FluxorPairing> found = (pairingToken != null && !pairingToken.isBlank())
                ? pairings.findByPairingTokenHash(sha256Hex(pairingToken))
                : resolveByPin(pin);

        if (found.isEmpty() || found.get().status() != PairingStatus.PENDING || found.get().isExpired(now)) {
            ipState.recordFailure(now);
            globalAttempts.recordFailure(now);
            throw new PairingClaimException();
        }

        FluxorPairing pairing = found.get();
        ipState.recordSuccess(now);
        globalAttempts.recordSuccess(now);

        DeviceTokens.Issued issued = DeviceTokens.issue(accountId,
                deviceName == null || deviceName.isBlank() ? "Fluxor IDE" : deviceName, now, random, signInFamily);
        FluxorDevice device = issued.device();
        devices.save(device);
        pairings.markClaimed(pairing.id(), accountId, device.id());
        pendingDeviceTokens.put(pairing.id(), issued.rawToken());
        return device;
    }

    /** {@code GET /fluxor/v1/pairings/{pollToken}} -- anonymous, polled by the IDE every ~2s. */
    public PollOutcome poll(String pollToken) {
        Instant now = Instant.now(clock);
        Optional<FluxorPairing> found = pairings.findByPollTokenHash(sha256Hex(pollToken));
        if (found.isEmpty()) {
            return PollOutcome.NOT_FOUND;
        }
        FluxorPairing pairing = found.get();

        if (pairing.status() == PairingStatus.PENDING && pairing.isExpired(now)) {
            pairings.markExpiredIfPast(pairing.id(), now);
            return PollOutcome.expired();
        }
        if (pairing.status() == PairingStatus.PENDING) {
            return PollOutcome.pending();
        }
        if (pairing.status() == PairingStatus.CLAIMED) {
            String deviceToken = pendingDeviceTokens.remove(pairing.id());
            pairings.updateStatus(pairing.id(), PairingStatus.CONSUMED);
            if (deviceToken == null) {
                // Already delivered (replay) or the in-memory handoff was lost (app-api restart
                // between claim and poll) -- multi-instance caveat above. Either way there is
                // nothing left to hand out safely.
                return PollOutcome.expired();
            }
            return PollOutcome.claimed(deviceToken, pairing.accountId());
        }
        // CONSUMED or EXPIRED already.
        return PollOutcome.expired();
    }

    public List<FluxorDevice> listDevices(UUID accountId) {
        return devices.findByAccount(accountId);
    }

    public void revokeDevice(UUID accountId, UUID deviceId) {
        devices.revoke(deviceId, accountId, Instant.now(clock));
    }

    private Optional<FluxorPairing> resolveByPin(String pin) {
        if (pin == null || pin.isBlank()) {
            return Optional.empty();
        }
        List<FluxorPairing> matches = pairings.findPendingByPinHash(sha256Hex(pin));
        return matches.size() == 1 ? Optional.of(matches.get(0)) : Optional.empty();
    }

    private String generatePin() {
        int value = random.nextInt(PIN_BOUND); // java.security.SecureRandom#nextInt(bound) is unbiased (rejection sampling)
        return String.format("%0" + PIN_DIGITS + "d", value);
    }

    private String randomToken(int bytes) {
        return DeviceTokens.randomToken(random, bytes);
    }

    private static String sha256Hex(String value) {
        return DeviceTokens.sha256Hex(value);
    }

    /** Constant-time comparison via fixed-length digests, same discipline as auth.ts
     *  secureCompare/AccountSessionCodec#verify. */
    private static boolean secureCompare(String provided, String expected) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] a = digest.digest(provided.getBytes(StandardCharsets.UTF_8));
            digest.reset();
            byte[] b = digest.digest(expected.getBytes(StandardCharsets.UTF_8));
            return MessageDigest.isEqual(a, b);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    /** Per-IP or global brute-force counter -- direct port of auth.ts's {@code AttemptState}. */
    private static final class AttemptTracker {
        private int count;
        private Instant lockedUntil = Instant.EPOCH;
        private Instant lastSeen = Instant.EPOCH;

        synchronized boolean isLockedOut(Instant now) {
            return lockedUntil.isAfter(now);
        }

        synchronized void recordFailure(Instant now) {
            if (!lockedUntil.equals(Instant.EPOCH) && !lockedUntil.isAfter(now)) {
                count = 0;
                lockedUntil = Instant.EPOCH;
            }
            count += 1;
            lastSeen = now;
            if (count >= MAX_AUTH_ATTEMPTS) {
                lockedUntil = now.plus(LOCKOUT);
            }
        }

        synchronized void recordSuccess(Instant now) {
            count = 0;
            lockedUntil = Instant.EPOCH;
            lastSeen = now;
        }

        synchronized boolean isIdle(Instant now) {
            return !isLockedOut(now) && lastSeen.isBefore(now.minus(ATTEMPT_STATE_IDLE));
        }
    }

    /** {@code create()} response -- the ONLY point these plaintext values ever exist. */
    public record PairingCreated(String pairingToken, String pin, String pollToken, int expiresIn, String claimUrl) {
    }

    /** {@code poll()} outcome -- {@link #NOT_FOUND}/pending map to {@code 204}, {@link #claimed}
     *  to {@code 200}, expired to {@code 410} at the resource layer. */
    public record PollOutcome(Kind kind, String deviceToken, UUID accountId) {
        public enum Kind {
            PENDING, CLAIMED, EXPIRED, NOT_FOUND
        }

        public static final PollOutcome NOT_FOUND = new PollOutcome(Kind.NOT_FOUND, null, null);

        public static PollOutcome pending() {
            return new PollOutcome(Kind.PENDING, null, null);
        }

        public static PollOutcome claimed(String deviceToken, UUID accountId) {
            return new PollOutcome(Kind.CLAIMED, deviceToken, accountId);
        }

        public static PollOutcome expired() {
            return new PollOutcome(Kind.EXPIRED, null, null);
        }
    }
}
