package com.javadaba.contexts.fluxor.infrastructure;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FlowDefinitionValidator;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Golden test for {@link FlowDefinitionValidator} (plan #19, Task 5 Step 1) -- parses the REAL
 * fixture copied verbatim from {@code
 * ../fluxor/fluxor-ide/sdk/conformance/conformance-chain.flow.json} (READ-ONLY reference, never
 * edited by this plan) at {@code src/test/resources/flow-fixtures/conformance-chain.flow.json},
 * and feeds it through the domain validator here (where Jackson IS available, unlike
 * fluxor-domain -- see the validator's javadoc). Also exercises the two mutations the plan calls
 * out explicitly: a cycle and a dangling dependency, both derived from the same golden fixture.
 */
class FlowDefinitionValidatorGoldenFixtureTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    @SuppressWarnings("unchecked")
    void conformanceChainFixtureValidatesCleanly() throws Exception {
        Map<String, Object> definition = readFixture();
        assertThat(definition.get("format")).isEqualTo("fluxor-flow");
        List<Object> steps = (List<Object>) definition.get("steps");
        assertThat(steps).hasSize(5);

        assertThatCode(() -> FlowDefinitionValidator.validateStructure(definition)).doesNotThrowAnyException();
    }

    @Test
    @SuppressWarnings("unchecked")
    void mutatedFixtureWithDanglingDependencyFails() throws Exception {
        Map<String, Object> definition = readFixture();
        List<Map<String, Object>> steps = new java.util.ArrayList<>(
                (List<Map<String, Object>>) (List<?>) definition.get("steps"));
        Map<String, Object> lastStep = new java.util.LinkedHashMap<>(steps.get(steps.size() - 1));
        lastStep.put("dependsOn", List.of("step-does-not-exist"));
        steps.set(steps.size() - 1, lastStep);
        Map<String, Object> mutated = new java.util.LinkedHashMap<>(definition);
        mutated.put("steps", steps);

        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(mutated))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("step-does-not-exist");
    }

    @Test
    @SuppressWarnings("unchecked")
    void mutatedFixtureWithCycleFails() throws Exception {
        Map<String, Object> definition = readFixture();
        List<Map<String, Object>> steps = new java.util.ArrayList<>(
                (List<Map<String, Object>>) (List<?>) definition.get("steps"));
        // step-a (index 0) normally has no deps; point it back at the last step to create a cycle.
        Map<String, Object> firstStep = new java.util.LinkedHashMap<>(steps.get(0));
        firstStep.put("dependsOn", List.of("step-e"));
        steps.set(0, firstStep);
        Map<String, Object> mutated = new java.util.LinkedHashMap<>(definition);
        mutated.put("steps", steps);

        assertThatThrownBy(() -> FlowDefinitionValidator.validateStructure(mutated))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("Cycle detected");
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readFixture() throws Exception {
        try (InputStream in = getClass().getClassLoader()
                .getResourceAsStream("flow-fixtures/conformance-chain.flow.json")) {
            assertThat(in).as("conformance-chain.flow.json fixture must be present").isNotNull();
            return objectMapper.readValue(in, Map.class);
        }
    }
}
