package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * An operation table with the one rule every table shares: a call's {@code params} are validated
 * against the operation's own JSON Schema BEFORE its handler runs, so a handler trusts its input
 * shape and an agent gets every failing field back at once, with what the operation takes
 * (card://JAVA-2004). A name the operation does not declare, but agents send for one it does, is
 * renamed first ({@link McpParamAliases}).
 */
public class McpOperationRegistry<C> {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** An operation's input schema, compiled once, and the fields it names. */
    private record Input(JsonSchema schema, McpInputShape shape) {
    }

    private final List<McpOperation<C>> operations;
    private final Map<String, McpOperation<C>> byKey = new LinkedHashMap<>();
    private final Map<String, Input> inputs = new ConcurrentHashMap<>();

    public McpOperationRegistry(List<McpOperation<C>> operations) {
        this.operations = List.copyOf(operations);
        for (McpOperation<C> op : this.operations) {
            if (byKey.put(op.key(), op) != null) {
                throw new IllegalArgumentException("Duplicate MCP operation key: " + op.key());
            }
        }
    }

    /** Every operation, or those whose key contains {@code filter} or whose mode is it. */
    public List<McpOperation<C>> discover(String filter) {
        if (filter == null || filter.isBlank()) {
            return operations;
        }
        String needle = filter.toLowerCase(Locale.ROOT);
        return operations.stream()
                .filter(o -> o.key().toLowerCase(Locale.ROOT).contains(needle) || o.mode().equals(needle))
                .toList();
    }

    public Optional<McpOperation<C>> find(String key) {
        return Optional.ofNullable(byKey.get(key));
    }

    public Object query(C caller, String key, JsonNode rawParams) {
        McpOperation<C> op = find(key)
                .orElseThrow(() -> new McpToolException("unknown_operation", "No such operation: " + key, "/operation",
                        null));
        Input input = inputs.computeIfAbsent(op.key(), k -> inputOf(op));
        JsonNode params = McpParamAliases.apply(input.shape(),
                rawParams == null || rawParams.isNull() ? MAPPER.createObjectNode() : rawParams);
        var errors = input.schema().validate(params);
        if (!errors.isEmpty()) {
            String violations = errors.stream().map(ValidationMessage::getMessage).collect(Collectors.joining("; "));
            throw McpToolException.invalid(violations + ". " + input.shape().takes(op.key()),
                    errors.iterator().next().getInstanceLocation().toString());
        }
        return op.handler().handle(caller, params);
    }

    private static Input inputOf(McpOperation<?> op) {
        JsonNode document = MAPPER.valueToTree(op.inputSchema());
        return new Input(JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(document),
                McpInputShape.of(document));
    }
}
