package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.UUID;

/**
 * How a device token ({@code jdbx_device_<secret>}) is issued, shared by PIN pairing and by an
 * enrollment code (JAVA-555): whichever ceremony proved the account, the device it creates is the
 * same kind of row, listed and revoked the same way. The plaintext only exists in the return value.
 */
final class DeviceTokens {

    static final String PREFIX = "jdbx_device_";
    private static final int NAME_MAX = 60;

    private DeviceTokens() {
    }

    static Issued issue(UUID accountId, String name, Instant now, SecureRandom random) {
        return issue(accountId, name, now, random, null);
    }

    /** @param signInFamily the native app's sign-in that proved the account, which the device ends with */
    static Issued issue(UUID accountId, String name, Instant now, SecureRandom random, UUID signInFamily) {
        String raw = PREFIX + randomToken(random, 32);
        String safeName = name.length() > NAME_MAX ? name.substring(0, NAME_MAX) : name;
        return new Issued(new FluxorDevice(UUID.randomUUID(), accountId, safeName, sha256Hex(raw), now, null, null,
                signInFamily), raw);
    }

    static String randomToken(SecureRandom random, int bytes) {
        byte[] buffer = new byte[bytes];
        random.nextBytes(buffer);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(buffer);
    }

    static String sha256Hex(String value) {
        return sha256Hex(value.getBytes(StandardCharsets.UTF_8));
    }

    static String sha256Hex(byte[] value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    record Issued(FluxorDevice device, String rawToken) {
    }
}
