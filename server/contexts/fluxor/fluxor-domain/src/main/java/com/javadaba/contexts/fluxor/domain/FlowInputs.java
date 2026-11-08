package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Reads a step's {@code inputs} block, which says how the notes in its {@code context} are read
 * ({@code doc://contracts/fluxor-flow} §1), the way {@link FlowLayout} needs it: the type of each
 * note, which notes a step takes as primary input, and the links between notes. Takes a document
 * that already passed {@link FlowDefinitionValidator}.
 */
final class FlowInputs {

    private FlowInputs() {
    }

    /** Note id to its type, for every typed note the document names in any step. */
    static Map<String, String> types(List<Map<String, Object>> steps) {
        Map<String, String> types = new HashMap<>();
        for (Map<String, Object> step : steps) {
            for (Map<?, ?> group : groups(step, "primaryInput", "context")) {
                if (group.get("type") instanceof String type) {
                    notes(group).forEach(id -> types.put(id, type));
                }
            }
        }
        return types;
    }

    /** The note ids a step takes as primary input. */
    static Set<String> primary(Map<String, Object> step) {
        Set<String> primary = new HashSet<>();
        groups(step, "primaryInput").forEach(group -> primary.addAll(notes(group)));
        return primary;
    }

    /** Each pair of notes linked to each other, once, in the order the document first names them. */
    static List<List<String>> links(List<Map<String, Object>> steps) {
        Set<List<String>> links = new LinkedHashSet<>();
        for (Map<String, Object> step : steps) {
            for (Object pair : list(step, "links")) {
                links.add(((List<?>) pair).stream().map(String.class::cast).toList());
            }
        }
        return List.copyOf(links);
    }

    private static List<Map<?, ?>> groups(Map<String, Object> step, String... fields) {
        List<Map<?, ?>> groups = new ArrayList<>();
        for (String field : fields) {
            for (Object group : list(step, field)) {
                if (group instanceof Map<?, ?> map) {
                    groups.add(map);
                }
            }
        }
        return groups;
    }

    private static List<String> notes(Map<?, ?> group) {
        return group.get("notes") instanceof List<?> ids ? ids.stream().map(String.class::cast).toList() : List.of();
    }

    private static List<?> list(Map<String, Object> step, String field) {
        return step.get("inputs") instanceof Map<?, ?> inputs && inputs.get(field) instanceof List<?> list
                ? list
                : List.of();
    }
}
