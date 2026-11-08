package com.javadaba.platform.action;

/**
 * Invocation identity forwarded into {@link ActionContext#attributes()} under the reserved key
 * {@link #ATTRIBUTE_KEY}. Added for {@code notify.dispatch@1}
 * (doc://history/plans/programa/2026-07-09-notify-notificador-de-eventos, Task 6): it is the
 * first Action that needs to know
 * WHICH org invoked it (to look up that org's own notification providers), not just the request
 * body -- every prior Action (seo.package@1, ocr.extract@1, ...) happened not to need it.
 *
 * <p>Before this, {@code ProductInvocationService.PipelineActionContext#attributes()} only
 * exposed the pipeline's step-output bindings; the invocation's {@code organizationId}/{@code
 * apiKeyId} (already present on {@code InvocationContext}, computed by {@code
 * ProductInvocationResource}) were silently dropped before reaching {@code Action#execute}. This
 * closes that gap generically -- any future Action can read it the same way:
 *
 * <pre>{@code
 * InvocationIdentity identity = (InvocationIdentity) ctx.attributes().get(InvocationIdentity.ATTRIBUTE_KEY);
 * }</pre>
 *
 * <p>{@code organizationId}/{@code apiKeyId} are null for {@link
 * com.javadaba.platform.product.InvocationContext#anonymous()}.
 */
public record InvocationIdentity(String invocationId, String organizationId, String apiKeyId) {
    public static final String ATTRIBUTE_KEY = "_invocation";
}
