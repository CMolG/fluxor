package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FlowCanvas;
import com.javadaba.contexts.fluxor.domain.FlowCompiler;
import com.javadaba.contexts.fluxor.domain.FlowDefinitionValidator;
import com.javadaba.contexts.fluxor.domain.FlowLayout;
import com.javadaba.contexts.fluxor.domain.FlowOrigin;
import com.javadaba.contexts.fluxor.domain.FlowStatus;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import com.javadaba.contexts.fluxor.domain.ports.FluxorFlowRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Flow drafts (console) + publish/materialize (IDE) -- plan #19, Task 5 Steps 2-3 -- and, since
 * JAVA-163, the designer's flows: a canvas stored as drawn, compiled to {@code fluxor-flow} on every
 * save, laid out for a flow that has none, and exported. Validates every incoming definition
 * against {@link FlowDefinitionValidator} (structure) and its own size check (needs Jackson to
 * re-measure -- see this class's javadoc on {@code FlowDefinitionValidator}) before ever persisting
 * it. Contract: {@code doc://contracts/fluxor-flow}.
 */
@ApplicationScoped
public class FlowSyncService {

    private final FluxorFlowRepository flows;
    private final RelayBroadcaster relay;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Inject
    public FlowSyncService(FluxorFlowRepository flows, RelayBroadcaster relay, ObjectMapper objectMapper) {
        this(flows, relay, objectMapper, Clock.systemUTC());
    }

    FlowSyncService(FluxorFlowRepository flows, RelayBroadcaster relay, ObjectMapper objectMapper, Clock clock) {
        this.flows = flows;
        this.relay = relay;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    /** A flow with the canvas to draw it (stored, or laid out from its definition) and, when it does
     *  not compile, why. */
    public record FlowDetail(FluxorFlow flow, Map<String, Object> canvas, List<String> problems) {
    }

    /** {@code POST /fluxor/v1/flows} with a {@code definition} (session) -- an import, or a console
     *  draft: checked against the whole format, stored as sent, {@code DRAFT}/{@code CONSOLE}. A
     *  blank {@code name} takes the document's own. */
    public FluxorFlow createDraft(UUID accountId, String name, Map<String, Object> definition) {
        validate(definition);
        String flowName = name == null || name.isBlank() ? (String) definition.get("name") : name;
        FluxorFlow flow = new FluxorFlow(UUID.randomUUID(), accountId, requireName(flowName), definition, null,
                FlowOrigin.CONSOLE, FlowStatus.DRAFT, 1, Instant.now(clock));
        flows.upsert(flow);
        publish(flow);
        return flow;
    }

    /** {@code POST /fluxor/v1/flows} with a {@code canvas} (session) -- a new flow from the designer. */
    public FlowDetail createFromCanvas(UUID accountId, String name, Map<String, Object> canvas) {
        String flowName = (name == null || name.isBlank()) && canvas != null
                && canvas.get("name") instanceof String drawn ? drawn : name;
        return save(new FluxorFlow(UUID.randomUUID(), accountId, requireName(flowName), null, canvas,
                FlowOrigin.DESIGNER, FlowStatus.DRAFT, 1, Instant.now(clock)), null);
    }

    /** {@code PUT /fluxor/v1/flows/{id}} (session) -- the designer saves its canvas; it compiles, or
     *  is stored with {@code definition: null} and the problems that keep it from compiling. */
    public FlowDetail update(UUID accountId, UUID id, String name, Map<String, Object> canvas,
            Integer expectedVersion) {
        if (expectedVersion == null) {
            throw new FluxorException("invalid_flow_request", "'expectedVersion' is required", 422);
        }
        FluxorFlow current = requireOwned(accountId, id);
        if (current.version() != expectedVersion) {
            throw versionConflict(current.version(), expectedVersion);
        }
        String flowName = name == null ? current.name() : requireName(name);
        return save(new FluxorFlow(id, accountId, flowName, null, canvas, FlowOrigin.DESIGNER, FlowStatus.DRAFT,
                expectedVersion + 1, Instant.now(clock)), expectedVersion);
    }

    public List<FluxorFlow> list(UUID accountId) {
        return flows.findByAccount(accountId);
    }

    public FluxorFlow get(UUID accountId, UUID id) {
        return requireOwned(accountId, id);
    }

    public FlowDetail detail(UUID accountId, UUID id) {
        return detail(requireOwned(accountId, id));
    }

    /** {@code GET /fluxor/v1/flows/{id}/export} -- the {@code fluxor-flow} document, only when there is one. */
    public FluxorFlow export(UUID accountId, UUID id) {
        FlowDetail detail = detail(accountId, id);
        if (detail.flow().definition() == null) {
            throw new FluxorException("flow_not_compilable",
                    "This flow does not compile yet, so there is no document to export.", 409, detail.problems());
        }
        return detail.flow();
    }

    /** {@code DELETE /fluxor/v1/flows/{id}} -- the flow and its runs. */
    public void delete(UUID accountId, UUID id) {
        FluxorFlow flow = requireOwned(accountId, id);
        flows.delete(id);
        relay.publish(accountId, "flow.deleted", Map.of("id", flow.id().toString()));
    }

    /** {@code GET /fluxor/v1/sync/flows?since=} (device) -- the IDE pulls to discover console
     *  drafts it needs to materialize. Returns every flow with a definition since the cursor (not
     *  just drafts): a device re-syncing after downtime should see every change, same
     *  tombstone-style "give me everything since X" shape as task sync. */
    public SyncPage pull(UUID accountId, String sinceCursor, int limit) {
        Optional<SyncCursor.Decoded> since = SyncCursor.decode(sinceCursor);
        List<FluxorFlow> page = flows.findSince(accountId, since.map(SyncCursor.Decoded::updatedAt).orElse(null),
                since.map(SyncCursor.Decoded::id).orElse(null), limit);
        String nextCursor = page.size() < limit || page.isEmpty()
                ? null
                : SyncCursor.encode(page.get(page.size() - 1).updatedAt(), page.get(page.size() - 1).id());
        return new SyncPage(page, nextCursor);
    }

    /** {@code PUT /fluxor/v1/sync/flows/{id}} (device) -- always ends up {@code origin=IDE,
     *  status=SYNCED} regardless of whether it started as a console draft (plan's literal Task 5
     *  Step 2: "once one is materialized, the IDE re-publishes it synced -- the draft dies
     *  there -- a single owner of the final state"). The pushed document replaces the design, so
     *  the stored canvas goes and the next read lays the new one out. Another account's id is not
     *  found, never overwritten. */
    public FluxorFlow push(UUID accountId, UUID id, String name, Map<String, Object> definition) {
        validate(definition);
        Optional<FluxorFlow> existing = flows.findById(id);
        if (existing.isPresent() && !existing.get().accountId().equals(accountId)) {
            throw notFound(id);
        }
        int version = existing.map(f -> f.version() + 1).orElse(1);
        FluxorFlow flow = new FluxorFlow(id, accountId, requireName(name), definition, null, FlowOrigin.IDE,
                FlowStatus.SYNCED, version, Instant.now(clock));
        flows.upsert(flow);
        publish(flow);
        return flow;
    }

    /** Stores a drawn flow with what it compiles to. {@code expectedVersion} null is a new flow; otherwise
     *  the write only lands while the stored flow is still at that version, so of two saves from the
     *  same read the second answers 409 instead of silently overwriting the first. */
    private FlowDetail save(FluxorFlow drawn, Integer expectedVersion) {
        FlowCanvas.validateSize(bytes(drawn.canvas(), "invalid_flow_canvas"));
        FlowCompiler.Compiled compiled = compile(drawn);
        FluxorFlow flow = new FluxorFlow(drawn.id(), drawn.accountId(), drawn.name(), compiled.definition(),
                drawn.canvas(), drawn.origin(), drawn.status(), drawn.version(), drawn.updatedAt());
        if (expectedVersion == null) {
            flows.upsert(flow);
        } else if (!flows.update(flow, expectedVersion)) {
            FluxorFlow now = requireOwned(drawn.accountId(), drawn.id());
            throw versionConflict(now.version(), expectedVersion);
        }
        publish(flow);
        return new FlowDetail(flow, flow.canvas(), compiled.problems());
    }

    private FlowDetail detail(FluxorFlow flow) {
        if (flow.canvas() == null) {
            return new FlowDetail(flow, FlowLayout.layout(flow.definition(), flow.name()), List.of());
        }
        List<String> problems = flow.definition() == null ? compile(flow).problems() : List.of();
        return new FlowDetail(flow, flow.canvas(), problems);
    }

    /** The compile, plus the format's size cap: a note copied into many steps' {@code context} can
     *  push the document past what {@link FlowDefinitionValidator} accepts on import, and a document
     *  this API would refuse to take back is not one it hands out. */
    private FlowCompiler.Compiled compile(FluxorFlow flow) {
        FlowCompiler.Compiled compiled = FlowCompiler.compile(flow.canvas(), flow.id().toString(), flow.name());
        if (compiled.definition() == null) {
            return compiled;
        }
        int size = bytes(compiled.definition(), "invalid_flow_canvas");
        if (size <= FlowDefinitionValidator.MAX_DEFINITION_BYTES) {
            return compiled;
        }
        return new FlowCompiler.Compiled(null, List.of("The compiled flow is " + size + " bytes, over the "
                + FlowDefinitionValidator.MAX_DEFINITION_BYTES + "-byte limit of a flow document. A note attached"
                + " to several steps is copied into each of them: shorten it or attach it to fewer steps."));
    }

    private static FluxorException versionConflict(int current, int expected) {
        return new FluxorException("version_conflict", "The flow changed since it was read: it is at version "
                + current + ", not " + expected + ". Read it again.", 409);
    }

    private void validate(Map<String, Object> definition) {
        FlowDefinitionValidator.validateSize(bytes(definition, "invalid_flow_definition"));
        FlowDefinitionValidator.validateStructure(definition);
    }

    private int bytes(Map<String, Object> json, String code) {
        try {
            return objectMapper.writeValueAsBytes(json).length;
        } catch (JsonProcessingException ex) {
            throw new FluxorException(code, "Not serializable JSON", 422);
        }
    }

    private String requireName(String name) {
        if (name == null || name.isBlank()) {
            throw new FluxorException("invalid_flow_name", "'name' is required", 422);
        }
        return name.trim();
    }

    private FluxorFlow requireOwned(UUID accountId, UUID id) {
        return flows.findById(id)
                .filter(f -> f.accountId().equals(accountId))
                .orElseThrow(() -> notFound(id));
    }

    private static FluxorException notFound(UUID id) {
        return new FluxorException("flow_not_found", "Flow not found: " + id, 404);
    }

    private void publish(FluxorFlow flow) {
        relay.publish(flow.accountId(), "flow.updated", Map.of(
                "id", flow.id().toString(),
                "status", flow.status().toDb(),
                "origin", flow.origin().toDb(),
                "version", flow.version()));
    }

    public record SyncPage(List<FluxorFlow> flows, String nextCursor) {
    }
}
