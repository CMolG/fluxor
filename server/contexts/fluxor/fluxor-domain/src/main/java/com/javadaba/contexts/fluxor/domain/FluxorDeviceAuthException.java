package com.javadaba.contexts.fluxor.domain;

/** Thrown by {@code FluxorDeviceAuthenticator} for a missing/malformed/unknown/revoked device
 *  bearer token -- generic on purpose (never distinguishes "revoked" from "never existed" to a
 *  caller), same discipline as {@code ApiKeyAuthenticationException}. */
public class FluxorDeviceAuthException extends RuntimeException {
    public FluxorDeviceAuthException(String message) {
        super(message);
    }
}
