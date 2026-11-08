package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

/**
 * One row of an authenticated MCP server's operation table: {@code discover} lists these,
 * {@code query} runs {@link #handler()} by {@link #key()} after validating params against
 * {@link #inputSchema()}. The shape Officium's MCP proved (JDB-220), made generic so every product
 * MCP is a table and not a server.
 *
 * @param mode {@code "read"} or {@code "write"}
 * @param scope the OAuth scope {@code query} requires for this operation
 * @param <C> who is calling, as the product needs it (an account, an account plus an agent name)
 */
public record McpOperation<C>(String key, String summary, String mode, String scope, Map<String, Object> inputSchema,
        Map<String, Object> example, Handler<C> handler) {

    public static final String READ = "read";
    public static final String WRITE = "write";

    public McpOperationView view() {
        return new McpOperationView(key, summary, mode, scope, inputSchema, example);
    }

    /** Calls the same application services REST does: an MCP operation is a door, never a rule. */
    @FunctionalInterface
    public interface Handler<C> {
        Object handle(C caller, JsonNode params);
    }
}
