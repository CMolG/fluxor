package com.javadaba.contexts.fluxor.domain;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static com.javadaba.contexts.fluxor.domain.FlowCompilerTest.steps;
import static org.assertj.core.api.Assertions.assertThat;

/** How a document is laid out as a canvas ({@code doc://contracts/fluxor-flow}). */
class FlowLayoutTest {

    @Test
    void aStepsColumnIsItsLongestPathAndItsRowItsOrderInTheColumn() {
        Map<String, Object> canvas = FlowLayout.layout(Map.of("steps", List.of(
                step("a", List.of()), step("b", List.of("a")), step("x", List.of("a")),
                step("c", List.of("a", "b")))), "Fallback");

        Map<String, Map<String, Object>> nodes = nodesById(canvas);
        assertThat(nodes.get("a").get("x")).isEqualTo(0);
        assertThat(nodes.get("b").get("x")).isEqualTo(nodes.get("x").get("x"));
        assertThat((int) nodes.get("x").get("y")).isGreaterThan((int) nodes.get("b").get("y"));
        assertThat((int) nodes.get("c").get("x")).isGreaterThan((int) nodes.get("b").get("x"));
        assertThat(canvas).containsEntry("name", "Fallback").containsEntry("contextMode", "blind")
                .containsEntry("version", 1);
    }

    @Test
    void aLegacyDraftGetsTheDefaultsTheDesignerDraws() {
        Map<String, Object> step = nodesById(FlowLayout.layout(Map.of("steps", List.of(step("a", List.of()))),
                "Draft")).get("a");

        assertThat(step).containsEntry("kind", "step").containsEntry("stepType", "llm_call")
                .containsEntry("prompt", "").containsEntry("title", "").doesNotContainKey("tools");
    }

    @Test
    void aSharedNoteIsDrawnOnceAboveItsFirstStepAndAttachedToEach() {
        Map<String, Object> first = step("a", List.of());
        first.put("context", Map.of("style", "Be brief"));
        Map<String, Object> second = step("b", List.of("a"));
        second.put("context", Map.of("style", "Be brief"));

        Map<String, Object> canvas = FlowLayout.layout(Map.of("steps", List.of(first, second)), "Flow");

        Map<String, Object> note = nodesById(canvas).get("style");
        assertThat(note).containsEntry("kind", "note").containsEntry("text", "Be brief");
        assertThat((int) note.get("y")).isLessThan((int) nodesById(canvas).get("a").get("y"));
        assertThat(edges(canvas)).filteredOn(e -> "attachment".equals(e.get("kind")))
                .extracting(e -> e.get("target")).containsExactly("a", "b");
    }

    @Test
    void aContextKeyThatIsAStepsIdGetsANoteIdOfItsOwn() {
        Map<String, Object> first = step("a", List.of());
        first.put("context", Map.of("a", "Note named like its step"));

        assertThat(nodesById(FlowLayout.layout(Map.of("steps", List.of(first)), "Flow"))).containsKey("note:a");
    }

    @Test
    void aNoteTypeAndAPrimaryInputModeComeBackOnTheNoteAndItsAttachment() {
        Map<String, Object> first = step("a", List.of());
        first.put("context", Map.of("n1", "Rival is slow"));
        first.put("inputs",
                Map.of("primaryInput", List.of(Map.of("type", "CompetitorWeakness", "notes", List.of("n1")))));

        Map<String, Object> canvas = FlowLayout.layout(Map.of("steps", List.of(first)), "Flow");

        assertThat(nodesById(canvas).get("n1")).containsEntry("type", "CompetitorWeakness");
        assertThat(edges(canvas)).filteredOn(e -> "attachment".equals(e.get("kind")))
                .singleElement().satisfies(e -> assertThat(e).containsEntry("mode", "primary-input"));
    }

    @Test
    void aReadContextAttachmentCarriesNoModeKey() {
        Map<String, Object> first = step("a", List.of());
        first.put("context", Map.of("n1", "Plain"));

        Map<String, Object> canvas = FlowLayout.layout(Map.of("steps", List.of(first)), "Flow");

        assertThat(edges(canvas)).filteredOn(e -> "attachment".equals(e.get("kind")))
                .singleElement().satisfies(e -> assertThat(e).doesNotContainKey("mode"));
    }

    @Test
    void aLinkBetweenNotesComesBackAsANoteToNoteAttachment() {
        Map<String, Object> first = step("a", List.of());
        first.put("context", Map.of("n1", "One", "n2", "Two"));
        first.put("inputs", Map.of("context", List.of(Map.of("notes", List.of("n1", "n2"))),
                "links", List.of(List.of("n1", "n2"))));

        Map<String, Object> canvas = FlowLayout.layout(Map.of("steps", List.of(first)), "Flow");

        assertThat(edges(canvas)).filteredOn(e -> "attachment".equals(e.get("kind")))
                .extracting(e -> e.get("source") + ">" + e.get("target")).contains("n1>n2");
    }

    @Test
    void compilingALaidOutDefinitionReturnsItsInputsAndContext() {
        Map<String, Object> first = step("a", List.of());
        first.put("context", Map.of("n1", "Rival is slow", "n2", "Cheap"));
        first.put("inputs",
                Map.of("primaryInput", List.of(Map.of("type", "CompetitorWeakness", "notes", List.of("n1"))),
                        "context", List.of(Map.of("notes", List.of("n2")))));
        Map<String, Object> second = step("b", List.of("a"));
        second.put("context", Map.of("n1", "Rival is slow"));
        second.put("inputs", Map.of("context", List.of(Map.of("type", "CompetitorWeakness", "notes", List.of("n1")))));
        Map<String, Object> definition = Map.of("steps", List.of(first, second));

        Map<String, Object> canvas = FlowLayout.layout(definition, "Flow");
        Map<String, Object> compiled = FlowCompiler.compile(canvas, "flow-1", "Flow").definition();

        assertThat(steps(compiled).get(0)).containsEntry("inputs", first.get("inputs"))
                .containsEntry("context", first.get("context"));
        assertThat(steps(compiled).get(1)).containsEntry("inputs", second.get("inputs"))
                .containsEntry("context", second.get("context"));
    }

    private static Map<String, Object> step(String id, List<String> dependsOn) {
        Map<String, Object> step = new LinkedHashMap<>();
        step.put("id", id);
        step.put("dependsOn", dependsOn);
        return step;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Map<String, Object>> nodesById(Map<String, Object> canvas) {
        Map<String, Map<String, Object>> byId = new LinkedHashMap<>();
        ((List<Map<String, Object>>) canvas.get("nodes")).forEach(n -> byId.put((String) n.get("id"), n));
        return byId;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> edges(Map<String, Object> canvas) {
        return (List<Map<String, Object>>) canvas.get("edges");
    }
}
