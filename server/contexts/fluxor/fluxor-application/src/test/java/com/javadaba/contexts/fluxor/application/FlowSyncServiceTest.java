package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FlowOrigin;
import com.javadaba.contexts.fluxor.domain.FlowStatus;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Plan #19, Task 5 Step 5: draft->synced full round-trip, invalid definitions rejected. */
class FlowSyncServiceTest {

    private static final Map<String, Object> LINEAR_FLOW = Map.of("steps", List.of(
            Map.of("id", "step-a", "dependsOn", List.of()),
            Map.of("id", "step-b", "dependsOn", List.of("step-a"))));

    private final FakeFluxorFlowRepository repo = new FakeFluxorFlowRepository();
    private final RelayBroadcaster relay = new RelayBroadcaster();
    private FlowSyncService service;

    @BeforeEach
    void setUp() {
        service = new FlowSyncService(repo, relay, new ObjectMapper());
    }

    @Test
    void createDraftIsConsoleOriginAndDraftStatus() {
        UUID accountId = UUID.randomUUID();
        FluxorFlow flow = service.createDraft(accountId, "My flow", LINEAR_FLOW);
        assertThat(flow.origin()).isEqualTo(FlowOrigin.CONSOLE);
        assertThat(flow.status()).isEqualTo(FlowStatus.DRAFT);
        assertThat(flow.version()).isEqualTo(1);
    }

    @Test
    void invalidDefinitionIsRejectedAtCreation() {
        UUID accountId = UUID.randomUUID();
        Map<String, Object> cyclic = Map.of("steps", List.of(
                Map.of("id", "a", "dependsOn", List.of("b")),
                Map.of("id", "b", "dependsOn", List.of("a"))));
        assertThatThrownBy(() -> service.createDraft(accountId, "Bad flow", cyclic))
                .isInstanceOf(FluxorException.class);
    }

    @Test
    void devicePushMaterializesDraftToIdeSynced() {
        UUID accountId = UUID.randomUUID();
        FluxorFlow draft = service.createDraft(accountId, "My flow", LINEAR_FLOW);
        assertThat(draft.status()).isEqualTo(FlowStatus.DRAFT);

        FluxorFlow materialized = service.push(accountId, draft.id(), "My flow", LINEAR_FLOW);
        assertThat(materialized.origin()).isEqualTo(FlowOrigin.IDE);
        assertThat(materialized.status()).isEqualTo(FlowStatus.SYNCED);
        assertThat(materialized.version()).isEqualTo(2);
    }

    @Test
    void pullPaginates() {
        UUID accountId = UUID.randomUUID();
        service.createDraft(accountId, "Flow 1", LINEAR_FLOW);
        service.createDraft(accountId, "Flow 2", LINEAR_FLOW);
        service.createDraft(accountId, "Flow 3", LINEAR_FLOW);

        FlowSyncService.SyncPage page = service.pull(accountId, null, 2);
        assertThat(page.flows()).hasSize(2);
        assertThat(page.nextCursor()).isNotNull();
    }

    @Test
    void anotherAccountsFlowIsNotFound() {
        UUID accountId = UUID.randomUUID();
        FluxorFlow flow = service.createDraft(accountId, "Flow", LINEAR_FLOW);
        assertThatThrownBy(() -> service.get(UUID.randomUUID(), flow.id())).isInstanceOf(FluxorException.class);
    }

    // ── the designer's flows (JAVA-163) ─────────────────────────────────────────────────────

    @Test
    void aSavedCanvasIsStoredAndCompiled() {
        UUID accountId = UUID.randomUUID();
        FlowSyncService.FlowDetail created = service.createFromCanvas(accountId, "Designed", canvas(true));
        assertThat(created.flow().origin()).isEqualTo(FlowOrigin.DESIGNER);
        assertThat(created.flow().definition()).containsEntry("id", created.flow().id().toString())
                .containsEntry("name", "Designed").containsEntry("rootStepId", "a");
        assertThat(created.problems()).isEmpty();

        FlowSyncService.FlowDetail saved = service.update(accountId, created.flow().id(), null, canvas(false), 1);

        assertThat(saved.flow().version()).isEqualTo(2);
        assertThat(saved.flow().definition()).isNull();
        assertThat(saved.flow().canvas()).isEqualTo(canvas(false));
        assertThat(saved.problems()).singleElement().asString().contains("nothing before them");
        assertThat(service.detail(accountId, created.flow().id()).problems()).isEqualTo(saved.problems());
    }

