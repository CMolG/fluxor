package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.List;

/**
 * The one JSON-RPC 2.0 transport every authenticated MCP of this API speaks (Officium's since
 * JDB-220, the APIs', one per product next): stateless POST, the streamable-HTTP subset real
 * clients use ({@code initialize}, {@code notifications/initialized} -&gt; 202, {@code ping},
 * {@code tools/list}, {@code tools/call}), and exactly two tools, {@code discover} and
 * {@code query}.
 *
 * <p>It knows nothing of HTTP or OAuth. The product's resource authenticates the request, then
 * hands this server a {@link Backend} already bound to that caller -- so no request can ever see
 * another's principal, which is why this is a plain class and not a library-managed MCP session.
 */
public final class McpJsonRpcServer {

    private static final String PROTOCOL_VERSION = "2025-06-18";

    private final String serverName;
    private final String product;
    private final ObjectMapper mapper;
    private final String instructions;

    /** @param product how the tool descriptions name the product ("Officium", "Javadaba's APIs") */
    public McpJsonRpcServer(String serverName, String product, ObjectMapper mapper) {
        this(serverName, product, mapper, null);
    }

    /**
     * @param instructions what {@code initialize} tells the client about using this server, which
     *     clients hand the model (the spec's {@code InitializeResult.instructions}); null for none
     */
    public McpJsonRpcServer(String serverName, String product, ObjectMapper mapper, String instructions) {
        this.serverName = serverName;
        this.product = product;
        this.mapper = mapper;
        this.instructions = instructions;
    }

    /** What the caller can see and run. {@code query} checks the operation's scope itself: it
     *  only learns which scope applies once it knows the operation. */
    public interface Backend {
        List<McpOperationView> discover(String filter);

        Object query(String operation, JsonNode params);
    }

    /** @param status 200 with a JSON-RPC envelope, or 202 with no body for a notification */
    public record Reply(int status, JsonNode body) {
    }

    public Reply handle(JsonNode body, Backend backend) {
        if (body == null || !body.hasNonNull("method")) {
            return new Reply(200, error(body != null && body.has("id") ? body.get("id") : null, -32600,
                    "Invalid Request"));
        }
        JsonNode id = body.get("id");
        String method = body.get("method").asText();
        if (id == null || id.isNull()) {
            return new Reply(202, null);
        }
        ObjectNode result = switch (method) {
            case "initialize" -> initialize(body.get("params"));
            case "ping" -> mapper.createObjectNode();
            case "tools/list" -> toolsList();
            case "tools/call" -> toolsCall(backend, body.get("params"));
            default -> null;
        };
        return new Reply(200, result == null ? error(id, -32601, "Method not found: " + method) : envelope(id, result));
    }

    private ObjectNode initialize(JsonNode params) {
        ObjectNode result = mapper.createObjectNode();
        result.put("protocolVersion", params != null && params.hasNonNull("protocolVersion")
                ? params.get("protocolVersion").asText()
                : PROTOCOL_VERSION);
        result.putObject("capabilities").putObject("tools");
        ObjectNode serverInfo = result.putObject("serverInfo");
        serverInfo.put("name", serverName);
        serverInfo.put("version", "1.0.0");
        if (instructions != null) {
            result.put("instructions", instructions);
        }
        return result;
    }

    private ObjectNode toolsList() {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode tools = result.putArray("tools");
        ObjectNode discover = tool(tools, "discover", "Lists " + product + "'s operations (key, summary, mode, "
                + "scope, input schema, example). Call this first, then use `query` with one of the returned keys.");
        discover.putObject("properties").putObject("filter").put("type", "string");
        discover.putArray("required");
        ObjectNode query = tool(tools, "query", "Runs one " + product + " operation by key with its params, "
                + "returning that operation's JSON result -- the SAME data REST returns for the same account.");
        ObjectNode properties = query.putObject("properties");
        properties.putObject("operation").put("type", "string");
        properties.putObject("params").put("type", "object");
        query.putArray("required").add("operation");
        return result;
    }

    /** Adds a tool descriptor and returns its (still empty) input schema. */
    private ObjectNode tool(ArrayNode tools, String name, String description) {
        ObjectNode node = tools.addObject();
        node.put("name", name);
        node.put("description", description);
        ObjectNode schema = node.putObject("inputSchema");
        schema.put("type", "object");
        return schema;
    }

    private ObjectNode toolsCall(Backend backend, JsonNode params) {
        if (params == null || !params.hasNonNull("name")) {
            return toolError(McpToolException.invalid("tools/call needs a tool name", "/name"));
        }
        JsonNode arguments = params.get("arguments");
        try {
            return switch (params.get("name").asText()) {
                case "discover" -> toolSuccess(discover(backend, arguments));
                case "query" -> {
                    if (arguments == null || !arguments.hasNonNull("operation")) {
                        throw McpToolException.invalid("query needs an operation key", "/operation");
                    }
                    yield toolSuccess(mapper.valueToTree(
                            backend.query(arguments.get("operation").asText(), arguments.get("params"))));
                }
                default -> throw new McpToolException("unknown_tool", "No such tool: " + params.get("name").asText(),
                        "/name", null);
            };
        } catch (McpToolException ex) {
            return toolError(ex);
        }
    }

    private ObjectNode discover(Backend backend, JsonNode arguments) {
        String filter = arguments != null && arguments.hasNonNull("filter") ? arguments.get("filter").asText() : null;
        ObjectNode payload = mapper.createObjectNode();
        ArrayNode operations = payload.putArray("operations");
        backend.discover(filter).forEach(op -> operations.add(mapper.valueToTree(op)));
        return payload;
    }

    private ObjectNode toolSuccess(JsonNode structured) {
        ObjectNode result = mapper.createObjectNode();
        result.putArray("content").addObject().put("type", "text").put("text", structured.toString());
        // The spec types structuredContent as an object, so a list result is wrapped as {items};
        // the text block keeps the raw value.
        if (structured.isObject()) {
            result.set("structuredContent", structured);
        } else if (structured.isArray()) {
            result.putObject("structuredContent").set("items", structured);
        }
        result.put("isError", false);
        return result;
    }

    /** Clients hand the model the content blocks, not extra result fields: the code, the path and
     *  the state to merge onto must travel in the text. */
    private ObjectNode toolError(McpToolException ex) {
        ObjectNode detail = mapper.createObjectNode();
        detail.put("error", ex.code());
        detail.put("message", ex.getMessage() == null ? ex.code() : ex.getMessage());
        if (ex.path() != null) {
            detail.put("path", ex.path());
        }
        if (ex.current() != null) {
            detail.set("current", ex.current());
        }
        if (ex.at() != null) {
            detail.put("at", ex.at());
        }
        ObjectNode result = mapper.createObjectNode();
        result.putArray("content").addObject().put("type", "text").put("text", detail.toString());
        result.set("structuredContent", detail.deepCopy());
        result.put("isError", true);
        result.setAll(detail);
        return result;
    }

    private ObjectNode envelope(JsonNode id, ObjectNode result) {
        ObjectNode envelope = mapper.createObjectNode();
        envelope.put("jsonrpc", "2.0");
        envelope.set("id", id);
        envelope.set("result", result);
        return envelope;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode envelope = mapper.createObjectNode();
        envelope.put("jsonrpc", "2.0");
        envelope.set("id", id == null ? mapper.nullNode() : id);
        ObjectNode error = envelope.putObject("error");
        error.put("code", code);
        error.put("message", message);
        return envelope;
    }
}
