package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Validates a {@code fluxor-flow} interchange document as a CONTRACT OF DATA, not of execution --
 * same pattern as {@code SduiDocument} (#6): the server never runs a flow, it only checks the
 * shape is internally consistent before storing/relaying it (plan #19, Task 5 Step 1). Operates
 * on an already-parsed {@code Map<String, Object>} (no JSON parser dependency in this module --
 * see {@code FlowSyncService}, which parses the request body via Jackson before calling here and
 * ALSO enforces the {@link #MAX_DEFINITION_BYTES} size cap by re-serializing, since the original
 * raw byte count isn't preserved past JAX-RS body deserialization).
 *
 * <p>Golden fixture: {@code ../fluxor/fluxor-ide/sdk/conformance/conformance-chain.flow.json}
 * (READ-ONLY reference) -- a COPY lives at {@code fluxor-infrastructure/src/test/resources/
 * flow-fixtures/conformance-chain.flow.json} and must validate cleanly (see the infrastructure-
 * layer golden test, which is where Jackson parsing of the actual file happens).
 */
public final class FlowDefinitionValidator {

    public static final int MAX_DEFINITION_BYTES = 256 * 1024;

    private FlowDefinitionValidator() {
    }

    public static void validateSize(int byteSize) {
        if (byteSize > MAX_DEFINITION_BYTES) {
            throw new FluxorException("invalid_flow_definition",
                    "Flow definition exceeds the " + MAX_DEFINITION_BYTES + "-byte cap (" + byteSize + " bytes)", 422);
        }
    }

    @SuppressWarnings("unchecked")
    public static void validateStructure(Map<String, Object> definition) {
        if (definition == null) {
            throw new FluxorException("invalid_flow_definition", "Flow definition must not be null", 422);
        }
        Object stepsRaw = definition.get("steps");
        if (!(stepsRaw instanceof List<?> stepsList) || stepsList.isEmpty()) {
            throw new FluxorException("invalid_flow_definition", "Flow definition requires a non-empty 'steps' array",
                    422);
        }

        Map<String, List<String>> dependsOnById = new LinkedHashMap<>();
        for (Object rawStep : stepsList) {
            if (!(rawStep instanceof Map<?, ?> stepMap)) {
                throw new FluxorException("invalid_flow_definition", "Each entry in 'steps' must be an object", 422);
            }
            Object idRaw = stepMap.get("id");
            if (!(idRaw instanceof String id) || id.isBlank()) {
                throw new FluxorException("invalid_flow_definition", "Every step requires a non-blank 'id'", 422);
            }
            if (dependsOnById.containsKey(id)) {
                throw new FluxorException("invalid_flow_definition", "steps[].id: duplicate step id '" + id + "'", 422);
            }
            List<String> dependsOn = extractDependsOn(id, stepMap.get("dependsOn"));
            dependsOnById.put(id, dependsOn);
        }

        for (Map.Entry<String, List<String>> entry : dependsOnById.entrySet()) {
            for (String dep : entry.getValue()) {
                if (!dependsOnById.containsKey(dep)) {
                    throw new FluxorException("invalid_flow_definition",
                            "steps[id=" + entry.getKey() + "].dependsOn references unknown step '" + dep + "'", 422);
                }
            }
        }

        detectCycle(dependsOnById);
        validateFormat(definition, (List<Object>) stepsList, dependsOnById);
    }

    /**
     * The rest of {@code fluxor-flow} v1 ({@code doc://contracts/fluxor-flow}): every field the
     * format names has its type, the first step depends on nothing, and loops follow the same rules
     * {@link FlowCompiler} applies. A field it does not name is carried, never refused, and so is
     * any {@code format} tag: an absent one or {@code heliox-flow} (the product's former name,
     * kept because it is written in users' exported files) is the legacy export, which the
     * runtimes still read.
     */
    @SuppressWarnings("unchecked")
    private static void validateFormat(Map<String, Object> definition, List<Object> steps,
            Map<String, List<String>> dependsOnById) {
        if (definition.containsKey("version") && !FlowCompiler.FORMAT_VERSION.equals(definition.get("version"))) {
            throw invalid("'version' must be \"1\"");
        }
        requireType(definition, "", "format", String.class);
        requireType(definition, "", "id", String.class);
        requireType(definition, "", "name", String.class);
        requireType(definition, "", "contextMode", String.class);
        requireType(definition, "", "meta", Map.class);
        for (Object raw : steps) {
            Map<String, Object> step = (Map<String, Object>) raw;
            String where = "steps[id=" + step.get("id") + "].";
            for (String field : List.of("type", "prompt", "title", "description", "systemPrompt", "model")) {
                requireType(step, where, field, String.class);
            }
            requireType(step, where, "contract", Map.class);
            if (step.get("tools") != null && !(step.get("tools") instanceof List<?> tools
                    && tools.stream().allMatch(String.class::isInstance))) {
                throw invalid(where + "tools must be an array of tool names");
            }
            if (step.get("context") != null && !(step.get("context") instanceof Map<?, ?> context
                    && context.values().stream().allMatch(String.class::isInstance))) {
                throw invalid(where + "context must map each note id to its text");
            }
            validateInputs(where, step.get("inputs"),
                    step.get("context") instanceof Map<?, ?> context ? context : Map.of());
        }
        if (definition.get("rootStepId") != null) {
            if (!(definition.get("rootStepId") instanceof String root) || !dependsOnById.containsKey(root)) {
                throw invalid("rootStepId must name one of the steps");
            }
            if (!dependsOnById.get(root).isEmpty()) {
                throw invalid("rootStepId '" + root + "' depends on other steps, so it cannot be the first");
            }
        }
        validateLoops(definition.get("loops"), dependsOnById);
    }

    /**
     * {@code inputs} says how the notes in {@code context} are read: its groups name notes the context
     * holds, and its links name two of them. Absent, it says nothing new.
     */
    private static void validateInputs(String where, Object raw, Map<?, ?> context) {
        if (raw == null) {
            return;
        }
        if (!(raw instanceof Map<?, ?> inputs)) {
            throw invalid(where + "inputs must be an object");
        }
        for (String field : List.of("primaryInput", "context")) {
            if (inputs.get(field) != null && !(inputs.get(field) instanceof List<?> groups
                    && groups.stream().allMatch(group -> isGroup(group, context)))) {
                throw invalid(where + "inputs." + field + " must be groups of notes the step's context holds");
            }
        }
        if (inputs.get("links") != null && !(inputs.get("links") instanceof List<?> links
                && links.stream().allMatch(link -> link instanceof List<?> pair && pair.size() == 2
                        && pair.stream().allMatch(context::containsKey)))) {
            throw invalid(where + "inputs.links must be pairs of notes the step's context holds");
        }
    }

    private static boolean isGroup(Object raw, Map<?, ?> context) {
        return raw instanceof Map<?, ?> group && (group.get("type") == null || group.get("type") instanceof String)
                && group.get("notes") instanceof List<?> notes && notes.stream().allMatch(context::containsKey);
    }

    private static void validateLoops(Object raw, Map<String, List<String>> dependsOnById) {
        if (raw == null) {
            return;
        }
        if (!(raw instanceof List<?> rawLoops)) {
            throw invalid("'loops' must be an array");
        }
        List<FlowGraph.Loop> loops = new ArrayList<>();
        Set<String> ids = new LinkedHashSet<>();
        for (Object item : rawLoops) {
            if (!(item instanceof Map<?, ?> loop) || !(loop.get("id") instanceof String id) || !ids.add(id)) {
                throw invalid("Every loop needs an id of its own");
            }
            if (!(loop.get("sourceStepId") instanceof String source) || !dependsOnById.containsKey(source)
                    || !(loop.get("targetStepId") instanceof String target) || !dependsOnById.containsKey(target)) {
                throw invalid("loops[id=" + id + "] must run between two of the flow's steps");
            }
            if (!(loop.get("maxIterations") instanceof Integer passes) || passes < 1
                    || passes > FlowGraph.LOOP_MAX_ITERATIONS) {
                throw invalid("loops[id=" + id + "].maxIterations must be a whole number from 1 to "
                        + FlowGraph.LOOP_MAX_ITERATIONS);
            }
            loops.add(new FlowGraph.Loop(id, source, target));
        }
        Map<String, List<String>> next = new LinkedHashMap<>();
        dependsOnById.forEach((stepId, deps) -> deps.forEach(
                dep -> next.computeIfAbsent(dep, k -> new ArrayList<>()).add(stepId)));
        List<String> problems = FlowGraph.loopProblems(loops, next, dependsOnById, id -> "'" + id + "'");
        if (!problems.isEmpty()) {
            throw invalid(problems.get(0));
        }
    }

    private static void requireType(Map<String, Object> map, String where, String field, Class<?> type) {
        if (map.get(field) != null && !type.isInstance(map.get(field))) {
            throw invalid(where + field + " must be " + (type == String.class ? "text" : "an object"));
        }
    }

    private static FluxorException invalid(String message) {
        return new FluxorException("invalid_flow_definition", message, 422);
    }

    private static List<String> extractDependsOn(String stepId, Object raw) {
        if (raw == null) {
            return List.of();
        }
        if (!(raw instanceof List<?> rawList)) {
            throw new FluxorException("invalid_flow_definition",
                    "steps[id=" + stepId + "].dependsOn must be an array of step ids", 422);
        }
        return rawList.stream().map(item -> {
            if (!(item instanceof String s)) {
                throw new FluxorException("invalid_flow_definition",
                        "steps[id=" + stepId + "].dependsOn must contain only strings", 422);
            }
            return s;
        }).toList();
    }

    /** Iterative 3-color DFS (WHITE/GRAY/BLACK) toposort cycle check -- reports the exact cycle
     *  path (e.g. {@code "step-a -> step-b -> step-a"}) in the error, per the plan's "fail with
     *  the error's path". */
    private static void detectCycle(Map<String, List<String>> dependsOnById) {
        Set<String> visited = new LinkedHashSet<>();
        for (String start : dependsOnById.keySet()) {
            if (visited.contains(start)) {
                continue;
            }
            Deque<String> path = new ArrayDeque<>();
            Set<String> onPath = new LinkedHashSet<>();
            walk(start, dependsOnById, visited, onPath, path);
        }
    }

    private static void walk(String id, Map<String, List<String>> dependsOnById, Set<String> visited,
            Set<String> onPath, Deque<String> path) {
        if (onPath.contains(id)) {
            StringBuilder cycle = new StringBuilder();
            boolean started = false;
            for (String node : path) {
                if (node.equals(id)) {
                    started = true;
                }
                if (started) {
                    cycle.append(node).append(" -> ");
                }
            }
            cycle.append(id);
            throw new FluxorException("invalid_flow_definition", "Cycle detected in dependsOn: " + cycle, 422);
        }
        if (visited.contains(id)) {
            return;
        }
        onPath.add(id);
        path.addLast(id);
        for (String dep : dependsOnById.getOrDefault(id, List.of())) {
            walk(dep, dependsOnById, visited, onPath, path);
        }
        path.removeLast();
        onPath.remove(id);
        visited.add(id);
    }
}
