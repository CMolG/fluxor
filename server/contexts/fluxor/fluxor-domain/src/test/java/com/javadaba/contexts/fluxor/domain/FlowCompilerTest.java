package com.javadaba.contexts.fluxor.domain;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The compile rules of {@code doc://contracts/fluxor-flow}, one by one. */
class FlowCompilerTest {

    @Test
    void aCanvasWithNoStepsDoesNotCompileYet() {
        FlowCompiler.Compiled compiled = compile(canvas(List.of(note("n", "context")), List.of()));

        assertThat(compiled.definition()).isNull();
        assertThat(compiled.problems()).containsExactly("The flow has no steps yet.");
    }

    @Test
    void aChainCompilesToTheFormatWithItsFirstStepAsRoot() {
        Map<String, Object> definition = compile(canvas(
                List.of(step("b", "Review", "", "Review the draft."), step("a", "Draft", "", "Write a draft.")),
                List.of(edge("e1", "a", "b", "link")))).definition();

        assertThat(definition).containsEntry("version", "1").containsEntry("format", "fluxor-flow")
                .containsEntry("id", "flow-1").containsEntry("name", "My flow").containsEntry("rootStepId", "a")
                .doesNotContainKeys("loops", "contextMode", "meta");
        assertThat(steps(definition)).extracting(s -> s.get("id")).containsExactly("a", "b");
        assertThat(steps(definition).get(1)).containsEntry("type", "llm_call").containsEntry("title", "Review")
                .containsEntry("prompt", "Review the draft.").containsEntry("dependsOn", List.of("a"))
                .containsEntry("tools", List.of()).doesNotContainKeys("description", "context");
    }

    @Test
    void stepsAreOrderedByDependencyWithTiesBrokenById() {
        Map<String, Object> definition = compile(canvas(
                List.of(step("c", "C", "", "c"), step("b", "B", "", "b"), step("a", "A", "", "a"),
                        step("d", "D", "", "d")),
                List.of(edge("1", "a", "c", "link"), edge("2", "a", "b", "link"), edge("3", "c", "d", "link"),
                        edge("4", "b", "d", "link"))))
                .definition();

        assertThat(steps(definition)).extracting(s -> s.get("id")).containsExactly("a", "b", "c", "d");
        assertThat(steps(definition).get(3)).containsEntry("dependsOn", List.of("c", "b"));
    }

    @Test
    void anEmptyPromptFallsBackToTheDescriptionThenTheTitle() {
        Map<String, Object> definition = compile(canvas(
                List.of(step("a", "Plan", "Plan the work", ""), step("b", "Ship it", "", "")),
                List.of(edge("e", "a", "b", "link")))).definition();

        assertThat(steps(definition).get(0)).containsEntry("prompt", "Plan the work")
                .containsEntry("description", "Plan the work");
        assertThat(steps(definition).get(1)).containsEntry("prompt", "Ship it");
    }

    @Test
    void aNoteAttachedEitherWayBecomesContextAndALooseNoteStaysOnTheCanvas() {
        Map<String, Object> definition = compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "Use British spelling"), note("n2", "Cite sources"),
                        note("loose", "Just a thought")),
                List.of(edge("e1", "n1", "a", "attachment"), edge("e2", "a", "n2", "attachment")))).definition();

        assertThat(steps(definition).get(0)).containsEntry("context",
                Map.of("n1", "Use British spelling", "n2", "Cite sources"));
    }

    @Test
    void moreThanOneFirstStepIsAProblemNamingThem() {
        FlowCompiler.Compiled compiled = compile(canvas(
                List.of(step("a", "Draft", "", "a"), step("b", "", "", "b")), List.of()));

        assertThat(compiled.definition()).isNull();
        assertThat(compiled.problems()).containsExactly(
                "2 steps have nothing before them (\"Draft\", b): link them so the flow has exactly one first step.");
    }

    @Test
    void linksInACircleAreAProblemThatSaysToMakeOneALoop() {
        FlowCompiler.Compiled compiled = compile(canvas(
                List.of(step("a", "A", "", "a"), step("b", "B", "", "b")),
                List.of(edge("1", "a", "b", "link"), edge("2", "b", "a", "link"))));

        assertThat(compiled.problems()).containsExactly(
                "Steps \"A\" -> \"B\" -> \"A\" link in a circle: make the connection that closes it a loop.");
    }

    @Test
    void aLoopRunsBackToAnEarlierStepWithItsIterationsClamped() {
        Map<String, Object> definition = compile(canvas(
                List.of(step("a", "A", "", "a"), step("b", "B", "", "b"), step("c", "C", "", "c")),
                List.of(edge("1", "a", "b", "link"), edge("2", "b", "c", "link"),
                        loop("loop-1", "c", "b", 99))))
                .definition();

        assertThat(definition).containsEntry("loops",
                List.of(Map.of("id", "loop-1", "sourceStepId", "c", "targetStepId", "b", "maxIterations", 50)));
        assertThat(steps(definition).get(1)).containsEntry("dependsOn", List.of("a"));
    }

    @ParameterizedTest
    @CsvSource({"0, 1", "2.7, 2", "50, 50", "51, 50"})
    void loopIterationsAreWholePassesFromOneToFifty(double drawn, int compiled) {
        Map<String, Object> definition = compile(canvas(
                List.of(step("a", "A", "", "a"), step("b", "B", "", "b")),
                List.of(edge("1", "a", "b", "link"), loop("l", "b", "a", drawn)))).definition();

        assertThat(loops(definition).get(0)).containsEntry("maxIterations", compiled);
    }

    @Test
    void aLoopWithNoIterationsRunsThreeTimes() {
        Map<String, Object> loop = new LinkedHashMap<>(edge("l", "b", "a", "loop"));
        Map<String, Object> definition = compile(canvas(List.of(step("a", "A", "", "a"), step("b", "B", "", "b")),
                List.of(edge("1", "a", "b", "link"), loop))).definition();

        assertThat(loops(definition).get(0)).containsEntry("maxIterations", 3);
    }

    @Test
    void aLoopThatDoesNotRunBackIsAProblem() {
        FlowCompiler.Compiled compiled = compile(canvas(
                List.of(step("a", "A", "", "a"), step("b", "B", "", "b")),
                List.of(edge("1", "a", "b", "link"), loop("l", "a", "b", 3))));

        assertThat(compiled.problems()).containsExactly(
                "A loop must run back to an earlier step: \"B\" does not lead to \"A\".");
    }

    @Test
    void aLoopOntoItselfIsAProblem() {
        FlowCompiler.Compiled compiled = compile(
                canvas(List.of(step("a", "A", "", "a")), List.of(loop("l", "a", "a", 3))));

        assertThat(compiled.problems()).containsExactly("A loop cannot run a step back to itself (\"A\").");
    }

    @Test
    void overlappingLoopsAreAProblem() {
        FlowCompiler.Compiled compiled = compile(canvas(
                List.of(step("a", "A", "", "a"), step("b", "B", "", "b"), step("c", "C", "", "c")),
                List.of(edge("1", "a", "b", "link"), edge("2", "b", "c", "link"), loop("outer", "c", "a", 3),
                        loop("inner", "c", "b", 3))));

        assertThat(compiled.problems()).containsExactly(
                "Loops outer and inner both repeat \"B\", \"C\": loops cannot be nested or overlap.");
    }

    @Test
    void theFlowsModeDescriptionAndMetaCarryOver() {
        Map<String, Object> drawn = canvas(List.of(step("a", "A", "", "a")), List.of());
        drawn.put("contextMode", "feedback");
        drawn.put("description", "Ships a release");
        drawn.put("meta", Map.of("author", "ops", "description", "stale"));

        Map<String, Object> definition = compile(drawn).definition();

        assertThat(definition).containsEntry("contextMode", "feedback")
                .containsEntry("meta", Map.of("author", "ops", "description", "Ships a release"));
    }

    @Test
    void aBlindFlowOmitsItsMode() {
        Map<String, Object> drawn = canvas(List.of(step("a", "A", "", "a")), List.of());
        drawn.put("contextMode", "blind");

        assertThat(compile(drawn).definition()).doesNotContainKey("contextMode");
    }

    @Test
    void aStepsCarriedFieldsSurviveVerbatim() {
        Map<String, Object> step = step("a", "A", "", "a");
        step.put("tools", List.of("uppercase"));
        step.put("systemPrompt", "You are terse.");
        step.put("contract", Map.of("mustWriteFiles", true, "maxAttempts", 2));
        step.put("model", "openai/gpt-4o-mini");
        step.put("stepType", "tool_call");

        Map<String, Object> compiled = steps(compile(canvas(List.of(step), List.of())).definition()).get(0);

        assertThat(compiled).containsEntry("type", "tool_call").containsEntry("tools", List.of("uppercase"))
                .containsEntry("systemPrompt", "You are terse.")
                .containsEntry("contract", Map.of("mustWriteFiles", true, "maxAttempts", 2))
                .containsEntry("model", "openai/gpt-4o-mini");
    }

    @Test
    void aConnectionToANodeThatIsNotThereIsNotACanvas() {
        Map<String, Object> drawn = canvas(List.of(step("a", "A", "", "a")), List.of(edge("1", "a", "gone", "link")));

        assertThatThrownBy(() -> compile(drawn)).isInstanceOf(FluxorException.class)
                .extracting(e -> ((FluxorException) e).code()).isEqualTo("invalid_flow_canvas");
    }

    @Test
    void aCanvasOfAnotherVersionIsRefused() {
        Map<String, Object> drawn = canvas(List.of(), List.of());
        drawn.put("version", 2);

        assertThatThrownBy(() -> compile(drawn)).isInstanceOf(FluxorException.class)
                .hasMessageContaining("version must be 1");
    }

    // ── canvas builders, the shape of packages/apps/fluxor/src/lib/flow.ts ──────────────────

    static Map<String, Object> canvas(List<Map<String, Object>> nodes, List<Map<String, Object>> edges) {
        Map<String, Object> canvas = new LinkedHashMap<>();
        canvas.put("version", 1);
        canvas.put("name", "Drawn name");
        canvas.put("description", "");
        canvas.put("contextMode", "blind");
        canvas.put("nodes", new ArrayList<>(nodes));
        canvas.put("edges", new ArrayList<>(edges));
        return canvas;
    }

    static Map<String, Object> step(String id, String title, String description, String prompt) {
        Map<String, Object> node = node(id, "step");
        node.put("title", title);
        node.put("description", description);
        node.put("prompt", prompt);
        node.put("stepType", "llm_call");
        return node;
    }

    static Map<String, Object> note(String id, String text) {
        Map<String, Object> node = node(id, "note");
        node.put("text", text);
        node.put("color", "#EDE9FE");
        node.put("shape", "square");
        return node;
    }

    static Map<String, Object> edge(String id, String source, String target, String kind) {
        Map<String, Object> edge = new LinkedHashMap<>();
        edge.put("id", id);
        edge.put("source", source);
        edge.put("target", target);
        edge.put("sourceHandle", "right");
        edge.put("targetHandle", "left");
        edge.put("kind", kind);
        return edge;
    }

    static Map<String, Object> loop(String id, String source, String target, Number maxIterations) {
        Map<String, Object> edge = edge(id, source, target, "loop");
        edge.put("maxIterations", maxIterations);
        return edge;
    }

    private static Map<String, Object> node(String id, String kind) {
        Map<String, Object> node = new LinkedHashMap<>();
        node.put("id", id);
        node.put("kind", kind);
        node.put("x", 0);
        node.put("y", 0);
        node.put("width", 300);
        node.put("height", 190);
        return node;
    }

    private static FlowCompiler.Compiled compile(Map<String, Object> canvas) {
        return FlowCompiler.compile(canvas, "flow-1", "My flow");
    }

    @SuppressWarnings("unchecked")
    static List<Map<String, Object>> steps(Map<String, Object> definition) {
        return (List<Map<String, Object>>) definition.get("steps");
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> loops(Map<String, Object> definition) {
        return (List<Map<String, Object>>) definition.get("loops");
    }
}
