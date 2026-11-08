package com.javadaba.apps.fluxor.local;

import jakarta.ws.rs.WebApplicationException;
import org.junit.jupiter.api.Test;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class LocalAuthTest {

    private static final UUID ACCOUNT = UUID.fromString("00000000-0000-4000-8000-00000000f10c");

    private record Settings(Optional<String> token, Optional<String> enrollmentCode) implements LocalSettings {
        @Override
        public UUID accountId() {
            return ACCOUNT;
        }

        @Override
        public String publicUrl() {
            return "http://127.0.0.1:18191/api";
        }
    }

    @Test
    void anOpenServerActsAsTheOwnerWithNoHeader() {
        LocalAuth auth = new LocalAuth(new Settings(Optional.empty(), Optional.empty()));

        assertThat(auth.authenticate(null)).isEqualTo(ACCOUNT);
    }

    @Test
    void aBlankTokenCountsAsNoToken() {
        LocalAuth auth = new LocalAuth(new Settings(Optional.of("  "), Optional.empty()));

        assertThat(auth.authenticate(null)).isEqualTo(ACCOUNT);
    }

    @Test
    void aSecuredServerAcceptsOnlyItsToken() {
        LocalAuth auth = new LocalAuth(new Settings(Optional.of("s3cret"), Optional.empty()));

        assertThat(auth.authenticate("Bearer s3cret")).isEqualTo(ACCOUNT);
        assertThatThrownBy(() -> auth.authenticate("Bearer wrong")).isInstanceOf(WebApplicationException.class);
        assertThatThrownBy(() -> auth.authenticate(null)).isInstanceOf(WebApplicationException.class);
    }

    @Test
    void theEnrollmentCodeIsTheTokenUnlessSetAndLocalWhenThereIsNone() {
        assertThat(new Settings(Optional.empty(), Optional.empty()).effectiveEnrollmentCode()).isEqualTo("local");
        assertThat(new Settings(Optional.of("s3cret"), Optional.empty()).effectiveEnrollmentCode())
                .isEqualTo("s3cret");
        assertThat(new Settings(Optional.of("s3cret"), Optional.of("join-me")).effectiveEnrollmentCode())
                .isEqualTo("join-me");
    }
}
