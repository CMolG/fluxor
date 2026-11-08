package com.javadaba.apps.fluxor.local;

import io.smallrye.config.ConfigMapping;

import java.util.Optional;
import java.util.UUID;

/** Fluxor Local's settings ({@code fluxor.local.*} in application.yml). */
@ConfigMapping(prefix = "fluxor.local")
public interface LocalSettings {

    /** The one owner account every request acts as. */
    UUID accountId();

    /** The bearer token that gates the MCP endpoint; empty means the server is open. */
    Optional<String> token();

    /** The code {@code fluxor-sync init --enroll} accepts; empty means the token, or "local" with none. */
    Optional<String> enrollmentCode();

    /** The URL machines reach this server at, which {@code harness.bootstrap} hands out as {@code --server}. */
    String publicUrl();

    default Optional<String> requiredToken() {
        return token().map(String::trim).filter(value -> !value.isEmpty());
    }

    /** What {@code fluxor-sync init --enroll} must present to enroll a machine. */
    default String effectiveEnrollmentCode() {
        return enrollmentCode().map(String::trim).filter(value -> !value.isEmpty())
                .or(this::requiredToken)
                .orElse("local");
    }
}
