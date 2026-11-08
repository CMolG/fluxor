package com.javadaba.contexts.fluxor.infrastructure.adapters.inbound;

import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessOwnItemService;
import com.javadaba.contexts.fluxor.application.HarnessPublishService;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.core.Context;
import jakarta.ws.rs.core.MediaType;

import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * What {@code fluxor-sync item publish} sends with the device token (card://JAVA-2007): first which of a
 * folder's files the blob store lacks, then the item with the bytes of only those. Under
 * {@code /fluxor/v1/sync/}, so {@link FluxorDeviceAuthFilter} authenticates it like every sync route.
 */
@Path("/fluxor/v1/sync/harness/items")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class FluxorSyncItemResource {

    private final HarnessPublishService publish;

    public FluxorSyncItemResource(HarnessPublishService publish) {
        this.publish = publish;
    }

    /** {@code {sha256: [...]}} → {@code {missing: [...]}}: the files to send with the item. */
    @POST
    @Path("/blobs")
    public Map<String, List<String>> missing(MissingRequest request) {
        return Map.of("missing", publish.missing(request == null ? List.of() : request.sha256()));
    }

    @PUT
    @Path("/{key}")
    public FluxorJson.HarnessItemView publish(@Context ContainerRequestContext ctx, @PathParam("key") String key,
            PublishRequest request) {
        if (request == null || request.files() == null) {
            throw new FluxorException("invalid_harness_item", "A JSON body with 'files' is required", 422);
        }
        UUID accountId = (UUID) ctx.getProperty(FluxorDeviceAuthFilter.ACCOUNT_ID_PROPERTY);
        List<HarnessPublishService.PublishedFile> files = request.files().stream().map(FluxorSyncItemResource::file)
                .toList();
        var item = publish.publish(accountId, key, new HarnessPublishService.Publication(request.kind(),
                request.title(), request.description(), request.hook(), files, request.atom(), request.card()),
                new HarnessOwnItemService.Sharing(request.visibility(), request.harnessProjectId(),
                        request.organizationAccountId()));
        return FluxorJson.HarnessItemView.of(item, accountId);
    }

    private static HarnessPublishService.PublishedFile file(FileRequest f) {
        if (f == null) {
            throw new FluxorException("invalid_harness_item", "A file entry is empty", 422);
        }
        try {
            byte[] content = f.content() == null ? null : Base64.getDecoder().decode(f.content());
            return new HarnessPublishService.PublishedFile(f.path(), f.sha256(), f.size(), f.executable(), content);
        } catch (IllegalArgumentException ex) {
            throw new FluxorException("harness_blob_mismatch", f.path() + "'s content is not base64", 422);
        }
    }

    public record MissingRequest(List<String> sha256) {
    }

    public record PublishRequest(String kind, String title, String description, String visibility,
            UUID harnessProjectId, UUID organizationAccountId, Map<String, Object> hook, List<FileRequest> files,
            String atom, String card) {
    }

    /** {@code content} is the file's bytes in base64, only for a file the store lacks. */
    public record FileRequest(String path, String sha256, long size, boolean executable, String content) {
    }
}
