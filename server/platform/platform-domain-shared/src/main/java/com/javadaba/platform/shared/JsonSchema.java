package com.javadaba.platform.shared;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.SequencedMap;
import java.util.TreeMap;

/**
 * The JSON Schema document of an {@code ActionDescriptor}'s input/output.
 *
 * <h2>The order of the keys is part of the contract</h2>
 *
 * <p>This document isn't consumed only by machines: {@code GET /public/v1/products/{slug}/schema}
 * serializes it as-is, {@code /examples} builds the example body by walking
 * {@code properties} <em>in iteration order</em>, and {@code javadaba-landing}
 * ({@code scripts/generate-api-docs.mjs}, {@code pnpm docs:apis}) materializes from there the
 * field table on every documentation page, which gets committed.
 *
 * <p>That's why a {@code Map.of(...)}/{@code Map.ofEntries(...)} with more than one entry does NOT
 * work for writing a schema: its immutable implementations ({@code ImmutableCollections.MapN})
 * scatter the keys with a <strong>random salt per JVM startup</strong>, so the
 * same descriptor produces a different order in every process. Symptom observed on 2026-08-06:
 * regenerating the docs without touching anything reordered the tables and examples of ~10
 * unrelated files, and whoever regenerated them had to restore them by hand.
 *
 * <p>This type closes the hole in three steps, and there's no need to choose between them:
 * <ol>
 *   <li>a <strong>deep copy that preserves encounter order</strong> (nested maps and
 *   lists included) into immutable {@link LinkedHashMap}s: a schema that declares its order
 *   keeps it intact all the way to the JSON;</li>
 *   <li>a safety net: if a map with more than one entry that does <em>not</em> guarantee
 *   order still gets through (it's not a {@link SequencedMap}), it's sorted
 *   <strong>alphabetically</strong>. It's a poor order —not the one a human would want to read—
 *   but it's <em>stable across restarts</em>, which is the only thing that makes {@code docs:apis}
 *   idempotent. Deliberately, no exception is thrown: that would turn one descriptor's oversight
 *   into a startup failure for the entire API;</li>
 *   <li>{@link #ordered(Object...)} is the correct way to write it, and
 *   {@code ActionDescriptorSchemaOrderTest} (apps/app-api) fails if an {@code ActionDescriptor}
 *   goes back to using {@code Map.of}/{@code Map.ofEntries}.</li>
 * </ol>
 */
public record JsonSchema(Map<String, Object> document) {

    public JsonSchema {
        Objects.requireNonNull(document, "document");
        document = deterministic(document);
    }

    public static JsonSchema object(Map<String, Object> properties, List<String> required) {
        SequencedMap<String, Object> root = new LinkedHashMap<>();
        root.put("type", "object");
        root.put("properties", properties == null ? Map.of() : properties);
        root.put("required", List.copyOf(required));
        return new JsonSchema(root);
    }

    public static JsonSchema emptyObject() {
        return object(Map.of(), List.of());
    }

    /**
     * <strong>Ordered</strong> map literal: the replacement for {@code Map.of(...)} inside a
     * schema. Returns an immutable {@link SequencedMap} that preserves the order the pairs were
     * written in, both at the {@code properties} level and for each field's
     * definition:
     *
     * <pre>{@code
     * JsonSchema.object(JsonSchema.ordered(
     *         "from", JsonSchema.ordered("type", "string", "description", "..."),
     *         "to",   JsonSchema.ordered("type", "string")
     * ), List.of("from", "to"))
     * }</pre>
     *
     * <p>It's also used for single-entry maps even though {@code Map.of} would be harmless there:
     * the rule "no {@code Map.of} appears inside a descriptor" is one that can be checked at a
     * glance (and with a test), and a rule with exceptions doesn't get respected.
     */
    public static SequencedMap<String, Object> ordered(Object... keyValuePairs) {
        if (keyValuePairs.length % 2 != 0) {
            throw new IllegalArgumentException(
                    "JsonSchema.ordered expects key/value pairs, got " + keyValuePairs.length + " arguments");
        }
        SequencedMap<String, Object> map = new LinkedHashMap<>();
        for (int i = 0; i < keyValuePairs.length; i += 2) {
            if (!(keyValuePairs[i] instanceof String key)) {
                throw new IllegalArgumentException("JsonSchema.ordered key at index " + i + " must be a String");
            }
            if (map.containsKey(key)) {
                throw new IllegalArgumentException("JsonSchema.ordered duplicate key: " + key);
            }
            map.put(key, keyValuePairs[i + 1]);
        }
        return Collections.unmodifiableSequencedMap(map);
    }

    /** Deep copy with stable order; see the type's javadoc for why it exists. */
    private static Map<String, Object> deterministic(Map<?, ?> source) {
        Map<?, ?> ordered = source;
        if (source.size() > 1 && !(source instanceof SequencedMap<?, ?>)) {
            // Last resort: alphabetical. Stable across restarts, which is what matters here.
            TreeMap<String, Object> sorted = new TreeMap<>();
            source.forEach((key, value) -> sorted.put(String.valueOf(key), value));
            ordered = sorted;
        }
        SequencedMap<String, Object> copy = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : ordered.entrySet()) {
            copy.put(String.valueOf(entry.getKey()), deterministicValue(entry.getValue()));
        }
        return Collections.unmodifiableSequencedMap(copy);
    }

    private static Object deterministicValue(Object value) {
        if (value instanceof Map<?, ?> nested) {
            return deterministic(nested);
        }
        if (value instanceof List<?> list) {
            return list.stream().map(JsonSchema::deterministicValue).toList();
        }
        return value;
    }
}
