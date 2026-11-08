package com.javadaba.contexts.fluxor.domain;

/**
 * Thrown by {@code DevicePairingService#claim} for ANY exchange failure -- wrong/expired/replayed
 * pairingToken or PIN, lockout, ambiguous PIN collision. Deliberately a single generic shape
 * (constant message, no error code distinguishing the cause): direct port of the local bridge's
 * {@code auth.ts} {@code GENERIC_AUTH_ERROR} ("never reveals *why*"). The landing translates this
 * one outcome into UX ("couldn't be linked, try again or generate a new QR") -- see Task 7.
 */
public class PairingClaimException extends RuntimeException {

    public PairingClaimException() {
        super("Could not pair Fluxor");
    }
}
