package com.javadaba.apps.api.fluxor;

import com.fasterxml.jackson.databind.JsonNode;
import com.javadaba.contexts.fluxor.application.FluxorJson;
import com.javadaba.contexts.fluxor.application.HarnessOwnItemService;
import com.javadaba.contexts.fluxor.application.HarnessPublishService;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.platform.mcp.McpOperation;
import com.javadaba.platform.mcp.McpParams;
import com.javadaba.platform.mcp.McpSchemas;
import com.javadaba.platform.shared.JsonSchema;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.SequencedMap;
import java.util.UUID;

/**
 * The items a person writes, written by their agent over MCP (card://JAVA-2123): a directive created
 * or edited as its next version, who sees an item, and a skill, hook, files item or directive
 * published whole, as {@code fluxor-sync item publish} does. Each is the REST write's service, so only
 * the author changes an item and every project following it moves to the new version.
 */
final class FluxorMcpItemWrites {

    private static final String OWN_KEY = "An own item's key, <namespace>.<name> like javadaba.code-review.";

    private FluxorMcpItemWrites() {
    }

    static List<McpOperation<UUID>> operations(HarnessOwnItemService items, HarnessPublishService publish) {
        return List.of(createDirective(items), versionDirective(items), share(items), publish(publish));
    }

    private static SequencedMap<String, Object> directiveFields() {
        return JsonSchema.ordered(
                "title", JsonSchema.ordered("type", "string"),
                "description", JsonSchema.ordered("type", "string", "description",
                        "What it does, as an agent reads it to explain what a project installs."),
                "body", JsonSchema.ordered("type", "string", "description", "The directive's Markdown."),
                "activation", JsonSchema.ordered("type", "string", "enum", List.of("always", "on-demand")),
                "exclusiveGroup", JsonSchema.ordered("type", "string", "description",
                        "role for a role: a project carries one item of a group."));
    }

    private static SequencedMap<String, Object> sharingFields(Map<String, Object> base) {
        SequencedMap<String, Object> fields = new LinkedHashMap<>(base);
        fields.put("visibility", JsonSchema.ordered("type", "string", "enum",
                List.of("private", "project", "organization", "public"),
                "description", "Who sees it; required for a new item."));
        fields.put("harnessProjectId", JsonSchema.ordered("type", "string",
                "description", "With visibility project: the harness project."));
        fields.put("organizationAccountId", JsonSchema.ordered("type", "string",
                "description", "With visibility organization: which one; yours when left out."));
        return fields;
    }

    private static McpOperation<UUID> createDirective(HarnessOwnItemService items) {
        SequencedMap<String, Object> fields = new LinkedHashMap<>(JsonSchema.ordered("key",
                JsonSchema.ordered("type", "string", "description", OWN_KEY)));
        fields.putAll(directiveFields());
        return new McpOperation<>("harness.directive.create",
                "Writes a new directive of yours (a rule; a role with exclusiveGroup role) at version 1. "
                        + "Put it on a project with harness.project.update.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(sharingFields(fields), List.of("key", "title", "body", "visibility")),
                JsonSchema.ordered("key", "javadaba.code-review", "title", "Code review", "body",
                        "# Code review\n\nEvery finding names a file and a line.\n", "visibility", "private"),
                (owner, params) -> FluxorJson.HarnessItemView.of(items.createDirective(owner,
                        params.get("key").asText(), directive(params), sharing(params)), owner));
    }

    private static McpOperation<UUID> versionDirective(HarnessOwnItemService items) {
        SequencedMap<String, Object> fields = new LinkedHashMap<>(JsonSchema.ordered("key",
                JsonSchema.ordered("type", "string", "description", OWN_KEY)));
        fields.putAll(directiveFields());
        return new McpOperation<>("harness.directive.version",
                "Saves your edit of a directive you wrote as its next version, whole (title and body are "
                        + "not merged with the last one). Every project that follows it moves to it.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(fields, List.of("key", "title", "body")),
                JsonSchema.ordered("key", "javadaba.code-review", "title", "Code review", "body",
                        "# Code review\n\nEvery finding names a file, a line and the rule it breaks.\n"),
                (owner, params) -> FluxorJson.HarnessItemView.of(items.newVersion(owner,
                        params.get("key").asText(), directive(params)), owner));
    }

    private static McpOperation<UUID> share(HarnessOwnItemService items) {
        SequencedMap<String, Object> fields = sharingFields(JsonSchema.ordered("key",
                JsonSchema.ordered("type", "string", "description", OWN_KEY)));
        fields.put("retired", JsonSchema.ordered("type", "boolean", "description",
                "True hides it from projects that do not carry it yet; false brings it back."));
        return new McpOperation<>("harness.item.share",
                "Changes who sees an item you wrote, or retires it or brings it back. Leave visibility out "
                        + "to only retire.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE, McpSchemas.schema(fields, List.of("key")),
                JsonSchema.ordered("key", "javadaba.code-review", "visibility", "organization"),
                (owner, params) -> FluxorJson.HarnessItemView.of(items.share(owner, params.get("key").asText(),
                        params.hasNonNull("visibility") ? sharing(params) : null,
                        McpParams.bool(params, "retired", null)), owner));
    }

