package com.javadaba.platform.shared;

import java.util.Objects;
import java.util.UUID;

public record ApiKeyId(UUID value) {
    public ApiKeyId {
        Objects.requireNonNull(value, "value");
    }
}
