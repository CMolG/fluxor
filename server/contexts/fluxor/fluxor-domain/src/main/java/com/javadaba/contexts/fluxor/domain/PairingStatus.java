package com.javadaba.contexts.fluxor.domain;

/** Matches the {@code fluxor_pairing.status} check constraint. */
public enum PairingStatus {
    PENDING, CLAIMED, CONSUMED, EXPIRED;

    public String toDb() {
        return name().toLowerCase();
    }

    public static PairingStatus fromDb(String value) {
        return PairingStatus.valueOf(value.toUpperCase());
    }
}
