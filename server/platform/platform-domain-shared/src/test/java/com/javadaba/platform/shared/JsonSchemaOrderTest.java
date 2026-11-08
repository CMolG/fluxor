package com.javadaba.platform.shared;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The ordering contract of {@link JsonSchema}: what makes
 * {@code pnpm --filter javadaba-landing docs:apis} idempotent.
 */
class JsonSchemaOrderTest {

    @Test
    void keepsTheDeclaredOrderOfProperties() {
        JsonSchema schema = JsonSchema.object(JsonSchema.ordered(
                "from", JsonSchema.ordered("type", "string", "description", "quien envia"),
                "to", JsonSchema.ordered("type", "string"),
                "subject", JsonSchema.ordered("type", "string"),
                "html", JsonSchema.ordered("type", "string")), List.of("from", "to", "subject"));

        assertThat(properties(schema)).containsExactly("from", "to", "subject", "html");
        // Also inside each field's definition: 'type' before 'description'.
        assertThat(keysOf(properties(schema, "from"))).containsExactly("type", "description");
        // And at the root: type, properties, required.
        assertThat(schema.document().keySet()).containsExactly("type", "properties", "required");
    }

    @Test
    void sortsAnUnorderedMapSoTheOutputIsStableAcrossJvmRuns() {
        // Map.of scatters the keys with a random salt per JVM startup: without the safety net,
        // the same descriptor would publish a different order in every process.
        JsonSchema schema = JsonSchema.object(Map.of(
                "zulu", Map.of("type", "string"),
                "alfa", Map.of("type", "string"),
                "mike", Map.of("type", "string")), List.of());

        assertThat(properties(schema)).containsExactly("alfa", "mike", "zulu");
    }

    @Test
    void copyingAnAlreadyNormalizedSchemaDoesNotReorderIt() {
        JsonSchema original = JsonSchema.object(JsonSchema.ordered(
                "zulu", JsonSchema.ordered("type", "string"),
                "alfa", JsonSchema.ordered("type", "string")), List.of());

        JsonSchema copy = new JsonSchema(original.document());

        assertThat(properties(copy)).containsExactly("zulu", "alfa");
    }

    @Test
    void nestedListsAndMapsAreNormalizedToo() {
        JsonSchema schema = JsonSchema.object(JsonSchema.ordered(
                "tags", JsonSchema.ordered("type", "array", "items", Map.of(
                        "zulu", "1", "alfa", "2"))),
                List.of());

        Object items = ((Map<?, ?>) properties(schema, "tags")).get("items");
        assertThat(keysOf(items)).containsExactly("alfa", "zulu");
    }

    @Test
    void theDocumentIsImmutable() {
        JsonSchema schema = JsonSchema.object(JsonSchema.ordered("a", JsonSchema.ordered("type", "string")),
                List.of("a"));

        assertThatThrownBy(() -> schema.document().put("boom", "x"))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void orderedRejectsMalformedInput() {
        assertThatThrownBy(() -> JsonSchema.ordered("dangling"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> JsonSchema.ordered("a", 1, "a", 2))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("duplicate");
        assertThatThrownBy(() -> JsonSchema.ordered(1, "a"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static List<String> properties(JsonSchema schema) {
        return keysOf(schema.document().get("properties"));
    }

    private static Object properties(JsonSchema schema, String name) {
        return ((Map<?, ?>) schema.document().get("properties")).get(name);
    }

    private static List<String> keysOf(Object map) {
        return ((Map<?, ?>) map).keySet().stream().map(String::valueOf).toList();
    }
}
