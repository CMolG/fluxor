package com.javadaba.platform.product;

import com.javadaba.platform.shared.Cost;
import com.javadaba.platform.shared.JsonSchema;
import com.javadaba.platform.shared.ProductSlug;

import java.util.Objects;

public record ProductDescriptor(
        ProductSlug slug,
        Version version,
        String displayName,
        String shortDescription,
        JsonSchema inputSchema,
        JsonSchema outputSchema,
        Cost estimatedCost,
        boolean mcpEnabled) {
    public ProductDescriptor {
        Objects.requireNonNull(slug, "slug");
        Objects.requireNonNull(version, "version");
        Objects.requireNonNull(displayName, "displayName");
        Objects.requireNonNull(shortDescription, "shortDescription");
        Objects.requireNonNull(inputSchema, "inputSchema");
        Objects.requireNonNull(outputSchema, "outputSchema");
        Objects.requireNonNull(estimatedCost, "estimatedCost");
    }
}
