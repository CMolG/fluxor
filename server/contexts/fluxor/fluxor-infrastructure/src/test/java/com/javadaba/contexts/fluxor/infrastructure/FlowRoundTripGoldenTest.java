package com.javadaba.contexts.fluxor.infrastructure;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FlowCompiler;
import com.javadaba.contexts.fluxor.domain.FlowDefinitionValidator;
import com.javadaba.contexts.fluxor.domain.FlowLayout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.io.InputStream;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The round trip of {@code doc://contracts/fluxor-flow}: each of fluxor-ide's five
 * {@code sdk/conformance} goldens (copied byte-identical from {@code feat/cockpit}) is imported,
 * laid out as a canvas, sent through JSON the way the designer sends it, and compiled back to the
 * same document. Only the top-level {@code id} changes (it becomes the flow's), and a legacy
 * {@code format} tag comes back as {@code fluxor-flow}.
 */
class FlowRoundTripGoldenTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @ParameterizedTest
    @ValueSource(strings = {"chain", "contract", "feedback-mode", "legacy-format", "loop"})
    void aGoldenComesBackFromItsCanvasUnchanged(String golden) throws Exception {
        Map<String, Object> definition = read("flow-fixtures/conformance-" + golden + ".flow.json");
        FlowDefinitionValidator.validateStructure(definition);

        Map<String, Object> canvas = throughJson(FlowLayout.layout(definition, "unused"));
        FlowCompiler.Compiled compiled = FlowCompiler.compile(canvas, "flow-id", (String) definition.get("name"));

        assertThat(compiled.problems()).isEmpty();
        FlowDefinitionValidator.validateStructure(compiled.definition());
        assertThat(compiled.definition()).containsEntry("id", "flow-id").containsEntry("format", "fluxor-flow");
        assertThat(withoutIdAndFormat(throughJson(compiled.definition()))).isEqualTo(withoutIdAndFormat(definition));
    }

    private Map<String, Object> withoutIdAndFormat(Map<String, Object> document) {
        Map<String, Object> rest = new LinkedHashMap<>(document);
        rest.remove("id");
        rest.remove("format");
        return rest;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> throughJson(Map<String, Object> value) throws Exception {
        return objectMapper.readValue(objectMapper.writeValueAsBytes(value), Map.class);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> read(String resource) throws Exception {
        try (InputStream in = getClass().getClassLoader().getResourceAsStream(resource)) {
            assertThat(in).as(resource + " must be present").isNotNull();
            return objectMapper.readValue(in, Map.class);
        }
    }
}
