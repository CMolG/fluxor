package com.javadaba.platform.mcp;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * card://JAVA-2004: an agent's call used to answer ONE violation and be refused by names it had no way to know. The
 * validator's messages follow the JVM's language, so these assert on the field names they quote, never on its words.
 */
class McpOperationRegistryTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** An operation that answers the params its handler received, so a test sees what a handler would. */
    private static McpOperation<String> echoing(String key, List<String> required, List<String> optional) {
        Map<String, Object> properties = new LinkedHashMap<>();
        Stream.concat(required.stream(), optional.stream()).forEach(name -> properties.put(name, McpSchemas.string()));
        return new McpOperation<>(key, "Answers its params", McpOperation.READ, "demo:read",
                McpSchemas.schema(properties, required), Map.of(), (caller, params) -> params);
    }

    private static JsonNode json(String text) {
        try {
            return MAPPER.readTree(text);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException(ex);
        }
    }

    private static JsonNode answer(McpOperation<String> op, String params) {
        return (JsonNode) new McpOperationRegistry<>(List.of(op)).query("ana", op.key(), json(params));
    }

    private static McpToolException refusal(McpOperation<String> op, String params) {
        try {
            answer(op, params);
        } catch (McpToolException ex) {
            return ex;
        }
        throw new AssertionError(op.key() + " accepted " + params);
    }

    @Test
    void everyMissingFieldComesBackInOneAnswer() {
        McpOperation<String> get = echoing("cards.get", List.of("projectId", "keyOrId"), List.of("view"));

        McpToolException refused = refusal(get, "{}");

        assertThat(refused.code()).isEqualTo("invalid_params");
        assertThat(refused.getMessage()).contains("'projectId'", "'keyOrId'")
                .endsWith("cards.get takes projectId, keyOrId (required); view (optional)");
        assertThat(refused.path()).isEqualTo("$");
    }

    @Test
    void aWrongTypeAndAMissingFieldAreListedTogetherAndThePathIsTheFirstsOwn() {
        McpOperation<String> add = echoing("notes.add", List.of("title", "text"), List.of());

        McpToolException refused = refusal(add, """
                {"title": 7}""");

        assertThat(refused.getMessage()).contains("$.title", "'text'");
        assertThat(refused.getMessage()).startsWith(refused.path() + ":");
    }

    @Test
    void aCallWithNoParamsAtAllListsEveryRequiredField() {
        McpOperation<String> get = echoing("cards.get", List.of("projectId", "keyOrId"), List.of());

        assertThatThrownBy(() -> new McpOperationRegistry<>(List.of(get)).query("ana", "cards.get", null))
                .isInstanceOf(McpToolException.class).hasMessageContaining("'projectId'")
                .hasMessageContaining("'keyOrId'");
    }

    static Stream<Arguments> operationsAndWhatTheyTake() {
        return Stream.of(
                Arguments.of(List.of("text"), List.of(), "{}", "notes.echo takes text (required)"),
                Arguments.of(List.of(), List.of("folderId", "archived"), "{\"folderId\": 7}",
                        "notes.echo takes folderId, archived (optional)"),
                Arguments.of(List.of(), List.of(), "\"not an object\"", "notes.echo takes no params"));
    }

    @ParameterizedTest
    @MethodSource("operationsAndWhatTheyTake")
    void theAnswerEndsWithWhatTheOperationTakes(List<String> required, List<String> optional, String params,
            String takes) {
        assertThat(refusal(echoing("notes.echo", required, optional), params).getMessage()).endsWith(takes);
    }

    @ParameterizedTest
    @CsvSource({"keyOrId,cardId", "keyOrId,key", "cardId,keyOrId", "cardId,key", "key,keyOrId", "key,cardId",
            "text,body", "modId,id"})
    void aNameAgentsSendIsRenamedToTheOneTheOperationDeclares(String declared, String sent) {
        McpOperation<String> op = echoing("any.op", List.of("projectId", declared), List.of());

        JsonNode seen = answer(op, "{\"projectId\": \"p\", \"" + sent + "\": \"OFF-12\"}");

        assertThat(seen.get(declared).asText()).isEqualTo("OFF-12");
        assertThat(seen.has(sent)).as("%s is gone once renamed", sent).isFalse();
    }

    @Test
    void aFieldTheCallAlreadySendsIsNeverOverridden() {
        McpOperation<String> get = echoing("cards.get", List.of("keyOrId"), List.of());

        JsonNode seen = answer(get, """
                {"keyOrId": "OFF-1", "key": "OFF-2"}""");

        assertThat(seen).isEqualTo(json("""
                {"keyOrId": "OFF-1", "key": "OFF-2"}"""));
    }

    @Test
    void nothingIsRenamedOntoAFieldTheOperationDoesNotDeclare() {
        McpOperation<String> add = echoing("notes.add", List.of("title"), List.of());
        String sent = """
                {"title": "t", "cardId": "OFF-1", "body": "b", "id": "7"}""";

        assertThat(answer(add, sent)).isEqualTo(json(sent));
    }

    @Test
    void twoAliasesAtOnceAreNotGuessedBetween() {
        McpOperation<String> get = echoing("cards.get", List.of("projectId", "keyOrId"), List.of());

        McpToolException refused = refusal(get, """
                {"projectId": "p", "cardId": "OFF-1", "key": "OFF-2"}""");

        assertThat(refused.getMessage()).contains("'keyOrId'").doesNotContain("'projectId'");
    }

    @Test
    void aCardFieldTheOperationDeclaresItselfIsNotAnotherOnesAlias() {
        McpOperation<String> pair = echoing("cards.pair", List.of("cardId", "key"), List.of());

        assertThat(refusal(pair, """
                {"cardId": "OFF-1"}""").getMessage()).contains("'key'").doesNotContain("'cardId'");
    }

    @Test
    void aBodyTheOperationDeclaresItselfIsNotRenamedToText() {
        McpOperation<String> page = echoing("docs.upsert", List.of("text"), List.of("body"));

        assertThat(refusal(page, """
                {"body": "# Title"}""").getMessage()).contains("'text'");
    }

    @Test
    void theCallersNodeIsNeverWrittenTo() {
        McpOperation<String> get = echoing("cards.get", List.of("keyOrId"), List.of());
        JsonNode sent = json("""
                {"key": "OFF-1"}""");

        new McpOperationRegistry<>(List.of(get)).query("ana", "cards.get", sent);

        assertThat(sent).isEqualTo(json("""
                {"key": "OFF-1"}"""));
    }
}
