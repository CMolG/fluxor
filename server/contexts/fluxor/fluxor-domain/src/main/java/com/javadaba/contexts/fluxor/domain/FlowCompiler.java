package com.javadaba.contexts.fluxor.domain;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Compiles the designer's canvas ({@link FlowCanvas}) into a {@code fluxor-flow} v1 document, or
 * says in words why it cannot: a design that does not compile yet is still saved, so the problems
 * are an answer, not an error. Reimplemented, never copied, from fluxor-ide {@code feat/cockpit}
 * (Apache-2.0): {@code compileFlowFromCanvas} ({@code src/renderer/lib/harness-compiler.ts}) and
 * {@code exportFlow} ({@code src/main/flow-export/fluxor-flow.ts}). The rules and the round trip
 * with {@link FlowLayout} are {@code doc://contracts/fluxor-flow}.
 */
public final class FlowCompiler {

    public static final String FORMAT = "fluxor-flow";
    public static final String FORMAT_VERSION = "1";

    private FlowCompiler() {
    }

    /** {@code definition} is null exactly when {@code problems} is not empty. */
    public record Compiled(Map<String, Object> definition, List<String> problems) {
    }

    public static Compiled compile(Map<String, Object> canvasJson, String id, String name) {
        FlowCanvas canvas = FlowCanvas.parse(canvasJson);
        if (canvas.steps().isEmpty()) {
            return new Compiled(null, List.of("The flow has no steps yet."));
        }
        Map<String, FlowCanvas.Step> steps = new LinkedHashMap<>();
        canvas.steps().forEach(step -> steps.put(step.id(), step));
        Function<String, String> label = stepId -> steps.get(stepId).title().isBlank()
                ? stepId
                : "\"" + steps.get(stepId).title().trim() + "\"";

        Map<String, List<String>> dependsOn = new LinkedHashMap<>();
        Map<String, List<String>> next = new LinkedHashMap<>();
        steps.keySet().forEach(stepId -> {
            dependsOn.put(stepId, new ArrayList<>());
            next.put(stepId, new ArrayList<>());
        });
        Map<String, FlowNotes.Reading> readings = FlowNotes.read(canvas);
        List<FlowGraph.Loop> loops = new ArrayList<>();
        List<Map<String, Object>> loopEntries = new ArrayList<>();
        for (FlowCanvas.Edge edge : canvas.edges()) {
            boolean betweenSteps = steps.containsKey(edge.source()) && steps.containsKey(edge.target());
            switch (edge.kind()) {
                case "link" -> {
                    if (betweenSteps) {
                        addUnique(dependsOn.get(edge.target()), edge.source());
                        addUnique(next.get(edge.source()), edge.target());
                    }
                }
                case "loop" -> {
                    if (betweenSteps) {
                        loops.add(new FlowGraph.Loop(edge.id(), edge.source(), edge.target()));
                        Map<String, Object> loop = new LinkedHashMap<>();
                        loop.put("id", edge.id());
                        loop.put("sourceStepId", edge.source());
                        loop.put("targetStepId", edge.target());
                        loop.put("maxIterations", FlowGraph.clampIterations(edge.maxIterations()));
                        loopEntries.add(loop);
                    }
                }
            }
        }

        List<String> problems = new ArrayList<>();
        List<String> circle = FlowGraph.cycle(steps.keySet(), next);
        if (!circle.isEmpty()) {
            problems.add("Steps " + String.join(" -> ", circle.stream().map(label).toList())
                    + " link in a circle: make the connection that closes it a loop.");
        } else {
            List<String> firsts = steps.keySet().stream().filter(stepId -> dependsOn.get(stepId).isEmpty()).toList();
            if (firsts.size() > 1) {
                problems.add(firsts.size() + " steps have nothing before them (" + String.join(", ",
                        firsts.stream().map(label).toList())
                        + "): link them so the flow has exactly one first step.");
            }
            problems.addAll(FlowGraph.loopProblems(loops, next, dependsOn, label));
        }
        if (!problems.isEmpty()) {
            return new Compiled(null, List.copyOf(problems));
        }

        List<Map<String, Object>> compiledSteps = new ArrayList<>();
        for (String stepId : FlowGraph.order(steps.keySet(), dependsOn)) {
            compiledSteps.add(step(steps.get(stepId), dependsOn.get(stepId), readings.get(stepId)));
        }
        Map<String, Object> definition = new LinkedHashMap<>();
        definition.put("version", FORMAT_VERSION);
        definition.put("format", FORMAT);
        definition.put("id", id);
        definition.put("name", name == null || name.isBlank()
                ? (canvas.name() == null || canvas.name().isBlank() ? "Untitled flow" : canvas.name())
                : name);
        definition.put("rootStepId", compiledSteps.get(0).get("id"));
        definition.put("steps", compiledSteps);
        if (!loopEntries.isEmpty()) {
            definition.put("loops", loopEntries);
        }
        if ("feedback".equals(canvas.contextMode())) {
            definition.put("contextMode", "feedback");
        }
        Map<String, Object> meta = new LinkedHashMap<>();
        if (canvas.meta() != null) {
            meta.putAll(canvas.meta());
            meta.remove("description");
        }
        if (!canvas.description().isBlank()) {
            meta.put("description", canvas.description());
        }
        if (!meta.isEmpty()) {
            definition.put("meta", meta);
        }
        return new Compiled(definition, List.of());
    }

    private static Map<String, Object> step(FlowCanvas.Step step, List<String> dependsOn, FlowNotes.Reading reading) {
        Map<String, Object> compiled = new LinkedHashMap<>();
        compiled.put("id", step.id());
        compiled.put("type", step.stepType().isBlank() ? "llm_call" : step.stepType());
        if (!step.title().isBlank()) {
            compiled.put("title", step.title());
        }
        if (!step.description().isBlank()) {
            compiled.put("description", step.description());
        }
        compiled.put("prompt", !step.prompt().isBlank()
                ? step.prompt()
                : !step.description().isBlank() ? step.description() : step.title());
        compiled.put("dependsOn", List.copyOf(dependsOn));
        if (step.systemPrompt() != null) {
            compiled.put("systemPrompt", step.systemPrompt());
        }
        compiled.put("tools", step.tools());
        if (!reading.context().isEmpty()) {
            compiled.put("context", reading.context());
        }
        if (reading.inputs() != null) {
            compiled.put("inputs", reading.inputs());
        }
        if (step.contract() != null) {
            compiled.put("contract", step.contract());
        }
        if (step.model() != null) {
            compiled.put("model", step.model());
        }
        return compiled;
    }

    private static void addUnique(List<String> list, String value) {
        if (!list.contains(value)) {
            list.add(value);
        }
    }
}
