package com.javadaba.platform.product;

import java.util.Map;

public record ProductInput(Map<String, Object> values) {
    public ProductInput {
        values = Map.copyOf(values == null ? Map.of() : values);
    }
}
