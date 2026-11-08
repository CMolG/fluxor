package com.javadaba.platform.product;

import com.javadaba.platform.shared.Cost;
import com.javadaba.platform.shared.InvocationId;

import java.util.Map;
import java.util.Objects;

public record ProductResult(
        InvocationId invocationId,
        Map<String, Object> output,
        Cost cost,
        boolean cached) {
    public ProductResult {
        Objects.requireNonNull(invocationId, "invocationId");
        output = Map.copyOf(output == null ? Map.of() : output);
        Objects.requireNonNull(cost, "cost");
    }
}
