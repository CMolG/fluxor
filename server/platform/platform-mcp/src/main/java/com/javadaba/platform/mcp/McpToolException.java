package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * A {@code query} that failed in a way the agent must read: it becomes a tool result with
 * {@code isError: true}, never a JSON-RPC error, because MCP clients hand the model the tool
 * result and swallow protocol errors.
 *
 * @param path JSON pointer into {@code params} when a field is to blame, else null
 * @param current the state the agent has to merge onto (a version conflict), else null
 * @param at the character offset a query failed to parse at (a product's own query language,
 *     e.g. Officium's OQL, JDB-270), else null
 */
public class McpToolException extends RuntimeException {

    private final String code;
    private final String path;
    private final transient JsonNode current;
    private final Integer at;

    public McpToolException(String code, String message) {
        this(code, message, null, null);
    }

    public McpToolException(String code, String message, String path, JsonNode current) {
        this(code, message, path, current, null);
    }

    public McpToolException(String code, String message, String path, JsonNode current, Integer at) {
        super(message);
        this.code = code;
        this.path = path;
        this.current = current;
        this.at = at;
    }

    public static McpToolException invalid(String message, String path) {
        return new McpToolException("invalid_params", message, path, null);
    }

    public String code() {
        return code;
    }

    public String path() {
        return path;
    }

    public JsonNode current() {
        return current;
    }

    public Integer at() {
        return at;
    }
}