    private static McpOperation<UUID> publish(HarnessPublishService publish) {
        Map<String, Object> file = McpSchemas.objectOf(JsonSchema.ordered(
                "path", JsonSchema.ordered("type", "string", "description",
                        "Inside the item (SKILL.md, scripts/x.py; a hook's fallback.md, hook.sh, hook.ps1); "
                                + "a files item's under .harness/ or .claude/rules/."),
                "text", JsonSchema.ordered("type", "string", "description", "Its content, UTF-8."),
                "base64", JsonSchema.ordered("type", "string", "description", "Its bytes, for a binary file."),
                "sha256", JsonSchema.ordered("type", "string", "description",
                        "Instead of content: a file harness.item already lists, kept as it is."),
                "size", JsonSchema.ordered("type", "integer", "description", "With sha256: its size."),
                "executable", JsonSchema.ordered("type", "boolean")), List.of("path"));
        SequencedMap<String, Object> fields = JsonSchema.ordered(
                "key", JsonSchema.ordered("type", "string", "description", OWN_KEY),
                "kind", JsonSchema.ordered("type", "string", "enum", List.of("skill", "hook", "files", "directive")),
                "title", JsonSchema.ordered("type", "string"),
                "description", JsonSchema.ordered("type", "string"),
                "files", McpSchemas.array(file),
                "hook", JsonSchema.ordered("type", "object", "description",
                        "A hook's manifest: event (sessionStart, promptSubmit, preTool, postTool, "
                                + "postToolFailure, stop, notification, statusLine), tools, timeoutMs."),
                "atom", JsonSchema.ordered("type", "string", "enum", List.of("role", "mod", "step", "flow")),
                "card", JsonSchema.ordered("type", "string", "description", "An atom's inventory card."));
        return new McpOperation<>("harness.item.publish",
                "Publishes an item of yours whole, as fluxor-sync item publish does: a new one at version 1, "
                        + "or your next version of it, which the projects following it move to. Every file "
                        + "goes each time; one you did not change goes as its sha256 and size.",
                McpOperation.WRITE, FluxorMcpResource.SCOPE_WRITE,
                McpSchemas.schema(sharingFields(fields), List.of("key", "kind", "files")),
                JsonSchema.ordered("key", "javadaba.contract", "kind", "skill", "title", "Contract", "files",
                        List.of(Map.of("path", "SKILL.md", "text", "---\nname: contract\n---\n# Contract\n")),
                        "visibility", "private"),
                (owner, params) -> FluxorJson.HarnessItemView.of(publish.publish(owner, params.get("key").asText(),
                        new HarnessPublishService.Publication(params.get("kind").asText(),
                                McpParams.string(params, "title", null), McpParams.string(params, "description", null),
                                params.hasNonNull("hook") ? FluxorMcpHarnessWrites.map(params.get("hook")) : null,
                                FluxorMcpHarnessWrites.objects(params.get("files")).stream()
                                        .map(FluxorMcpItemWrites::file).toList(),
                                McpParams.string(params, "atom", null), McpParams.string(params, "card", null)),
                        sharing(params)), owner));
    }

    /** A file with its content (text or base64), or named by the sha256 of one the store keeps. */
    private static HarnessPublishService.PublishedFile file(JsonNode f) {
        String path = f.get("path").asText();
        boolean executable = McpParams.bool(f, "executable", false);
        if (f.hasNonNull("text")) {
            return HarnessPublishService.PublishedFile.of(path, executable,
                    f.get("text").asText().getBytes(StandardCharsets.UTF_8));
        }
        if (f.hasNonNull("base64")) {
            try {
                return HarnessPublishService.PublishedFile.of(path, executable,
                        Base64.getDecoder().decode(f.get("base64").asText()));
            } catch (IllegalArgumentException ex) {
                throw new FluxorException("harness_blob_mismatch", path + "'s base64 does not decode", 422);
            }
        }
        if (!f.hasNonNull("sha256") || !f.hasNonNull("size")) {
            throw new FluxorException("invalid_harness_item",
                    path + " needs its text, its base64, or the sha256 and size of a file already published", 422);
        }
        return new HarnessPublishService.PublishedFile(path, f.get("sha256").asText(), f.get("size").asLong(),
                executable, null);
    }

    private static HarnessOwnItemService.Directive directive(JsonNode params) {
        return new HarnessOwnItemService.Directive(McpParams.string(params, "title", null),
                McpParams.string(params, "description", null), McpParams.string(params, "body", null),
                McpParams.string(params, "activation", null), McpParams.string(params, "exclusiveGroup", null));
    }

    private static HarnessOwnItemService.Sharing sharing(JsonNode params) {
        return new HarnessOwnItemService.Sharing(McpParams.string(params, "visibility", null),
                McpParams.optionalUuid(params, "harnessProjectId"),
                McpParams.optionalUuid(params, "organizationAccountId"));
    }
}
