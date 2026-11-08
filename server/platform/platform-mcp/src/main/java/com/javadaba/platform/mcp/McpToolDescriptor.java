package com.javadaba.platform.mcp;

import com.javadaba.platform.shared.JsonSchema;

import java.util.Objects;

public record McpToolDescriptor(
        String name,
        String description,
        JsonSchema inputSchema) {
    public McpToolDescriptor {
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(description, "description");
        Objects.requireNonNull(inputSchema, "inputSchema");
    }
}
