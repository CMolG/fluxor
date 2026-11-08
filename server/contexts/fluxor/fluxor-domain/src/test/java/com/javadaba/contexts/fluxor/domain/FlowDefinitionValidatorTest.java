package com.javadaba.contexts.fluxor.domain;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * FAIL-first per plan #19, Task 5 Step 1. The golden case here hand-builds the SAME shape as
 * {@code ../fluxor/fluxor-ide/sdk/conformance/conformance-chain.flow.json} (5 steps, linear
 * dependsOn chain a->b->c->d->e) -- the infrastructure-layer test parses the REAL copied fixture
 * file and feeds it through this same validator.
 */
class FlowDefinitionValidatorTest {

    @Test
    void linearChainValidatesCleanly() {
        Map<String, Object> definition = Map.of("steps", List.of(
                step("step-a", List.of()),
                step("step-b", List.of("step-a")),
                step("step-c", List.of("step-b")),
                step("step-d", List.of("step-c")),
                step("step-e", List.of("step-d"))));
        assertThatCode(() -> FlowDefinitionValidator.validateStructure(definition));
    }

    @Test
    void missingStepsIsRejected() {
        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(Map.of()))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("steps");
    }

    @Test
    void danglingDependencyIsRejectedWithPath() {
        Map<String, Object> definition = Map.of("steps", List.of(
                step("step-a", List.of()),
                step("step-b", List.of("step-does-not-exist"))));
        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(definition))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("step-b")
                .hasMessageContaining("step-does-not-exist");
    }

    @Test
    void cycleIsRejectedWithPath() {
        Map<String, Object> definition = Map.of("steps", List.of(
                step("step-a", List.of("step-b")),
                step("step-b", List.of("step-a"))));
        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(definition))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("Cycle detected");
    }

    @Test
    void duplicateStepIdIsRejected() {
        Map<String, Object> definition = Map.of("steps", List.of(
                step("step-a", List.of()),
                step("step-a", List.of())));
        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(definition))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("duplicate");
    }

    @Test
    void sizeCapIsEnforced() {
        assertThatThrownBy(() -> FlowDefinitionValidator.validateSize(FlowDefinitionValidator.MAX_DEFINITION_BYTES + 1))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("exceeds");
    }

    @Test
    void sizeAtCapIsAccepted() {
        FlowDefinitionValidator.validateSize(FlowDefinitionValidator.MAX_DEFINITION_BYTES); // does not throw
    }

    // ── the rest of the format (JAVA-163) ───────────────────────────────────────────────────

    @Test
    void aLegacyOrUnknownFormatTagIsCarriedNotRefused() {
        for (String format : List.of("heliox-flow", "something-else")) {
            FlowDefinitionValidator.validateStructure(document(Map.of("format", format)));
        }
    }

    @Test
    void anotherFormatVersionIsRejected() {
        assertRejected(document(Map.of("version", "2")), "'version' must be \"1\"");
    }

    @Test
    void theRootMustBeAStepThatDependsOnNothing() {
        assertRejected(document(Map.of("rootStepId", "nope")), "rootStepId must name one of the steps");
        assertRejected(document(Map.of("rootStepId", "step-b")), "depends on other steps");
    }

    @Test
    void aStepsFieldsHaveTheFormatsTypes() {
        Map<String, Object> badTools = new HashMap<>(step("step-a", List.of()));
        badTools.put("tools", List.of(1));
        assertRejected(Map.of("steps", List.of(badTools)), "tools must be an array of tool names");

        Map<String, Object> badContext = new HashMap<>(step("step-a", List.of()));
        badContext.put("context", Map.of("n", 3));
        assertRejected(Map.of("steps", List.of(badContext)), "context must map each note id to its text");

        Map<String, Object> badPrompt = new HashMap<>(step("step-a", List.of()));
        badPrompt.put("prompt", List.of());
        assertRejected(Map.of("steps", List.of(badPrompt)), "prompt must be text");
    }

    @Test
    void aLoopRunsBackBetweenTheFlowsStepsFromOneToFiftyTimes() {
        FlowDefinitionValidator
                .validateStructure(document(Map.of("loops", List.of(loop("l", "step-b", "step-a", 50)))));

        assertRejected(document(Map.of("loops", List.of(loop("l", "step-b", "step-a", 0)))),
                "maxIterations must be a whole number from 1 to 50");
        assertRejected(document(Map.of("loops", List.of(loop("l", "step-b", "ghost", 3)))),
                "must run between two of the flow's steps");
        assertRejected(document(Map.of("loops", List.of(loop("l", "step-a", "step-b", 3)))),
                "must run back to an earlier step");
        assertRejected(document(Map.of("loops", List.of(loop("l", "step-a", "step-a", 3)))),
                "cannot run a step back to itself");
        assertRejected(document(Map.of("loops", List.of(loop("l", "step-b", "step-a", 3),
                loop("l", "step-b", "step-a", 3)))), "Every loop needs an id of its own");
        assertRejected(document(Map.of("loops", List.of(loop("outer", "step-b", "step-a", 3),
                loop("inner", "step-b", "step-a", 3)))), "cannot be nested or overlap");
    }

    private static Map<String, Object> document(Map<String, Object> extra) {
        Map<String, Object> definition = new HashMap<>(extra);
        definition.put("steps", List.of(step("step-a", List.of()), step("step-b", List.of("step-a"))));
        return definition;
    }

    private static Map<String, Object> loop(String id, String source, String target, int maxIterations) {
        return Map.of("id", id, "sourceStepId", source, "targetStepId", target, "maxIterations", maxIterations);
    }

    @Test
    void anInputsBlockNamesOnlyNotesTheStepsContextHolds() {
        Map<String, Object> stepA = new HashMap<>(step("step-a", List.of()));
        stepA.put("context", Map.of("n1", "One", "n2", "Two"));
        stepA.put("inputs", Map.of("primaryInput", List.of(Map.of("type", "CoreVision", "notes", List.of("n1")))));
        assertThatCode(() -> FlowDefinitionValidator.validateStructure(Map.of("steps", List.of(stepA))));

        Map<String, Object> ghost = new HashMap<>(stepA);
        ghost.put("inputs", Map.of("primaryInput", List.of(Map.of("notes", List.of("n9")))));
        assertRejected(Map.of("steps", List.of(ghost)),
                "inputs.primaryInput must be groups of notes the step's context holds");

        Map<String, Object> oneLink = new HashMap<>(stepA);
        oneLink.put("inputs", Map.of("links", List.of(List.of("n1"))));
        assertRejected(Map.of("steps", List.of(oneLink)), "inputs.links must be pairs of notes");

        Map<String, Object> numericType = new HashMap<>(stepA);
        numericType.put("inputs", Map.of("context", List.of(Map.of("type", 3, "notes", List.of("n1")))));
        assertRejected(Map.of("steps", List.of(numericType)), "inputs.context must be groups");

        Map<String, Object> notAnObject = new HashMap<>(stepA);
        notAnObject.put("inputs", List.of());
        assertRejected(Map.of("steps", List.of(notAnObject)), "inputs must be an object");
    }

    private static void assertRejected(Map<String, Object> definition, String message) {
        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(definition))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining(message);
    }

    private static Map<String, Object> step(String id, List<String> dependsOn) {
        return Map.of("id", id, "type", "llm_call", "dependsOn", dependsOn, "tools", List.of());
    }

    private static void assertThatCode(Runnable runnable) {
        runnable.run(); // just must not throw -- kept explicit/named for readability at call sites
        assertThat(true).isTrue();
    }
}
