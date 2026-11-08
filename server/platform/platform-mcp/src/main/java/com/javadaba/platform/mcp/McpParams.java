package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Reads a {@code query}'s {@code params} after {@link McpOperationRegistry} validated them: the
 *  helpers exist for optional fields and for what a JSON Schema cannot express (UUIDs). */
public final class McpParams {

    private McpParams() {
    }

    public static UUID uuid(JsonNode params, String field) {
        UUID value = optionalUuid(params, field);
        if (value == null) {
            throw McpToolException.invalid(field + " is required", "/" + field);
        }
        return value;
    }

    public static UUID optionalUuid(JsonNode params, String field) {
        String raw = string(params, field, null);
        if (raw == null) {
            return null;
        }
        try {
            return UUID.fromString(raw);
        } catch (IllegalArgumentException ex) {
            throw McpToolException.invalid(field + " must be a UUID", "/" + field);
        }
    }

    public static String string(JsonNode params, String field, String fallback) {
        return params == null || !params.hasNonNull(field) ? fallback : params.get(field).asText();
    }

    public static String requiredString(JsonNode params, String field) {
        String value = string(params, field, null);
        if (value == null || value.isBlank()) {
            throw McpToolException.invalid(field + " is required", "/" + field);
        }
        return value;
    }

    // These three read like the others above but CANNOT use their ternary shape: with a null
    // `fallback`, `cond ? fallback : params.get(field).asInt()` unifies to the primitive type
    // (JLS 15.25 binary numeric promotion) and unboxes `fallback` to compare branch types even
    // when the `fallback` branch is the one taken, throwing an NPE. Officium's callers rely on a
    // null fallback (an absent `order`/`estimate` left untouched), so this is a real path, not a
    // theoretical one.
    public static Integer integer(JsonNode params, String field, Integer fallback) {
        if (params == null || !params.hasNonNull(field)) {
            return fallback;
        }
        return params.get(field).asInt();
    }

    public static Double number(JsonNode params, String field, Double fallback) {
        if (params == null || !params.hasNonNull(field)) {
            return fallback;
        }
        return params.get(field).asDouble();
    }

    public static Boolean bool(JsonNode params, String field, Boolean fallback) {
        if (params == null || !params.hasNonNull(field)) {
            return fallback;
        }
        return params.get(field).asBoolean();
    }

    public static List<String> stringArray(JsonNode params, String field) {
        List<String> result = new ArrayList<>();
        if (params != null && params.hasNonNull(field)) {
            params.get(field).forEach(item -> result.add(item.asText()));
        }
        return result;
    }
}
