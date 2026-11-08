package com.javadaba.platform.mcp;

import com.javadaba.platform.shared.JsonSchema;

import java.util.List;
import java.util.Map;
import java.util.SequencedMap;

/** Builders for operation input schemas over {@link JsonSchema#ordered}: deterministic key order,
 *  so {@code discover} answers the same bytes every time. */
public final class McpSchemas {

    private McpSchemas() {
    }

    public static SequencedMap<String, Object> string() {
        return JsonSchema.ordered("type", "string");
    }

    public static SequencedMap<String, Object> stringEnum(String... values) {
        return JsonSchema.ordered("type", "string", "enum", List.of(values));
    }

    public static SequencedMap<String, Object> integer() {
        return JsonSchema.ordered("type", "integer");
    }

    public static SequencedMap<String, Object> number() {
        return JsonSchema.ordered("type", "number");
    }

    public static SequencedMap<String, Object> bool() {
        return JsonSchema.ordered("type", "boolean");
    }

    public static SequencedMap<String, Object> object() {
        return JsonSchema.ordered("type", "object");
    }

    public static SequencedMap<String, Object> array(Object items) {
        return JsonSchema.ordered("type", "array", "items", items);
    }

    public static SequencedMap<String, Object> objectOf(Map<String, Object> properties, List<String> required) {
        return JsonSchema.ordered("type", "object", "properties", properties, "required", required);
    }

    public static Map<String, Object> schema(Map<String, Object> properties, List<String> required) {
        return JsonSchema.object(properties, required).document();
    }
}