    @Test
    void aStaleVersionIsAConflict() {
        UUID accountId = UUID.randomUUID();
        UUID id = service.createFromCanvas(accountId, "Designed", canvas(true)).flow().id();
        service.update(accountId, id, null, canvas(true), 1);

        assertThatThrownBy(() -> service.update(accountId, id, null, canvas(true), 1))
                .isInstanceOf(FluxorException.class)
                .extracting(e -> ((FluxorException) e).httpStatus()).isEqualTo(409);
    }

    @Test
    void ofTwoSavesFromTheSameReadTheSecondIsAConflictNotAnOverwrite() {
        UUID accountId = UUID.randomUUID();
        UUID id = service.createFromCanvas(accountId, "Designed", canvas(true)).flow().id();
        // The other tab's save lands between this save's version check and its write.
        FlowSyncService racing = new FlowSyncService(new FakeFluxorFlowRepository.Delegating(repo) {
            @Override
            public boolean update(FluxorFlow flow, int expectedVersion) {
                service.update(accountId, id, "Other tab", canvas(true), 1);
                return super.update(flow, expectedVersion);
            }
        }, relay, new ObjectMapper());

        assertThatThrownBy(() -> racing.update(accountId, id, "This tab", canvas(true), 1))
                .isInstanceOf(FluxorException.class)
                .satisfies(e -> {
                    FluxorException ex = (FluxorException) e;
                    assertThat(ex.httpStatus()).isEqualTo(409);
                    assertThat(ex.code()).isEqualTo("version_conflict");
                });
        assertThat(repo.findById(id).orElseThrow().name()).isEqualTo("Other tab");
    }

    @Test
    void aCompiledFlowOverTheFormatsSizeCapIsAProblemNotADocument() {
        UUID accountId = UUID.randomUUID();
        // A 10 KB note attached to 30 steps compiles into 30 copies of it, past the 256 KB a
        // fluxor-flow document may have, while the canvas itself stays small.
        List<Map<String, Object>> nodes = new ArrayList<>();
        List<Map<String, Object>> edges = new ArrayList<>();
        nodes.add(Map.of("id", "note", "kind", "note", "x", 0, "y", 0, "width", 200, "height", 100,
                "text", "x".repeat(10_000)));
        for (int i = 0; i < 30; i++) {
            nodes.add(step("s" + i));
            edges.add(edge("attach-" + i, "note", "s" + i, "attachment"));
            if (i > 0) {
                edges.add(edge("link-" + i, "s0", "s" + i, "link"));
            }
        }
        Map<String, Object> canvas = Map.of("version", 1, "name", "Heavy", "description", "", "nodes", nodes,
                "edges", edges);

        FlowSyncService.FlowDetail saved = service.createFromCanvas(accountId, "Heavy", canvas);

        assertThat(saved.flow().definition()).isNull();
        assertThat(saved.problems()).singleElement().asString().contains("byte limit");
        assertThat(service.detail(accountId, saved.flow().id()).problems()).isEqualTo(saved.problems());
        assertThatThrownBy(() -> service.export(accountId, saved.flow().id()))
                .extracting(e -> ((FluxorException) e).code()).isEqualTo("flow_not_compilable");
    }

    @Test
    void aFlowWithNoCanvasIsLaidOutOnRead() {
        UUID accountId = UUID.randomUUID();
        FluxorFlow imported = service.createDraft(accountId, null, Map.of("name", "Imported", "steps", List.of(
                Map.of("id", "step-a", "dependsOn", List.of()))));

        FlowSyncService.FlowDetail detail = service.detail(accountId, imported.id());

        assertThat(imported.name()).isEqualTo("Imported");
        assertThat(detail.canvas()).containsEntry("name", "Imported").containsKey("nodes");
        assertThat(detail.problems()).isEmpty();
    }

    @Test
    void onlyAFlowThatCompilesExports() {
        UUID accountId = UUID.randomUUID();
        UUID compiles = service.createFromCanvas(accountId, "Good", canvas(true)).flow().id();
        UUID doesNot = service.createFromCanvas(accountId, "Unfinished", canvas(false)).flow().id();

        assertThat(service.export(accountId, compiles).definition()).containsKey("steps");
        assertThatThrownBy(() -> service.export(accountId, doesNot))
                .isInstanceOf(FluxorException.class)
                .satisfies(e -> {
                    FluxorException ex = (FluxorException) e;
                    assertThat(ex.code()).isEqualTo("flow_not_compilable");
                    assertThat(ex.problems()).isNotEmpty();
                });
    }

