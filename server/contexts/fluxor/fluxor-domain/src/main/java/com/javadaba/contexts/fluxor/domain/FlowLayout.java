package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Lays a {@code fluxor-flow} document out as a designer canvas, so every flow has one to show: an
 * import, an IDE push, a console draft. The inverse of {@link FlowCompiler} over the fields the
 * format names, which is the round trip {@code doc://contracts/fluxor-flow} promises: a step's
 * column is its longest path from the first step, its row its order in that column, and a note (a
 * {@code context} entry) sits above the first step that uses it. Takes a document that already
 * passed {@link FlowDefinitionValidator}.
 */
public final class FlowLayout {

    private static final int STEP_WIDTH = 300;
    private static final int STEP_HEIGHT = 190;
    private static final int NOTE_WIDTH = 200;
    private static final int NOTE_HEIGHT = 140;
    private static final int GAP = 40;
    private static final int COLUMN = STEP_WIDTH + 3 * GAP;
    private static final int ROW = NOTE_HEIGHT + STEP_HEIGHT + 2 * GAP;
    private static final String NOTE_COLOR = "#EDE9FE";

    private FlowLayout() {
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> layout(Map<String, Object> definition, String fallbackName) {
        List<Map<String, Object>> steps = (List<Map<String, Object>>) definition.get("steps");
        Map<String, List<String>> dependsOn = new LinkedHashMap<>();
        for (Map<String, Object> step : steps) {
            dependsOn.put((String) step.get("id"),
                    step.get("dependsOn") instanceof List<?> deps ? (List<String>) deps : List.of());
        }
        Map<String, Integer> column = new HashMap<>();
        for (String stepId : FlowGraph.order(dependsOn.keySet(), dependsOn)) {
            column.put(stepId, dependsOn.get(stepId).stream().mapToInt(dep -> column.get(dep) + 1).max().orElse(0));
        }
        Map<String, String> types = FlowInputs.types(steps);

        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        Map<Integer, Integer> rowsUsed = new HashMap<>();
        Set<String> notesPlaced = new LinkedHashSet<>();
        for (Map<String, Object> step : steps) {
            String stepId = (String) step.get("id");
            int x = column.get(stepId) * COLUMN;
            int y = rowsUsed.merge(column.get(stepId), 1, Integer::sum) * ROW - ROW + NOTE_HEIGHT + GAP;
            nodes.add(stepNode(step, x, y));
            for (String dep : dependsOn.get(stepId)) {
                edges.add(edge("link:" + dep + ":" + stepId, dep, stepId, "right", "left", "link"));
            }
            if (step.get("context") instanceof Map<?, ?> context) {
                Set<String> primary = FlowInputs.primary(step);
                int placedHere = 0;
                for (Map.Entry<?, ?> entry : context.entrySet()) {
                    String key = (String) entry.getKey();
                    String noteId = noteId(key, dependsOn);
                    if (notesPlaced.add(noteId)) {
                        nodes.add(noteNode(noteId, (String) entry.getValue(), types.get(key),
                                x + placedHere++ * (NOTE_WIDTH + GAP / 2), y - NOTE_HEIGHT - GAP));
                    }
                    Map<String, Object> attached = edge("note:" + noteId + ":" + stepId, noteId, stepId,
                            "bottom", "top", "attachment");
                    if (primary.contains(key)) {
                        attached.put("mode", FlowCanvas.PRIMARY_INPUT);
                    }
                    edges.add(attached);
                }
            }
        }
        for (List<String> pair : FlowInputs.links(steps)) {
            String source = noteId(pair.get(0), dependsOn);
            String target = noteId(pair.get(1), dependsOn);
            edges.add(edge("note-link:" + source + ":" + target, source, target, "right", "left", "attachment"));
        }
        if (definition.get("loops") instanceof List<?> loops) {
            for (Object raw : loops) {
                Map<String, Object> loop = (Map<String, Object>) raw;
                Map<String, Object> edge = edge((String) loop.get("id"), (String) loop.get("sourceStepId"),
                        (String) loop.get("targetStepId"), "bottom", "bottom", "loop");
                edge.put("maxIterations", FlowGraph.clampIterations(loop.get("maxIterations")));
                edges.add(edge);
            }
        }

        Map<String, Object> meta = definition.get("meta") instanceof Map<?, ?> m
                ? new LinkedHashMap<>((Map<String, Object>) m)
                : new LinkedHashMap<>();
        Object description = meta.remove("description");
        Map<String, Object> canvas = new LinkedHashMap<>();
        canvas.put("version", 1);
        canvas.put("name", definition.get("name") instanceof String name && !name.isBlank() ? name : fallbackName);
        canvas.put("description", description instanceof String text ? text : "");
        canvas.put("contextMode", "feedback".equals(definition.get("contextMode")) ? "feedback" : "blind");
        canvas.put("nodes", nodes);
        canvas.put("edges", edges);
        if (!meta.isEmpty()) {
            canvas.put("meta", meta);
        }
        return canvas;
    }

    private static Map<String, Object> stepNode(Map<String, Object> step, int x, int y) {
        Map<String, Object> node = new LinkedHashMap<>();
        node.put("id", step.get("id"));
        node.put("kind", "step");
        node.put("x", x);
        node.put("y", y);
        node.put("width", STEP_WIDTH);
        node.put("height", STEP_HEIGHT);
        node.put("title", textOrEmpty(step.get("title")));
        node.put("description", textOrEmpty(step.get("description")));
        node.put("prompt", textOrEmpty(step.get("prompt")));
        node.put("stepType", step.get("type") instanceof String type ? type : "llm_call");
        for (String field : List.of("tools", "systemPrompt", "contract", "model")) {
            if (step.get(field) != null) {
                node.put(field, step.get(field));
            }
        }
        return node;
    }

    /** A context key that is also a step's id cannot be a node's id too. */
    private static String noteId(String key, Map<String, List<String>> dependsOn) {
        return dependsOn.containsKey(key) ? "note:" + key : key;
    }

    private static Map<String, Object> noteNode(String id, String text, String type, int x, int y) {
        Map<String, Object> node = new LinkedHashMap<>();
        node.put("id", id);
        node.put("kind", "note");
        node.put("x", x);
        node.put("y", y);
        node.put("width", NOTE_WIDTH);
        node.put("height", NOTE_HEIGHT);
        node.put("text", text);
        if (type != null) {
            node.put("type", type);
        }
        node.put("color", NOTE_COLOR);
        node.put("shape", "square");
        return node;
    }

    private static Map<String, Object> edge(String id, String source, String target, String sourceHandle,
            String targetHandle, String kind) {
        Map<String, Object> edge = new LinkedHashMap<>();
        edge.put("id", id);
        edge.put("source", source);
        edge.put("target", target);
        edge.put("sourceHandle", sourceHandle);
        edge.put("targetHandle", targetHandle);
        edge.put("kind", kind);
        return edge;
    }

    private static String textOrEmpty(Object value) {
        return value instanceof String text ? text : "";
    }
}
