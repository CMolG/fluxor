package com.javadaba.platform.mcp;

public final class McpToolName {
    private McpToolName() {
    }

    public static String fromProductSlug(String slug) {
        return slug.replace('-', '_');
    }
}
