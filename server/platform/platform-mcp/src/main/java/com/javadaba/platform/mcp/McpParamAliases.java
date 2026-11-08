package com.javadaba.platform.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.List;

/**
 * Agents name the same parameter differently from one operation to the next, and every wrong guess costs a round trip
 * (card://JAVA-2004: 102 of 418 {@code query} calls failed over 39 sessions, most on a card called {@code key} where
 * the operation said {@code keyOrId}). So before a call is validated, a name the operation does not declare is
 * renamed to the one it does, from {@link #TABLE}: the only place these names are written.
 *
 * <p>It renames only when the answer is certain. The operation declares the name, the call lacks it, and the call
 * carries exactly one of its aliases, none of which the operation declares itself: a name an operation knows is that
 * operation's own parameter, never an alias. What the call already sends is never overridden, and a name the
 * operation does not declare is never invented.
 */
final class McpParamAliases {

    /** What an operation may declare, and the other names agents send for the same thing. */
    private record Alias(String declared, List<String> sent) {
    }

    private static final List<Alias> TABLE = List.of(
            // A card is named by its key ("OFF-12") or its id, and Officium's operations spell that three ways.
            new Alias("keyOrId", List.of("cardId", "key")),
            new Alias("cardId", List.of("keyOrId", "key")),
            new Alias("key", List.of("keyOrId", "cardId")),
            new Alias("text", List.of("body")),
            new Alias("modId", List.of("id")));

    private McpParamAliases() {
    }

    /** {@code params} with the aliases renamed; a copy, because the caller's node is never written to. */
    static JsonNode apply(McpInputShape shape, JsonNode params) {
        if (!params.isObject()) {
            return params;
        }
        ObjectNode renamed = params.deepCopy();
        for (Alias alias : TABLE) {
            if (!shape.declares(alias.declared()) || renamed.hasNonNull(alias.declared())) {
                continue;
            }
            List<String> carried = alias.sent().stream()
                    .filter(name -> !shape.declares(name) && renamed.hasNonNull(name)).toList();
            if (carried.size() == 1) {
                renamed.set(alias.declared(), renamed.remove(carried.getFirst()));
            }
        }
        return renamed;
    }
}
