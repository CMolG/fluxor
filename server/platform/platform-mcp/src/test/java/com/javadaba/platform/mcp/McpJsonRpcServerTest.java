package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class McpJsonRpcServerTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final McpOperationRegistry<String> table = new McpOperationRegistry<>(List.of(
            new McpOperation<>("notes.echo", "Echoes the text", McpOperation.READ, "demo:read",
                    McpSchemas.schema(Map.of("text", McpSchemas.string()), List.of("text")), Map.of("text", "hi"),
                    (caller, params) -> Map.of("caller", caller, "text", params.get("text").asText())),
            new McpOperation<>("notes.fail", "Always refuses", McpOperation.WRITE, "demo:write",
                    McpSchemas.schema(Map.of(), List.of()), Map.of(),
                    (caller, params) -> {
                        throw new McpToolException("version_conflict", "Changed meanwhile", null,
                                MAPPER.valueToTree(Map.of("version", 7)));
                    })));
    private final McpJsonRpcServer server = new McpJsonRpcServer("demo", "Demo", MAPPER);
    private final McpJsonRpcServer.Backend backend = new McpJsonRpcServer.Backend() {
        @Override
        public List<McpOperationView> discover(String filter) {
            return table.discover(filter).stream().map(McpOperation::view).toList();
        }

        @Override
        public Object query(String operation, JsonNode params) {
            return table.query("ana", operation, params);
        }
    };

    @Test
    void initializeNamesTheServerAndEchoesTheClientsProtocol() {
        JsonNode result = call("initialize", Map.of("protocolVersion", "2025-03-26")).get("result");

        assertThat(result.get("protocolVersion").asText()).isEqualTo("2025-03-26");
        assertThat(result.at("/serverInfo/name").asText()).isEqualTo("demo");
        assertThat(result.has("instructions")).as("a server with none says nothing").isFalse();
    }

    @Test
    void initializeCarriesTheServersInstructionsForTheModel() {
        McpJsonRpcServer guided = new McpJsonRpcServer("demo", "Demo", MAPPER, "Ask before installing.");
        McpJsonRpcServer.Reply reply = guided.handle(MAPPER.valueToTree(
                Map.of("jsonrpc", "2.0", "id", 1, "method", "initialize", "params", Map.of())), backend);

        assertThat(reply.body().at("/result/instructions").asText()).isEqualTo("Ask before installing.");
    }

    @Test
    void theToolsAreExactlyDiscoverAndQuery() {
        JsonNode tools = call("tools/list", Map.of()).at("/result/tools");

        assertThat(tools).extracting(t -> t.get("name").asText()).containsExactly("discover", "query");
        assertThat(tools.get(0).get("description").asText()).startsWith("Lists Demo's operations");
    }

    @Test
    void queryRunsTheOperationForTheBoundCaller() {
        JsonNode result = tool("query", Map.of("operation", "notes.echo", "params", Map.of("text", "hello")));

        assertThat(result.get("isError").asBoolean()).isFalse();
        assertThat(result.at("/structuredContent/caller").asText()).isEqualTo("ana");
        assertThat(result.at("/structuredContent/text").asText()).isEqualTo("hello");
    }

    @Test
    void paramsThatBreakTheSchemaComeBackAsAToolErrorWithThePath() {
        JsonNode result = tool("query", Map.of("operation", "notes.echo", "params", Map.of()));

        assertThat(result.get("isError").asBoolean()).isTrue();
        assertThat(result.get("error").asText()).isEqualTo("invalid_params");
        assertThat(result.at("/content/0/text").asText()).contains("invalid_params");
    }

    /** card://JAVA-2004: the agent reads what the operation takes in the same text block as the violation. */
    @Test
    void theToolErrorKeepsItsShapeAndEndsWithWhatTheOperationTakes() {
        JsonNode result = tool("query", Map.of("operation", "notes.echo", "params", Map.of()));

        assertThat(result.get("message").asText()).contains("'text'").endsWith("notes.echo takes text (required)");
        assertThat(result.get("path").asText()).isEqualTo("$");
        assertThat(result.at("/structuredContent/message").asText()).isEqualTo(result.get("message").asText());
    }

    @Test
    void aDomainRefusalTravelsWithTheStateToMergeOnto() {
        JsonNode result = tool("query", Map.of("operation", "notes.fail"));

        assertThat(result.get("error").asText()).isEqualTo("version_conflict");
        assertThat(result.at("/current/version").asInt()).isEqualTo(7);
    }

    @Test
    void discoverListsTheTableAndFiltersByMode() {
        JsonNode all = tool("discover", Map.of());
        JsonNode writes = tool("discover", Map.of("filter", "write"));

        assertThat(all.at("/structuredContent/operations")).hasSize(2);
        assertThat(writes.at("/structuredContent/operations/0/key").asText()).isEqualTo("notes.fail");
    }

    @Test
    void aNotificationIsAcceptedWithNoBodyAndAnUnknownMethodIsAJsonRpcError() {
        McpJsonRpcServer.Reply notification = server.handle(
                MAPPER.valueToTree(Map.of("jsonrpc", "2.0", "method", "notifications/initialized")), backend);

        assertThat(notification.status()).isEqualTo(202);
        assertThat(call("resources/list", Map.of()).at("/error/code").asInt()).isEqualTo(-32601);
    }

    private JsonNode tool(String name, Map<String, Object> arguments) {
        return call("tools/call", Map.of("name", name, "arguments", arguments)).get("result");
    }

    private JsonNode call(String method, Map<String, Object> params) {
        McpJsonRpcServer.Reply reply = server.handle(
                MAPPER.valueToTree(Map.of("jsonrpc", "2.0", "id", 1, "method", method, "params", params)), backend);
        assertThat(reply.status()).isEqualTo(200);
        return reply.body();
    }
}
