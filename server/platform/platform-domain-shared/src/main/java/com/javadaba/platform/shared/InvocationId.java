package com.javadaba.platform.shared;

import java.util.Objects;
import java.util.UUID;

public record InvocationId(UUID value) {
    public InvocationId {
        Objects.requireNonNull(value, "value");
    }

    public static InvocationId newId() {
        return new InvocationId(UUID.randomUUID());
    }
}
