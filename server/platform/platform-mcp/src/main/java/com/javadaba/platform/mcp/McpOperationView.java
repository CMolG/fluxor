package com.javadaba.platform.mcp;

import java.util.Map;

/** What {@code discover} shows of an operation: everything but the code that runs it. */
public record McpOperationView(String key, String summary, String mode, String scope, Map<String, Object> inputSchema,
        Map<String, Object> example) {
}