    @Test
    void theIdeNeverPullsAFlowWithNoDefinition() {
        UUID accountId = UUID.randomUUID();
        FluxorFlow good = service.createDraft(accountId, "Good", LINEAR_FLOW);
        service.createFromCanvas(accountId, "Unfinished", canvas(false));

        assertThat(service.pull(accountId, null, 10).flows()).extracting(FluxorFlow::id).containsExactly(good.id());
    }

    @Test
    void deletingRemovesTheFlowOnlyForItsOwner() {
        UUID accountId = UUID.randomUUID();
        UUID id = service.createDraft(accountId, "Flow", LINEAR_FLOW).id();

        assertThatThrownBy(() -> service.delete(UUID.randomUUID(), id)).isInstanceOf(FluxorException.class);
        service.delete(accountId, id);
        assertThat(repo.findById(id)).isEmpty();
    }

    @Test
    void aDevicePushNeverOverwritesAnotherAccountsFlow() {
        UUID owner = UUID.randomUUID();
        FluxorFlow flow = service.createDraft(owner, "Mine", LINEAR_FLOW);

        assertThatThrownBy(() -> service.push(UUID.randomUUID(), flow.id(), "Theirs", LINEAR_FLOW))
                .isInstanceOf(FluxorException.class)
                .extracting(e -> ((FluxorException) e).httpStatus()).isEqualTo(404);
        assertThat(repo.findById(flow.id()).orElseThrow().name()).isEqualTo("Mine");
    }

    @Test
    void aDevicePushReplacesTheDesign() {
        UUID accountId = UUID.randomUUID();
        UUID id = service.createFromCanvas(accountId, "Designed", canvas(true)).flow().id();

        FluxorFlow pushed = service.push(accountId, id, "Designed", LINEAR_FLOW);

        assertThat(pushed.canvas()).isNull();
        assertThat(service.detail(accountId, id).canvas()).containsKey("nodes");
    }

    @Test
    @SuppressWarnings("unchecked")
    void aTypedNoteAttachedAsPrimaryInputIsExportedAsInputs() {
        UUID accountId = UUID.randomUUID();
        Map<String, Object> note = Map.of("id", "n1", "kind", "note", "x", 0, "y", 0, "width", 200, "height", 140,
                "text", "Rival is slow", "type", "CompetitorWeakness");
        Map<String, Object> attached = Map.of("id", "e1", "source", "n1", "target", "a", "sourceHandle", "bottom",
                "targetHandle", "top", "kind", "attachment", "mode", "primary-input");
        Map<String, Object> canvas = Map.of("version", 1, "name", "Typed", "description", "", "contextMode", "blind",
                "nodes", List.of(step("a"), note), "edges", List.of(attached));

        UUID id = service.createFromCanvas(accountId, "Typed", canvas).flow().id();

        List<Map<String, Object>> steps = (List<Map<String, Object>>) service.export(accountId, id).definition()
                .get("steps");
        assertThat(steps.get(0)).containsEntry("inputs",
                Map.of("primaryInput", List.of(Map.of("type", "CompetitorWeakness", "notes", List.of("n1")))));
    }

    /** One step, or two unlinked steps (two first steps, so it does not compile). */
    private static Map<String, Object> canvas(boolean compiles) {
        List<Map<String, Object>> nodes = new ArrayList<>(List.of(step("a")));
        if (!compiles) {
            nodes.add(step("b"));
        }
        return Map.of("version", 1, "name", "Drawn", "description", "", "contextMode", "blind", "nodes", nodes,
                "edges", List.of());
    }

    private static Map<String, Object> step(String id) {
        return Map.of("id", id, "kind", "step", "x", 0, "y", 0, "width", 300, "height", 190, "title", id,
                "description", "", "prompt", "Do " + id, "stepType", "llm_call");
    }

    private static Map<String, Object> edge(String id, String source, String target, String kind) {
        return Map.of("id", id, "source", source, "target", target, "sourceHandle", "bottom", "targetHandle", "top",
                "kind", kind);
    }
}
