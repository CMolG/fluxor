package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import com.javadaba.contexts.fluxor.domain.FluxorRun;
import com.javadaba.contexts.fluxor.domain.FluxorRunEvent;
import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.HarnessAccess;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;
import com.javadaba.contexts.fluxor.domain.HarnessProject;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Shared JSON view records for the Fluxor domain objects that carry enum fields ({@code
 * TaskSource}, {@code FlowOrigin}/{@code FlowStatus}, {@code RunStatus}). Both {@code apps-api}
 * (session-gated console resources) and {@code fluxor-infrastructure} (device-gated sync
 * resource) need the EXACT same lowercase-string shape on the wire, so it lives here (a module
 * both already depend on) instead of being duplicated per resource class.
 *
 * <p>Why this exists at all: returning {@code FluxorTask}/{@code FluxorFlow}/{@code FluxorRun}
 * domain records DIRECTLY from a JAX-RS method serializes their enum fields via Jackson's default
 * {@code name()} ({@code "CONSOLE"}, {@code "DRAFT"}...), not {@code toDb()} ({@code "console"},
 * {@code "draft"}...) -- caught by {@code FluxorFlowRunHttpRoutingTest} expecting the lowercase DB
 * form the rest of this API (task {@code state}, which is a plain String) already uses. Same
 * discipline {@code NotifyManageResource}/{@code SocialManageResource} already follow with their
 * own {@code ProviderView}/{@code ConnectionView} records -- domain objects are never serialized
 * as-is when they carry an enum.
 */
public final class FluxorJson {

    private FluxorJson() {
    }

    public record TaskView(String id, String accountId, String title, String body, String state, int priority,
            String epicRef, String source, String externalRef, int version, Instant updatedAt, String updatedBy,
            boolean deleted) {
        public static TaskView of(FluxorTask t) {
            return new TaskView(t.id().toString(), t.accountId().toString(), t.title(), t.body(), t.state(),
                    t.priority(), t.epicRef(), t.source().toDb(), t.externalRef(), t.version(), t.updatedAt(),
                    t.updatedBy(), t.deleted());
        }

        public static List<TaskView> of(List<FluxorTask> tasks) {
            return tasks.stream().map(TaskView::of).toList();
        }
    }

    public record TaskSyncPageView(List<TaskView> tasks, String nextCursor) {
        public static TaskSyncPageView of(TaskSyncService.SyncPage page) {
            return new TaskSyncPageView(TaskView.of(page.tasks()), page.nextCursor());
        }
    }

    public record FlowView(String id, String accountId, String name, Map<String, Object> definition, String origin,
            String status, int version, Instant updatedAt) {
        public static FlowView of(FluxorFlow f) {
            return new FlowView(f.id().toString(), f.accountId().toString(), f.name(), f.definition(),
                    f.origin().toDb(), f.status().toDb(), f.version(), f.updatedAt());
        }

        public static List<FlowView> of(List<FluxorFlow> flows) {
            return flows.stream().map(FlowView::of).toList();
        }
    }

    /**
     * One flow as {@code GET /fluxor/v1/flows/{id}} answers it (JAVA-163): its definition, or null
     * plus the {@code problems} that keep its canvas from compiling, and the canvas to draw. MCP's
     * {@code flows.get} leaves the canvas out: an agent reads the document, not the drawing.
     */
    public record FlowDetailView(String id, String accountId, String name, Map<String, Object> definition,
            List<String> problems, @JsonInclude(JsonInclude.Include.NON_NULL) Map<String, Object> canvas,
            String origin, String status, int version, Instant updatedAt) {
        public static FlowDetailView of(FlowSyncService.FlowDetail detail, boolean withCanvas) {
            FluxorFlow f = detail.flow();
            return new FlowDetailView(f.id().toString(), f.accountId().toString(), f.name(), f.definition(),
                    detail.problems(), withCanvas ? detail.canvas() : null, f.origin().toDb(), f.status().toDb(),
                    f.version(), f.updatedAt());
        }
    }

