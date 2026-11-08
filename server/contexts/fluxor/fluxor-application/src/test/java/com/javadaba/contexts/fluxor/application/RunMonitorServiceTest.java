package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import com.javadaba.contexts.fluxor.domain.FluxorRun;
import com.javadaba.contexts.fluxor.domain.RunStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Plan #19, Task 5 Step 5: events out of order rejected, run of another account 404s, close
 *  fixes status immutably. */
class RunMonitorServiceTest {

    private final FakeFluxorFlowRepository flowRepo = new FakeFluxorFlowRepository();
    private final FakeFluxorRunRepositories.Runs runRepo = new FakeFluxorRunRepositories.Runs();
    private final FakeFluxorRunRepositories.Events eventRepo = new FakeFluxorRunRepositories.Events();
    private final RelayBroadcaster relay = new RelayBroadcaster();
    private RunMonitorService service;
    private UUID accountId;
    private UUID flowId;

    @BeforeEach
    void setUp() {
        service = new RunMonitorService(flowRepo, runRepo, eventRepo, relay, new ObjectMapper());
        accountId = UUID.randomUUID();
        FlowSyncService flowService = new FlowSyncService(flowRepo, relay, new ObjectMapper());
        FluxorFlow flow = flowService.createDraft(accountId, "Flow", Map.of("steps", List.of(
                Map.of("id", "step-a", "dependsOn", List.of()))));
        flowId = flow.id();
    }

    @Test
    void openCreatesRunningRun() {
        FluxorRun run = service.open(accountId, UUID.randomUUID(), flowId);
        assertThat(run.status()).isEqualTo(RunStatus.RUNNING);
        assertThat(run.finishedAt()).isNull();
    }

    @Test
    void openForUnknownFlowIsNotFound() {
        assertThatThrownBy(() -> service.open(accountId, UUID.randomUUID(), UUID.randomUUID()))
                .isInstanceOf(FluxorException.class);
    }

    @Test
    void aFlowThatDoesNotCompileCannotRun() {
        FlowSyncService flowService = new FlowSyncService(flowRepo, relay, new ObjectMapper());
        UUID unfinished = flowService.createFromCanvas(accountId, "Unfinished", Map.of("version", 1, "nodes",
                List.of(), "edges", List.of())).flow().id();

        assertThatThrownBy(() -> service.open(accountId, UUID.randomUUID(), unfinished))
                .isInstanceOf(FluxorException.class)
                .hasMessageContaining("does not compile");
    }

    @Test
    void eventsMustBeStrictlyOrdered() {
        FluxorRun run = service.open(accountId, UUID.randomUUID(), flowId);

        service.appendEvents(accountId, run.id(), List.of(
                new RunMonitorService.EventInput(0, "step-a", "step-started", Map.of())));

        assertThatThrownBy(() -> service.appendEvents(accountId, run.id(), List.of(
                new RunMonitorService.EventInput(2, "step-a", "step-output", Map.of())))) // skipped seq 1
                .isInstanceOf(FluxorException.class);

        // Correct next seq applies cleanly.
        service.appendEvents(accountId, run.id(), List.of(
                new RunMonitorService.EventInput(1, "step-a", "step-passed", Map.of())));
        assertThat(service.eventsAfterSeq(accountId, run.id(), -1)).hasSize(2);
    }

    @Test
    void closeFixesStatusImmutably() {
        FluxorRun run = service.open(accountId, UUID.randomUUID(), flowId);
        service.close(accountId, run.id(), RunStatus.PASSED, Map.of("ok", true));

        assertThatThrownBy(() -> service.close(accountId, run.id(), RunStatus.FAILED, Map.of()))
                .isInstanceOf(FluxorException.class);

        assertThatThrownBy(() -> service.appendEvents(accountId, run.id(), List.of(
                new RunMonitorService.EventInput(0, "step-a", "step-started", Map.of()))))
                .isInstanceOf(FluxorException.class);
    }

    @Test
    void runFromAnotherAccountIsNotFound() {
        FluxorRun run = service.open(accountId, UUID.randomUUID(), flowId);
        assertThatThrownBy(() -> service.get(UUID.randomUUID(), run.id())).isInstanceOf(FluxorException.class);
    }
}
