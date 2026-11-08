package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The designer's canvas as the server reads it: the {@code Flow} v1 shape of
 * {@code packages/apps/fluxor/src/lib/flow.ts} (step and note nodes; link, loop and attachment
 * edges), plus the fields a step or the flow carries only so an imported document survives the
 * round trip ({@code tools}, {@code systemPrompt}, {@code contract}, {@code model}, {@code meta}).
 * Parsed from the JSON map the app sends, never bound by reflection (invariant 8), and stored as
 * that same map: positions, sizes and colours are the app's, so they ride along untouched.
 * Contract: {@code doc://contracts/fluxor-flow}.
 */
public record FlowCanvas(String name, String description, String contextMode, Map<String, Object> meta,
        List<Step> steps, List<Note> notes, List<Edge> edges) {

    public static final int MAX_CANVAS_BYTES = 256 * 1024;

    public static final String PRIMARY_INPUT = "primary-input";
    public static final String READ_CONTEXT = "read-context";

    private static final Set<String> HANDLES = Set.of("top", "right", "bottom", "left");
    private static final Set<String> EDGE_KINDS = Set.of("link", "loop", "attachment");
    private static final Set<String> MODES = Set.of(PRIMARY_INPUT, READ_CONTEXT);

    public record Step(String id, String title, String description, String prompt, String stepType,
            List<String> tools, String systemPrompt, Map<String, Object> contract, String model) {
    }

    /** {@code type} is null when the note has none. */
    public record Note(String id, String text, String type) {
    }

    /** {@code mode} is null on a connection that does not say (a read-context attachment, or any other kind). */
    public record Edge(String id, String source, String target, String kind, Object maxIterations, String mode) {
    }

    public static void validateSize(int byteSize) {
        if (byteSize > MAX_CANVAS_BYTES) {
            throw invalid("The canvas exceeds the " + MAX_CANVAS_BYTES + "-byte cap (" + byteSize + " bytes)");
        }
    }

    /** Reads a canvas, refusing anything that is not one rather than compiling half of it (like the app's {@code parseFlow}). */
    public static FlowCanvas parse(Map<String, Object> canvas) {
        if (canvas == null) {
            throw invalid("'canvas' is required");
        }
        if (!(canvas.get("version") instanceof Number version) || version.intValue() != 1) {
            throw invalid("The canvas is not in a format this server reads (version must be 1)");
        }
        if (!(canvas.get("nodes") instanceof List<?> rawNodes) || !(canvas.get("edges") instanceof List<?> rawEdges)) {
            throw invalid("The canvas needs a 'nodes' and an 'edges' array");
        }
        List<Step> steps = new ArrayList<>();
        List<Note> notes = new ArrayList<>();
        Set<String> ids = new HashSet<>();
        for (Object raw : rawNodes) {
            if (!(raw instanceof Map<?, ?> node) || !(node.get("id") instanceof String id) || id.isBlank()
                    || !ids.add(id)) {
                throw invalid("Every node needs an id of its own");
            }
            for (String field : List.of("x", "y", "width", "height")) {
                if (!(node.get(field) instanceof Number n) || !Double.isFinite(n.doubleValue())) {
                    throw invalid("Node " + id + " has no '" + field + "'");
                }
            }
            switch (node.get("kind") instanceof String kind ? kind : "") {
                case "step" -> steps.add(new Step(id, text(node, "title"), text(node, "description"),
                        text(node, "prompt"), text(node, "stepType"), tools(node), optional(node, "systemPrompt"),
                        map(node, "contract"), optional(node, "model")));
                case "note" -> notes.add(new Note(id, text(node, "text"), noteType(node)));
                default -> throw invalid("Node " + id + " is neither a step nor a note");
            }
        }
        List<Edge> edges = new ArrayList<>();
        for (Object raw : rawEdges) {
            if (!(raw instanceof Map<?, ?> edge) || !(edge.get("id") instanceof String id)
                    || !(edge.get("source") instanceof String source) || !ids.contains(source)
                    || !(edge.get("target") instanceof String target) || !ids.contains(target)
                    || !HANDLES.contains(edge.get("sourceHandle")) || !HANDLES.contains(edge.get("targetHandle"))
                    || !(edge.get("kind") instanceof String kind) || !EDGE_KINDS.contains(kind)) {
                throw invalid("The canvas has a connection this server cannot read");
            }
            edges.add(new Edge(id, source, target, kind, edge.get("maxIterations"), mode(edge)));
        }
        return new FlowCanvas(optional(canvas, "name"), text(canvas, "description"), optional(canvas, "contextMode"),
                map(canvas, "meta"), steps, notes, edges);
    }

    private static String text(Map<?, ?> map, String field) {
        String value = optional(map, field);
        return value == null ? "" : value;
    }

    private static String optional(Map<?, ?> map, String field) {
        Object value = map.get(field);
        if (value != null && !(value instanceof String)) {
            throw invalid("'" + field + "' must be text");
        }
        return (String) value;
    }

    private static String noteType(Map<?, ?> node) {
        String type = optional(node, "type");
        return type == null || type.isBlank() ? null : type;
    }

    private static String mode(Map<?, ?> edge) {
        String mode = optional(edge, "mode");
        if (mode != null && !MODES.contains(mode)) {
            throw invalid("A connection's 'mode' must be primary-input or read-context");
        }
        return mode;
    }

    private static List<String> tools(Map<?, ?> node) {
        Object value = node.get("tools");
        if (value == null) {
            return List.of();
        }
        if (!(value instanceof List<?> list) || !list.stream().allMatch(String.class::isInstance)) {
            throw invalid("A step's 'tools' must be a list of tool names");
        }
        return list.stream().map(String.class::cast).toList();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Map<?, ?> source, String field) {
        Object value = source.get(field);
        if (value != null && !(value instanceof Map<?, ?>)) {
            throw invalid("'" + field + "' must be an object");
        }
        return (Map<String, Object>) value;
    }

    private static FluxorException invalid(String message) {
        return new FluxorException("invalid_flow_canvas", message, 422);
    }
}
