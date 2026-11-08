package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.InterviewConsent;
import com.javadaba.contexts.fluxor.domain.Pack;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
import com.javadaba.contexts.fluxor.domain.ports.InterviewRepository;
import com.javadaba.contexts.fluxor.domain.ports.PackRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * A CEET pack published to Fluxor online and delivered to its owner's projects (card://JAVA-286).
 * The person renders the pack on their own machine ({@code render_pack.py}); Fluxor keeps exactly the
 * bytes {@code pack.json} hashed, after proving every hash, and never runs a model or Python on them.
 * Only the shared files travel: {@code private/} (the verbatim answers) is refused, never stored.
 */
@ApplicationScoped
public class PackService {

    public static final String MANIFEST = "pack.json";
    public static final String GITIGNORE = ".gitignore";
    static final int MAX_FILES = 400;
    static final int MAX_FILE_BYTES = 1_000_000;
    static final int MAX_PACK_BYTES = 4_000_000;
    /** {@code <role>-<person>} in kebab-case, as ceet-core's {@code common.schema.json} defines a pack id. */
    static final Pattern PACK_ID = Pattern.compile("[a-z0-9]+(-[a-z0-9]+)*");
    /** A path segment: the writer puts these paths on disk, so nothing a shell or a filesystem reads specially. */
    private static final Pattern SEGMENT = Pattern.compile("[A-Za-z0-9._-]+");
    private static final TypeReference<Map<String, Object>> JSON_OBJECT = new TypeReference<>() {
    };

    private final HarnessService harness;
    private final HarnessRepository catalog;
    private final InterviewRepository interviews;
    private final PackRepository packs;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Inject
    public PackService(HarnessService harness, HarnessRepository catalog, InterviewRepository interviews,
            PackRepository packs, ObjectMapper objectMapper) {
        this(harness, catalog, interviews, packs, objectMapper, Clock.systemUTC());
    }

