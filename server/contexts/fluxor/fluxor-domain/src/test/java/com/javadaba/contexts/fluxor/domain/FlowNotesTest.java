package com.javadaba.contexts.fluxor.domain;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static com.javadaba.contexts.fluxor.domain.FlowCompilerTest.canvas;
import static com.javadaba.contexts.fluxor.domain.FlowCompilerTest.edge;
import static com.javadaba.contexts.fluxor.domain.FlowCompilerTest.note;
import static com.javadaba.contexts.fluxor.domain.FlowCompilerTest.steps;
import static com.javadaba.contexts.fluxor.domain.FlowCompilerTest.step;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** What a step reads from the canvas's notes: the attached ones, and those reached through note-to-note links. */
class FlowNotesTest {

    @Test
    void aPrimaryInputNoteIsGroupedByItsTypeUnderPrimaryInput() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), typed("n1", "Rival is slow", "CompetitorWeakness")),
                List.of(attachment("e1", "n1", "a", "primary-input"))))).get(0);

        assertThat(step).containsEntry("context", Map.of("n1", "Rival is slow"));
        assertThat(inputs(step)).containsOnlyKeys("primaryInput")
                .containsEntry("primaryInput", List.of(Map.of("type", "CompetitorWeakness", "notes", List.of("n1"))));
    }

    @Test
    void readContextNotesAreGroupedByTypeInTheOrderTheyAreFirstSeen() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), typed("n1", "One", "CoreVision"), note("n3", "Three"),
                        typed("n2", "Two", "CoreVision")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n3", "a", null),
                        attachment("e3", "n2", "a", null)))))
                .get(0);

        assertThat(inputs(step)).containsOnlyKeys("context")
                .containsEntry("context", List.of(Map.of("type", "CoreVision", "notes", List.of("n1", "n2")),
                        Map.of("notes", List.of("n3"))));
    }

    @Test
    void notesReachedThroughLinksAreReadAtAnyDepthInBreadthFirstOrder() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "1"), note("n2", "2"), note("n3", "3"), note("n4", "4")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n2", "n1", null),
                        attachment("e3", "n2", "n3", null), attachment("e4", "n3", "n4", null)))))
                .get(0);

        assertThat(step.get("context")).isEqualTo(Map.of("n1", "1", "n2", "2", "n3", "3", "n4", "4"));
        assertThat(castMap(step.get("context")).keySet()).containsExactly("n1", "n2", "n3", "n4");
    }

    @Test
    void aLinkCanBeDrawnEitherWayAndABranchIsFollowedOnBothSides() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "1"), note("n2", "2"), note("n3", "3")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n1", "n2", null),
                        attachment("e3", "n3", "n1", null)))))
                .get(0);

        assertThat(step.get("context")).isEqualTo(Map.of("n1", "1", "n2", "2", "n3", "3"));
    }

    @Test
    void aRingOfLinkedNotesTerminatesAndEachNoteIsReadOnce() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "1"), note("n2", "2"), note("n3", "3")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n1", "n2", null),
                        attachment("e3", "n2", "n3", null), attachment("e4", "n3", "n1", null)))))
                .get(0);

        assertThat(step.get("context")).isEqualTo(Map.of("n1", "1", "n2", "2", "n3", "3"));
    }

    @Test
    void aReachedNoteInheritsThePrimaryModeOfTheNoteItWasReachedFrom() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), typed("n1", "1", "CoreVision"), typed("n2", "2", "CoreVision")),
                List.of(attachment("e1", "n1", "a", "primary-input"), attachment("e2", "n2", "n1", null))))).get(0);

        assertThat(inputs(step)).containsEntry("primaryInput",
                List.of(Map.of("type", "CoreVision", "notes", List.of("n1", "n2"))))
                .doesNotContainKey("context");
    }

    @Test
    void aDirectAttachmentBeatsTheModeInheritedThroughALink() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), typed("n1", "1", "CoreVision"), typed("n2", "2", "CoreVision")),
                List.of(attachment("e1", "n1", "a", "primary-input"), attachment("e2", "n2", "a", null),
                        attachment("e3", "n2", "n1", null)))))
                .get(0);

        assertThat(inputs(step))
                .containsEntry("primaryInput", List.of(Map.of("type", "CoreVision", "notes", List.of("n1"))))
                .containsEntry("context", List.of(Map.of("type", "CoreVision", "notes", List.of("n2"))));
    }

    @Test
    void primaryInputWinsWhenSeveralPathsReachANote() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "1"), typed("n2", "2", "CoreVision"), note("n3", "3")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n2", "a", "primary-input"),
                        attachment("e3", "n3", "n1", null), attachment("e4", "n3", "n2", null)))))
                .get(0);

        assertThat(inputs(step)).containsEntry("primaryInput", List.of(
                Map.of("type", "CoreVision", "notes", List.of("n2")), Map.of("notes", List.of("n3"))))
                .containsEntry("context", List.of(Map.of("notes", List.of("n1"))));
    }

    @Test
    void aNoteAttachedTwiceToOneStepIsReadOnceAndPrimaryWins() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), typed("n1", "1", "CoreVision")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "a", "n1", "primary-input"))))).get(0);

        assertThat(step.get("context")).isEqualTo(Map.of("n1", "1"));
        assertThat(inputs(step)).containsEntry("primaryInput",
                List.of(Map.of("type", "CoreVision", "notes", List.of("n1"))));
    }

    @Test
    void aNoteSharedByTwoStepsKeepsEachStepsOwnMode() {
        List<Map<String, Object>> steps = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), step("b", "B", "", "b"), typed("n1", "1", "CoreVision")),
                List.of(edge("e0", "a", "b", "link"), attachment("e1", "n1", "a", "primary-input"),
                        attachment("e2", "n1", "b", null)))));

        assertThat(inputs(steps.get(0))).containsOnlyKeys("primaryInput");
        assertThat(inputs(steps.get(1))).containsOnlyKeys("context");
    }

    @Test
    void aLooseNoteOnTheCanvasIsLeftOutOfEveryStep() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "1"), note("loose", "Just a thought"), note("n2", "2")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n2", "loose", null))))).get(0);

        assertThat(step.get("context")).isEqualTo(Map.of("n1", "1"));
    }

    @Test
    void aNoteLinkedToAStepOnlyThroughAnotherNoteIsReadWithItsLink() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), typed("n1", "1", "CoreVision"), note("n2", "2")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "n1", "n2", null))))).get(0);

        assertThat(inputs(step)).containsEntry("links", List.of(List.of("n1", "n2")));
    }

    @Test
    void anOldCanvasWithNoNoteLinksAndNoTypesCompilesWithoutInputs() {
        Map<String, Object> step = steps(compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "Use British spelling"), note("n2", "Cite sources")),
                List.of(attachment("e1", "n1", "a", null), attachment("e2", "a", "n2", null))))).get(0);

        assertThat(json(step)).isEqualTo("{\"id\":\"a\",\"type\":\"llm_call\",\"title\":\"A\",\"prompt\":\"a\","
                + "\"dependsOn\":[],\"tools\":[],\"context\":{\"n1\":\"Use British spelling\",\"n2\":\"Cite sources\"}}");
    }

    @Test
    void aTypeThatIsNotTextAndAModeThatIsNotKnownAreRefused() {
        Map<String, Object> badTyped = note("n1", "1");
        badTyped.put("type", 3);
        assertThatThrownBy(() -> compile(canvas(
                List.of(step("a", "A", "", "a"), badTyped), List.of(attachment("e1", "n1", "a", null)))))
                .isInstanceOf(FluxorException.class);
        assertThatThrownBy(() -> compile(canvas(
                List.of(step("a", "A", "", "a"), note("n1", "1")),
                List.of(attachment("e1", "n1", "a", "sometimes"))))).isInstanceOf(FluxorException.class);
    }

    private static Map<String, Object> typed(String id, String text, String type) {
        Map<String, Object> note = note(id, text);
        note.put("type", type);
        return note;
    }

    private static Map<String, Object> attachment(String id, String source, String target, String mode) {
        Map<String, Object> edge = edge(id, source, target, "attachment");
        if (mode != null) {
            edge.put("mode", mode);
        }
        return edge;
    }

    private static Map<String, Object> inputs(Map<String, Object> step) {
        return castMap(step.get("inputs"));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object value) {
        return (Map<String, Object>) value;
    }

    private static Map<String, Object> compile(Map<String, Object> canvas) {
        return FlowCompiler.compile(canvas, "flow-1", "My flow").definition();
    }

    /** The compiled step as JSON text, keys in the order the compiler wrote them. */
    private static String json(Object value) {
        if (value instanceof Map<?, ?> map) {
            return map.entrySet().stream()
                    .map(entry -> json(entry.getKey()) + ":" + json(entry.getValue()))
                    .collect(Collectors.joining(",", "{", "}"));
        }
        if (value instanceof List<?> list) {
            return list.stream().map(FlowNotesTest::json).collect(Collectors.joining(",", "[", "]"));
        }
        if (value instanceof String text) {
            return "\"" + text + "\"";
        }
        return String.valueOf(value);
    }
}
