package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import com.javadaba.contexts.fluxor.domain.FluxorRun;
import com.javadaba.contexts.fluxor.domain.FluxorRunEvent;
import com.javadaba.contexts.fluxor.domain.RunStatus;
import com.javadaba.contexts.fluxor.domain.ports.FluxorFlowRepository;
import com.javadaba.contexts.fluxor.domain.ports.FluxorRunEventRepository;
import com.javadaba.contexts.fluxor.domain.ports.FluxorRunRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Run monitoring (plan #19, Task 5 Step 4) -- opened/closed and streamed by the DEVICE (the IDE is
 * the only runtime; the server mirrors), read by the console (session) either live over the relay
 * (Task 6) or via polling {@link #eventsAfterSeq} ("el polling ES el fallback oficial del WS --
 * mismo shape").
 */
@ApplicationScoped
public class RunMonitorService {

    private static final int MAX_EVENT_PAYLOAD_BYTES = 8 * 1024;

    private final FluxorFlowRepository flows;
    private final FluxorRunRepository runs;
    private final FluxorRunEventRepository events;
    private final RelayBroadcaster relay;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Inject
    public RunMonitorService(FluxorFlowRepository flows, FluxorRunRepository runs, FluxorRunEventRepository events,
            RelayBroadcaster relay, ObjectMapper objectMapper) {
        this(flows, runs, events, relay, objectMapper, Clock.systemUTC());
    }

    RunMonitorService(FluxorFlowRepository flows, FluxorRunRepository runs, FluxorRunEventRepository events,
            RelayBroadcaster relay, ObjectMapper objectMapper, Clock clock) {
        this.flows = flows;
        this.runs = runs;
        this.events = events;
        this.relay = relay;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    /** {@code POST /fluxor/v1/sync/runs} (device) -- opens a run, linking flow+device. */
    public FluxorRun open(UUID accountId, UUID deviceId, UUID flowId) {
        FluxorFlow flow = flows.findById(flowId)
                .filter(f -> f.accountId().equals(accountId))
                .orElseThrow(() -> new FluxorException("flow_not_found", "Flow not found: " + flowId, 404));
        if (flow.definition() == null) {
            throw new FluxorException("flow_not_compilable", "This flow does not compile yet, so it cannot run.", 409);
        }
        FluxorRun run = new FluxorRun(UUID.randomUUID(), accountId, flow.id(), deviceId, RunStatus.RUNNING,
                Instant.now(clock), null, null);
        runs.save(run);
        relay.publish(accountId, "run.opened", Map.of("id", run.id().toString(), "flowId", flow.id().toString()));
        return run;
    }

    /** {@code POST /fluxor/v1/sync/runs/{id}/events} (device) -- batch append, strictly ordered by
     *  {@code seq} (continuing from the run's current max), capped at {@value
     *  #MAX_EVENT_PAYLOAD_BYTES} bytes/event (no file contents). */
    public List<FluxorRunEvent> appendEvents(UUID accountId, UUID runId, List<EventInput> batch) {
        FluxorRun run = requireOwned(accountId, runId);
        if (run.status().isTerminal()) {
            throw new FluxorException("run_closed", "Cannot append events to a closed run", 409);
        }
        int expectedNext = events.maxSeq(runId) + 1;
        List<FluxorRunEvent> toAppend = new ArrayList<>();
        Instant now = Instant.now(clock);
        for (EventInput input : batch) {
            if (input.seq() != expectedNext) {
                throw new FluxorException("out_of_order_event",
                        "Expected seq " + expectedNext + " but got " + input.seq(), 422);
            }
            validatePayloadSize(input.payload());
            toAppend.add(new FluxorRunEvent(runId, input.seq(), input.stepId(), input.type(), input.payload(), now));
            expectedNext++;
        }
        events.appendAll(toAppend);
        relay.publish(accountId, "run.event", Map.of("runId", runId.toString(), "count", toAppend.size(),
                "lastSeq", toAppend.isEmpty() ? -1 : toAppend.get(toAppend.size() - 1).seq()));
        return toAppend;
    }

    /** {@code POST /fluxor/v1/sync/runs/{id}/close} (device) -- terminal, immutable once set. */
    public FluxorRun close(UUID accountId, UUID runId, RunStatus status, Map<String, Object> summary) {
        FluxorRun run = requireOwned(accountId, runId);
        if (run.status().isTerminal()) {
            throw new FluxorException("run_already_closed", "Run " + runId + " is already closed", 409);
        }
        if (!status.isTerminal()) {
            throw new FluxorException("invalid_run_status", "close() requires a terminal status "
                    + "(passed/failed/cancelled), got " + status.toDb(), 422);
        }
        FluxorRun closed = new FluxorRun(run.id(), run.accountId(), run.flowId(), run.deviceId(), status,
                run.startedAt(), Instant.now(clock), summary);
        runs.updateStatus(closed);
        relay.publish(accountId, "run.closed", Map.of("id", runId.toString(), "status", status.toDb()));
        return closed;
    }

    public List<FluxorRun> list(UUID accountId, UUID flowId, RunStatus status) {
        return runs.findByAccount(accountId, flowId, status);
    }

    public FluxorRun get(UUID accountId, UUID runId) {
        return requireOwned(accountId, runId);
    }

    public List<FluxorRunEvent> eventsAfterSeq(UUID accountId, UUID runId, int afterSeq) {
        requireOwned(accountId, runId);
        return events.findAfterSeq(runId, afterSeq);
    }

    private FluxorRun requireOwned(UUID accountId, UUID runId) {
        return runs.findById(runId)
                .filter(r -> r.accountId().equals(accountId))
                .orElseThrow(() -> new FluxorException("run_not_found", "Run not found: " + runId, 404));
    }

    private void validatePayloadSize(Map<String, Object> payload) {
        try {
            int size = objectMapper.writeValueAsBytes(payload == null ? Map.of() : payload).length;
            if (size > MAX_EVENT_PAYLOAD_BYTES) {
                throw new FluxorException("event_payload_too_large",
                        "Run event payload exceeds the " + MAX_EVENT_PAYLOAD_BYTES + "-byte cap (" + size + " bytes)",
                        413);
            }
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new FluxorException("invalid_event_payload", "Run event payload is not serializable JSON", 422);
        }
    }

    public record EventInput(int seq, String stepId, String type, Map<String, Object> payload) {
    }
}