    PackService(HarnessService harness, HarnessRepository catalog, InterviewRepository interviews, PackRepository packs,
            ObjectMapper objectMapper, Clock clock) {
        this.harness = harness;
        this.catalog = catalog;
        this.interviews = interviews;
        this.packs = packs;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    /**
     * Stores the pack under the account and attaches it to the project; publishing it again replaces
     * its files. {@code files} are paths relative to the pack folder with their text.
     */
    public Pack publish(UUID accountId, UUID projectId, String packId, List<Upload> files) {
        harness.project(accountId, projectId);
        if (packId == null || packId.length() > 100 || !PACK_ID.matcher(packId).matches()) {
            throw invalid("'" + packId + "' is not a pack id: <role>-<person> in kebab-case, up to 100 characters");
        }
        Map<String, String> uploaded = uploads(files);
        Map<String, Object> manifest = manifest(uploaded.get(MANIFEST));
        if (!packId.equals(manifest.get("packId"))) {
            throw invalid("pack.json names pack " + manifest.get("packId") + ", not " + packId);
        }
        if (!"interview".equals(manifest.get("source"))) {
            throw new FluxorException("pack_not_interview", "Only a pack from the person's own interview is "
                    + "published; a simulated pack carries a third party's data", 422);
        }
        String role = role(manifest, packId);
        if (!(manifest.get("consent") instanceof Map<?, ?> consent)
                || !InterviewConsent.STATEMENT_VERSION.equals(consent.get("statementVersion"))) {
            throw new FluxorException("pack_consent", "pack.json was made under another consent statement: Fluxor "
                    + "keeps a pack only under " + InterviewConsent.STATEMENT_VERSION, 422);
        }
        // Kept local, the pack ignores itself: without that file every synced copy could be committed.
        String ignore = uploaded.get(GITIGNORE);
        if ("local".equals(consent.get("storage"))
                && (ignore == null || !List.of(ignore.split("\\s+")).contains("*"))) {
            throw invalid("a pack kept local (consent storage: local) is published with its .gitignore, which "
                    + "ignores everything (*)");
        }
        if (interviews.findCurrentConsent(accountId, role).filter(InterviewConsent::admitsAnswers).isEmpty()) {
            throw new FluxorException("consent_required",
                    "This account has no current " + InterviewConsent.STATEMENT_VERSION
                            + " consent for " + role + " in Fluxor online",
                    409);
        }
        List<Pack.File> stored = files(manifest, uploaded);
        Pack pack = new Pack(UUID.randomUUID(), accountId, packId, role, string(manifest, "formVersion"),
                string(manifest, "profileVersion"), InterviewConsent.STATEMENT_VERSION, Instant.now(clock), stored);
        packs.publish(pack, projectId);
        return pack;
    }

    /** Detaches the pack from this project; it stays in Fluxor for the account's other projects. */
    public void detach(UUID accountId, UUID projectId, String packId) {
        harness.project(accountId, projectId);
        if (!packs.detach(accountId, packId, projectId)) {
            throw notFound(packId, "is not attached to this project");
        }
    }

    /** Deletes the pack from Fluxor: every project it was attached to drops it on its next pull. */
    public void unpublish(UUID accountId, String packId) {
        if (!packs.delete(accountId, packId)) {
            throw notFound(packId, "is not published by this account");
        }
    }

    /** The packs a project's snapshot delivers. */
    public List<Pack> attached(UUID projectId) {
        return packs.findAttached(projectId);
    }

    private static Map<String, String> uploads(List<Upload> files) {
        if (files == null || files.isEmpty()) {
            throw invalid("a pack is uploaded with its files");
        }
        if (files.size() > MAX_FILES) {
            throw invalid("a pack has at most " + MAX_FILES + " files");
        }
        Map<String, String> uploaded = new LinkedHashMap<>();
        long total = 0;
        for (Upload file : files) {
            String path = file == null ? null : file.path();
            if (path == null || !safe(path)) {
                throw invalid("'" + path + "' is not a path inside the pack");
            }
            if (path.startsWith("private/") || path.equals(".fluxor") || path.startsWith(".fluxor/")) {
                throw new FluxorException("pack_private_path", path + " is never published: private/ holds the "
                        + "person's verbatim answers, and .fluxor/ is the writer's", 422);
            }
            if (file.content() == null) {
                throw invalid(path + " has no content");
            }
            int bytes = file.content().getBytes(StandardCharsets.UTF_8).length;
            total += bytes;
            if (bytes > MAX_FILE_BYTES || total > MAX_PACK_BYTES) {
                throw new FluxorException("pack_too_large", "A pack file holds at most " + MAX_FILE_BYTES
                        + " bytes and a pack " + MAX_PACK_BYTES, 413);
            }
            if (uploaded.put(path, file.content()) != null) {
                throw invalid(path + " is uploaded twice");
            }
        }
        return uploaded;
    }

    private Map<String, Object> manifest(String text) {
        if (text == null) {
            throw invalid("the upload has no pack.json");
        }
        try {
            return objectMapper.readValue(text, JSON_OBJECT);
        } catch (IOException ex) {
            throw invalid("pack.json is not a JSON object");
        }
    }

    /** The meta-skill the pack came from, which must be one in the catalog and prefix the pack id. */
    private String role(Map<String, Object> manifest, String packId) {
        String metaSkill = manifest.get("metaSkill") instanceof String s ? s : "";
        String role = metaSkill.replaceFirst("@.*$", "");
        boolean meta = !role.isEmpty() && catalog.findItem(role, null)
                .filter(i -> i.kind() == HarnessItemKind.SKILL && "meta".equals(i.spec().get("packaging")))
                .isPresent();
        if (!meta) {
            throw new FluxorException("pack_unknown_role", "pack.json's metaSkill '" + metaSkill
                    + "' is not a meta-skill in Fluxor's catalog", 422);
        }
        if (!packId.startsWith(role.replaceFirst("^ceet-", "") + "-")) {
            throw invalid("a " + role + " pack id starts with " + role.replaceFirst("^ceet-", "") + "-");
        }
        return role;
    }

    /**
     * Every file pack.json lists, its hash proven, plus pack.json and the root .gitignore: exactly
     * those, so nothing pack.json does not account for is stored.
     */
    private static List<Pack.File> files(Map<String, Object> manifest, Map<String, String> uploaded) {
        if (!(manifest.get("files") instanceof List<?> listed) || listed.isEmpty()) {
            throw invalid("pack.json lists no files");
        }
        Set<String> expected = new HashSet<>(Set.of(MANIFEST));
        List<Pack.File> stored = new ArrayList<>();
        for (Object entry : listed) {
            if (!(entry instanceof Map<?, ?> file) || !(file.get("path") instanceof String path)
                    || !(file.get("sha256") instanceof String sha256)) {
                throw invalid("pack.json lists a malformed file: " + entry);
            }
            String content = uploaded.get(path);
            if (content == null) {
                throw invalid(path + " is listed in pack.json but was not uploaded");
            }
            if (!DeviceTokens.sha256Hex(content).equals(sha256)) {
                throw new FluxorException("pack_hash_mismatch", path + " does not match its sha256 in pack.json: "
                        + "re-render the pack (render_pack.py render --write) or publish it as rendered", 422);
            }
            expected.add(path);
        }
        if (uploaded.containsKey(GITIGNORE)) {
            expected.add(GITIGNORE);
        }
        for (Map.Entry<String, String> file : uploaded.entrySet()) {
            if (!expected.contains(file.getKey())) {
                throw invalid(file.getKey() + " is not listed in pack.json");
            }
            stored.add(new Pack.File(file.getKey(), DeviceTokens.sha256Hex(file.getValue()), file.getValue()));
        }
        stored.sort((a, b) -> a.path().compareTo(b.path()));
        return stored;
    }

    private static boolean safe(String path) {
        if (path.length() > 300) {
            return false;
        }
        for (String segment : path.split("/", -1)) {
            if (segment.equals(".") || segment.equals("..") || !SEGMENT.matcher(segment).matches()) {
                return false;
            }
        }
        return true;
    }

    private static String string(Map<String, Object> manifest, String field) {
        if (!(manifest.get(field) instanceof String value) || value.isBlank() || value.length() > 40) {
            throw invalid("pack.json has no " + field);
        }
        return value;
    }

    private static FluxorException invalid(String message) {
        return new FluxorException("invalid_pack", message, 422);
    }

    private static FluxorException notFound(String packId, String why) {
        return new FluxorException("pack_not_found", "Pack " + packId + " " + why, 404);
    }

    /** One file of an upload: its path relative to the pack folder, and its text. */
    public record Upload(String path, String content) {
    }
}