    public record FlowSyncPageView(List<FlowView> flows, String nextCursor) {
        public static FlowSyncPageView of(FlowSyncService.SyncPage page) {
            return new FlowSyncPageView(FlowView.of(page.flows()), page.nextCursor());
        }
    }

    public record RunView(String id, String accountId, String flowId, String deviceId, String status,
            Instant startedAt, Instant finishedAt, Map<String, Object> summary) {
        public static RunView of(FluxorRun r) {
            return new RunView(r.id().toString(), r.accountId().toString(), r.flowId().toString(),
                    r.deviceId() == null ? null : r.deviceId().toString(), r.status().toDb(), r.startedAt(),
                    r.finishedAt(), r.summary());
        }

        public static List<RunView> of(List<FluxorRun> runs) {
            return runs.stream().map(RunView::of).toList();
        }
    }

    /**
     * A catalog entry in a listing: no body or spec, which can be long. The two spec fields a picker
     * needs ride along (JAVA-160): {@code exclusiveGroup}, so a client keeps one role active, and a
     * hook's {@code event}, so it can tell prehooks from posthooks.
     */
    /**
     * Whose an item is, as the reading account sees it (card://JAVA-750): null on a market item. {@code
     * mine} says the reader wrote it, so it may change it.
     */
    public record HarnessOwnView(String visibility, boolean mine, boolean retired, String harnessProjectId,
            String organizationAccountId) {
        static HarnessOwnView of(HarnessItem item, UUID reader) {
            HarnessOwnership own = item.ownership();
            return own == null
                    ? null
                    : new HarnessOwnView(own.visibility().wire(), own.ownerAccountId().equals(reader),
                            own.retired(), own.harnessProjectId() == null ? null : own.harnessProjectId().toString(),
                            own.organizationAccountId() == null ? null : own.organizationAccountId().toString());
        }
    }

    public record HarnessItemSummaryView(String key, String kind, int version, String title, String description,
            String marketVersion, String contentHash, String exclusiveGroup, String event, HarnessOwnView own) {
        public static List<HarnessItemSummaryView> of(List<HarnessItem> items, UUID reader) {
            return items.stream().map(i -> new HarnessItemSummaryView(i.key(), i.kind().toDb(), i.version(), i.title(),
                    i.description(), i.marketVersion(), i.contentHash(), specString(i, "exclusiveGroup"),
                    specString(i, "event"), HarnessOwnView.of(i, reader))).toList();
        }

        private static String specString(HarnessItem item, String field) {
            return item.spec() != null && item.spec().get(field) instanceof String value ? value : null;
        }
    }

    public record HarnessItemView(String key, String kind, int version, String title, String description, String body,
            Map<String, Object> spec, String provenance, String marketVersion, String contentHash, HarnessOwnView own) {
        public static HarnessItemView of(HarnessItem i, UUID reader) {
            return new HarnessItemView(i.key(), i.kind().toDb(), i.version(), i.title(), i.description(), i.body(),
                    i.spec(), i.provenance(), i.marketVersion(), i.contentHash(), HarnessOwnView.of(i, reader));
        }
    }

    /**
     * A harness project as the reading account sees it: {@code access} is {@code owner}, {@code editor}
     * or {@code viewer} (card://JAVA-2006), and {@code sharedThrough} names the Officium project a shared
     * one comes through (null for the account's own, and on a detail read).
     */
    public record HarnessProjectView(String id, String name, String officiumProjectId, long revision,
            Instant updatedAt, String access, String sharedThrough) {
        /** A project the account has just created: its own. */
        public static HarnessProjectView of(HarnessProject p) {
            return of(p, HarnessAccess.OWNER, null);
        }

        public static HarnessProjectView of(HarnessProject p, HarnessAccess access, String sharedThrough) {
            return new HarnessProjectView(p.id().toString(), p.name(),
                    p.officiumProjectId() == null ? null : p.officiumProjectId().toString(), p.revision(),
                    p.updatedAt(), access.wire(), sharedThrough);
        }

        public static List<HarnessProjectView> of(List<HarnessService.SharedProject> projects) {
            return projects.stream().map(s -> of(s.project(), s.access(), s.sharedThrough())).toList();
        }
    }

