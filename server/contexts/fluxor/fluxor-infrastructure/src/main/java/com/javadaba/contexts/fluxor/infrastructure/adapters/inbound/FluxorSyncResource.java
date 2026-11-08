package com.javadaba.contexts.fluxor.infrastructure.adapters.inbound;

import com.javadaba.contexts.fluxor.application.FlowSyncService;
import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessEnrollmentService;
import com.javadaba.contexts.fluxor.application.HarnessService;
import com.javadaba.contexts.fluxor.application.HarnessSnapshotService;
import com.javadaba.contexts.fluxor.application.PackService;
import com.javadaba.contexts.fluxor.application.RunMonitorService;
import com.javadaba.contexts.fluxor.application.TaskSyncService;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.Pack;
import com.javadaba.contexts.fluxor.domain.RunStatus;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.PATCH;
import jakarta.ws.rs.DELETE;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.core.Context;
import jakarta.ws.rs.core.EntityTag;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Request;
import jakarta.ws.rs.core.Response;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Device-token-gated sync (plan #19, Tasks 4/5) -- guarded by {@link FluxorDeviceAuthFilter}, NOT
 * an account session (device tokens {@code jdbx_device_*} are their own auth plane). Lives in
 * {@code fluxor-infrastructure} (not {@code apps-api}) precisely BECAUSE it does NOT touch {@code
 * AccountSessionCodec} -- contrast with {@code FluxorTaskResource}/{@code FluxorFlowResource}/
 * {@code FluxorRunResource} (apps-api, session CRUD).
 *
 * <p>ALL device-sync routes (tasks/flows/runs) live in this ONE class under the common {@code
 * /fluxor/v1/sync} prefix -- deliberately not split across classes with their own class-level
 * {@code @Path("/fluxor/v1/sync/tasks")}/{@code .../flows} etc: that shape is exactly the
 * collision the {@code FormManageHttpResourceTest} landmine warns about (two classes rooted at
 * overlapping prefixes silently 404ing each other). One class, one root, sub-paths per resource.
 */
@Path("/fluxor/v1/sync")
@Produces(MediaType.APPLICATION_JSON)
public class FluxorSyncResource {

    private static final int DEFAULT_LIMIT = 100;
    private static final int MAX_LIMIT = 500;

    private final TaskSyncService taskSync;
    private final FlowSyncService flowSync;
    private final RunMonitorService runMonitor;
    private final HarnessSnapshotService snapshots;
    private final HarnessEnrollmentService enrollments;
    private final PackService packs;
    private final HarnessService harness;

    public FluxorSyncResource(TaskSyncService taskSync, FlowSyncService flowSync, RunMonitorService runMonitor,
            HarnessSnapshotService snapshots, HarnessEnrollmentService enrollments, PackService packs,
            HarnessService harness) {
        this.harness = harness;
        this.taskSync = taskSync;
        this.flowSync = flowSync;
        this.runMonitor = runMonitor;
        this.snapshots = snapshots;
        this.enrollments = enrollments;
        this.packs = packs;
    }

    // ── tasks (Task 4) ──────────────────────────────────────────────────────

    @GET
    @Path("/tasks")
    public FluxorJson.TaskSyncPageView pullTasks(
            @Context ContainerRequestContext ctx,
            @QueryParam("since") String since,
            @QueryParam("limit") Integer limit) {
        return FluxorJson.TaskSyncPageView.of(taskSync.pull(accountId(ctx), since, effectiveLimit(limit)));
    }

    @PUT
    @Path("/tasks/{id}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response pushTask(@Context ContainerRequestContext ctx, @PathParam("id") UUID id, TaskPushRequest request) {
        TaskSyncService.TaskPush push = new TaskSyncService.TaskPush(
                request.title(), request.body(), request.state(), request.priority() == null ? 3 : request.priority(),
                request.epicRef(), request.externalRef(), request.expectedVersion(),
                Boolean.TRUE.equals(request.deleted()));
        TaskSyncService.PushResult result = taskSync.push(accountId(ctx), deviceId(ctx), id, push);
        return switch (result) {
            case TaskSyncService.PushResult.Applied applied ->
                Response.ok(FluxorJson.TaskView.of(applied.task())).build();
            case TaskSyncService.PushResult.Conflict conflict -> Response.status(409)
                    .entity(conflict.current().map(FluxorJson.TaskView::of).orElse(null))
                    .build();
        };
    }

    // ── flows (Task 5 Step 2) ───────────────────────────────────────────────

    @GET
    @Path("/flows")
    public FluxorJson.FlowSyncPageView pullFlows(
            @Context ContainerRequestContext ctx,
            @QueryParam("since") String since,
            @QueryParam("limit") Integer limit) {
        return FluxorJson.FlowSyncPageView.of(flowSync.pull(accountId(ctx), since, effectiveLimit(limit)));
    }

    @PUT
    @Path("/flows/{id}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response pushFlow(@Context ContainerRequestContext ctx, @PathParam("id") UUID id, FlowPushRequest request) {
        var flow = flowSync.push(accountId(ctx), id, request.name(), request.definition());
        return Response.ok(FluxorJson.FlowView.of(flow)).build();
    }

    // ── runs (Task 5 Step 4) ────────────────────────────────────────────────

    @POST
    @Path("/runs")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response openRun(@Context ContainerRequestContext ctx, OpenRunRequest request) {
        var run = runMonitor.open(accountId(ctx), deviceId(ctx), request.flowId());
        return Response.status(Response.Status.CREATED).entity(FluxorJson.RunView.of(run)).build();
    }

    @POST
    @Path("/runs/{id}/events")
    @Consumes(MediaType.APPLICATION_JSON)
    public List<FluxorJson.RunEventView> appendRunEvents(
            @Context ContainerRequestContext ctx, @PathParam("id") UUID id, List<EventRequest> batch) {
        List<RunMonitorService.EventInput> inputs = batch.stream()
                .map(e -> new RunMonitorService.EventInput(e.seq(), e.stepId(), e.type(),
                        e.payload() == null ? Map.of() : e.payload()))
                .toList();
        return FluxorJson.RunEventView.of(runMonitor.appendEvents(accountId(ctx), id, inputs));
    }

    @POST
    @Path("/runs/{id}/close")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response closeRun(@Context ContainerRequestContext ctx, @PathParam("id") UUID id, CloseRunRequest request) {
        var run = runMonitor.close(accountId(ctx), id, RunStatus.fromDb(request.status()),
                request.summary() == null ? Map.of() : request.summary());
        return Response.ok(FluxorJson.RunView.of(run)).build();
    }

    // ── harness (JAVA-555, ADR 0019): what a paired writer pulls ─────────────

    @GET
    @Path("/harness/projects")
    public List<FluxorJson.HarnessProjectView> harnessProjects(@Context ContainerRequestContext ctx) {
        return FluxorJson.HarnessProjectView.of(snapshots.projects(accountId(ctx)));
    }

    /**
     * The snapshot's hash is its {@code ETag}: an unchanged harness answers 304 and the writer touches
     * nothing. {@code include=packs} is how a writer that knows packs (card://JAVA-286) asks for them.
     */
    @GET
    @Path("/harness/projects/{id}/snapshot")
    public Response harnessSnapshot(@Context ContainerRequestContext ctx, @Context Request request,
            @PathParam("id") UUID id, @QueryParam("include") String include) {
        HarnessSnapshotService.Snapshot snapshot = snapshots.snapshot(accountId(ctx), id, "packs".equals(include));
        EntityTag tag = new EntityTag(snapshot.hash());
        Response.ResponseBuilder notModified = request.evaluatePreconditions(tag);
        return (notModified != null ? notModified : Response.ok(snapshot)).tag(tag).build();
    }

    /** Content-addressed, so a blob never changes under its name and may be cached for good. */
    @GET
    @Path("/harness/blobs/{sha256}")
    @Produces(MediaType.APPLICATION_OCTET_STREAM)
    public Response harnessBlob(@Context ContainerRequestContext ctx, @PathParam("sha256") String sha256) {
        return Response.ok(snapshots.blob(accountId(ctx), sha256)).tag(new EntityTag(sha256))
                .header("Cache-Control", "private, max-age=31536000, immutable").build();
    }

    /**
     * The project's items changed from a machine (card://JAVA-2011, `fluxor-sync select`): the same change
     * and rules as the harness page's, so a workspace can set its selection from a script.
     */
    @PATCH
    @Path("/harness/projects/{id}/items")
    @Consumes(MediaType.APPLICATION_JSON)
    public FluxorJson.HarnessProjectDetailView selectItems(@Context ContainerRequestContext ctx,
            @PathParam("id") UUID id,
            SelectRequest request) {
        if (request == null || request.expectedRevision() == null) {
            throw new FluxorException("invalid_harness_change", "'expectedRevision' is required", 422);
        }
        return FluxorJson.HarnessProjectDetailView.of(harness.update(accountId(ctx), id, request.expectedRevision(),
                request.put(), request.remove()));
    }

    // ── packs (card://JAVA-286): a person's CEET pack, published from one of their projects ─────

    /** Publishes the pack (or a new version of it) and attaches it to this project. */
    @PUT
    @Path("/harness/projects/{id}/packs/{packId}")
    @Consumes(MediaType.APPLICATION_JSON)
    public PublishedPackView publishPack(@Context ContainerRequestContext ctx, @PathParam("id") UUID id,
            @PathParam("packId") String packId, PackUploadRequest request) {
        List<PackService.Upload> files = request == null || request.files() == null
                ? List.of()
                : request.files().stream().map(f -> f == null ? null : new PackService.Upload(f.path(), f.content()))
                        .toList();
        Pack pack = packs.publish(accountId(ctx), id, packId, files);
        return new PublishedPackView(pack.packId(), pack.role(), pack.profileVersion(), pack.files().size(),
                pack.publishedAt());
    }

    /** Detaches the pack from this project; the account's other projects keep it. */
    @DELETE
    @Path("/harness/projects/{id}/packs/{packId}")
    public Response detachPack(@Context ContainerRequestContext ctx, @PathParam("id") UUID id,
            @PathParam("packId") String packId) {
        packs.detach(accountId(ctx), id, packId);
        return Response.noContent().build();
    }

    /** Deletes the pack from Fluxor: every project drops it on its next pull. */
    @DELETE
    @Path("/harness/packs/{packId}")
    public Response unpublishPack(@Context ContainerRequestContext ctx, @PathParam("packId") String packId) {
        packs.unpublish(accountId(ctx), packId);
        return Response.noContent().build();
    }

    /**
     * Trades a one-time enrollment code for a device token. Anonymous: the code is the credential,
     * so {@link FluxorDeviceAuthFilter} lets this one route through and {@code IpRateLimitFilter}
     * limits it per IP, like pairing. The code travels in the body, never the path, so it stays out
     * of the access log and the edge analytics.
     */
    @POST
    @Path("/enrollments")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response enroll(EnrollRequest request) {
        HarnessEnrollmentService.Enrolled enrolled = request == null
                ? enrollments.redeem(null, null)
                : enrollments.redeem(request.code(), request.hostname());
        return Response.status(Response.Status.CREATED).entity(new EnrolledView(enrolled.deviceToken(),
                enrolled.device().id().toString(), enrolled.device().name(), enrolled.device().createdAt())).build();
    }

    // ── shared ───────────────────────────────────────────────────────────────

    private int effectiveLimit(Integer limit) {
        return (limit == null || limit <= 0) ? DEFAULT_LIMIT : Math.min(limit, MAX_LIMIT);
    }

    private UUID accountId(ContainerRequestContext ctx) {
        return (UUID) ctx.getProperty(FluxorDeviceAuthFilter.ACCOUNT_ID_PROPERTY);
    }

    private UUID deviceId(ContainerRequestContext ctx) {
        return (UUID) ctx.getProperty(FluxorDeviceAuthFilter.DEVICE_ID_PROPERTY);
    }

    public record TaskPushRequest(String title, String body, String state, Integer priority, String epicRef,
            String externalRef, int expectedVersion, Boolean deleted) {
    }

    public record FlowPushRequest(String name, Map<String, Object> definition) {
    }

    public record OpenRunRequest(UUID flowId) {
    }

    public record EventRequest(int seq, String stepId, String type, Map<String, Object> payload) {
    }

    public record CloseRunRequest(String status, Map<String, Object> summary) {
    }

    public record EnrollRequest(String code, String hostname) {
    }

    public record PackUploadRequest(List<PackFileRequest> files) {
    }

    public record SelectRequest(Long expectedRevision, List<HarnessService.ItemChange> put, List<String> remove) {
    }

    public record PackFileRequest(String path, String content) {
    }

    public record PublishedPackView(String packId, String role, String profileVersion, int files,
            Instant publishedAt) {
    }

    /** The only moment the device token exists in plaintext. */
    public record EnrolledView(String deviceToken, String deviceId, String name, Instant createdAt) {
    }
}
