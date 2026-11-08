package com.javadaba.platform.shared;

import java.util.Objects;
import java.util.UUID;

public record OrganizationId(UUID value) {
    public OrganizationId {
        Objects.requireNonNull(value, "value");
    }
}