    public record HarnessProjectItemView(String key, String kind, int version, String title,
            Map<String, Object> params, long changedRevision) {
        public static List<HarnessProjectItemView> of(List<HarnessService.Entry> entries) {
            return entries.stream().map(e -> new HarnessProjectItemView(e.item().itemKey(), e.catalog().kind().toDb(),
                    e.item().itemVersion(), e.catalog().title(), e.item().params(), e.item().changedRevision()))
                    .toList();
        }
    }

    public record HarnessProjectDetailView(HarnessProjectView project, List<HarnessProjectItemView> items) {
        public static HarnessProjectDetailView of(HarnessService.ProjectHarness h) {
            return new HarnessProjectDetailView(HarnessProjectView.of(h.project(), h.access(), null),
                    HarnessProjectItemView.of(h.items()));
        }
    }

    /** A changed item carries its catalog body and spec, so one pull is enough to write it to disk. */
    public record HarnessChangedItemView(String key, String kind, int version, String title, Map<String, Object> params,
            long changedRevision, String body, Map<String, Object> spec) {
    }

    public record HarnessChangesView(String projectId, long revision, boolean full,
            List<HarnessChangedItemView> changed, List<String> removed) {
        public static HarnessChangesView of(HarnessService.Changes c) {
            return new HarnessChangesView(c.project().id().toString(), c.project().revision(), c.full(),
                    c.changed().stream().map(e -> new HarnessChangedItemView(e.item().itemKey(),
                            e.catalog().kind().toDb(), e.item().itemVersion(), e.catalog().title(), e.item().params(),
                            e.item().changedRevision(), e.catalog().body(), e.catalog().spec())).toList(),
                    c.removed());
        }
    }

    /**
     * A preset as the public page of what a setup installs shows it (JAVA-676): each item's words,
     * and for a hook when it runs and what it sends. No body, script or param: those are what the
     * snapshot writes, and this read is about what the user is consenting to.
     */
    public record PublicPresetView(String key, int version, String title, String description,
            List<PublicPresetItemView> items) {
        public static PublicPresetView of(HarnessService.PresetContents contents) {
            HarnessItem preset = contents.preset();
            return new PublicPresetView(preset.key(), preset.version(), preset.title(), preset.description(),
                    contents.items().stream().map(PublicPresetItemView::of).toList());
        }
    }

    /** {@code hook} only on a hook. */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record PublicPresetItemView(String key, String kind, int version, String title, String description,
            PublicHookView hook) {
        static PublicPresetItemView of(HarnessItem item) {
            return new PublicPresetItemView(item.key(), item.kind().toDb(), item.version(), item.title(),
                    item.description(), item.kind() == HarnessItemKind.HOOK ? PublicHookView.of(item.spec()) : null);
        }
    }

    /**
     * The market's hook manifest fields a person consents to ({@code hook.schema.json}). Every field
     * is written even when null, {@code sends} above all: null there is the hook's own statement
     * that it sends nothing, and a reader must be able to tell it from a field left out.
     */
    @JsonInclude(JsonInclude.Include.ALWAYS)
    public record PublicHookView(String event, List<?> tools, List<?> notifications, Integer timeoutMs,
            Map<?, ?> sends) {
        static PublicHookView of(Map<String, Object> spec) {
            Map<String, Object> s = spec == null ? Map.of() : spec;
            return new PublicHookView(s.get("event") instanceof String event ? event : null,
                    s.get("tools") instanceof List<?> tools ? tools : null,
                    s.get("notifications") instanceof List<?> notifications ? notifications : null,
                    s.get("timeoutMs") instanceof Number timeout ? timeout.intValue() : null,
                    s.get("sends") instanceof Map<?, ?> sends ? sends : null);
        }
    }

    public record RunEventView(String runId, int seq, String stepId, String type, Map<String, Object> payload,
            Instant at) {
        public static RunEventView of(FluxorRunEvent e) {
            return new RunEventView(e.runId().toString(), e.seq(), e.stepId(), e.type(), e.payload(), e.at());
        }

        public static List<RunEventView> of(List<FluxorRunEvent> events) {
            return events.stream().map(RunEventView::of).toList();
        }
    }
}
