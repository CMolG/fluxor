package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.ArrayList;
import java.util.List;

/**
 * The fields an operation's input schema names: the required ones in the order it lists them, then the optional ones.
 * What {@link McpParamAliases} checks a name against, and what an {@code invalid_params} answer tells the agent the
 * operation takes.
 */
record McpInputShape(List<String> required, List<String> optional) {

    static McpInputShape of(JsonNode schema) {
        List<String> required = new ArrayList<>();
        schema.path("required").forEach(name -> required.add(name.asText()));
        List<String> optional = new ArrayList<>();
        schema.path("properties").fieldNames().forEachRemaining(name -> {
            if (!required.contains(name)) {
                optional.add(name);
            }
        });
        return new McpInputShape(List.copyOf(required), List.copyOf(optional));
    }

    boolean declares(String name) {
        return required.contains(name) || optional.contains(name);
    }

    /** For example {@code cards.get takes projectId, keyOrId (required); view (optional)}. */
    String takes(String operation) {
        List<String> parts = new ArrayList<>();
        if (!required.isEmpty()) {
            parts.add(String.join(", ", required) + " (required)");
        }
        if (!optional.isEmpty()) {
            parts.add(String.join(", ", optional) + " (optional)");
        }
        return operation + " takes " + (parts.isEmpty() ? "no params" : String.join("; ", parts));
    }
}
