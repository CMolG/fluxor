package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
import com.javadaba.contexts.fluxor.domain.ports.PackRepository;
import jakarta.enterprise.context.ApplicationScoped;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A project's harness at its revision, as the files a paired writer puts on disk (JAVA-555, ADR
 * 0019). The layout is the spike's decision 4: directives at {@code .harness/rules/<key>.md}, skills
 * under {@code .harness/skills/<key>/}, a hook's {@code fallback} as a directive plus its scripts and
 * manifest under {@code .harness/hooks/} (the writer wires it only once the user consented to the
 * manifest's hash, JAVA-556), and each client's thin wiring. Skill files are references
 * to the blob store by sha256; everything this service generates carries its {@code content}
 * inline, with {@code {{NAME}}} replaced from the item's params and the built-in
 * {@value #OFFICIUM_PROJECT_ID}. A skill with params also gets its config file, the params as JSON
 * (card://JAVA-835). The writer itself is a file of every snapshot ({@link HarnessWriter}, JAVA-162),
 * so an installed one updates itself on its next pull.
 *
 * <p>The shape is {@code format: 1} of {@code doc://contracts/catalog-format}: installed
 * writers read it, so it only ever grows. The {@code hash} names the file set, so the same revision
 * always gives the same hash, and it is the snapshot's {@code ETag}.
 *
 * <p>A writer that asks for them ({@code include=packs}, card://JAVA-286) also gets the CEET packs its
 * owner published and attached to the project, under {@code .harness/packs/<pack-id>/}, with the
 * manifests of their hooks. A writer from before packs never asks: it would lock a pack's paths in the
 * committed {@code harness.lock.json}, and could not parse the {@code --print-packs} its session start
 * would then run.
 */
@ApplicationScoped
public class HarnessSnapshotService {

    public static final int FORMAT = 1;
    static final String BLOCK_BEGIN = "<!-- fluxor:begin -->";
    static final String BLOCK_END = "<!-- fluxor:end -->";
    /** Where the writer lives (JAVA-162), so each client's session start can run it. */
    public static final String WRITER = ".harness/bin/fluxor-sync.py";
    /**
     * What starts Python in Claude Code's session start (card://JAVA-834). It runs hooks in a POSIX
     * shell everywhere, Git Bash on Windows, where {@code python3} is often the Microsoft Store stub
     * (exit 49): try it, else {@code python}. The writer's {@code PYTHON} is the same line.
     */
    static final String PYTHON = "py=python3; \"$py\" -c '' </dev/null >/dev/null 2>&1 || py=python; \"$py\"";
    /** Where a skill's config file lives: the {@code config.file} of its market manifest. */
    public static final String CONFIG = ".harness/config/";
    /** The param every render knows: the Officium project the harness project is linked to (JAVA-161). */
    static final String OFFICIUM_PROJECT_ID = "OFFICIUM_PROJECT_ID";
    private static final Pattern PARAM = Pattern.compile("\\{\\{([A-Za-z0-9_]+)\\}\\}");
    /** A hook's key names its files, and the writer puts their paths in a shell command. */
    private static final Pattern HOOK_KEY = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]*");
    /** Sorted keys, so the same hook always gives the same manifest bytes, and so the same hash. */
    static final ObjectMapper MANIFEST_JSON = new ObjectMapper()
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
    /** A config file is the project's to read and edit, so it is indented; keys sorted as above. */
    private static final ObjectMapper CONFIG_JSON = MANIFEST_JSON.copy()
            .configure(SerializationFeature.INDENT_OUTPUT, true);

    private final HarnessService harness;
    private final HarnessRepository repository;
    private final HarnessWriter writer;
    private final PackRepository packs;

    public HarnessSnapshotService(HarnessService harness, HarnessRepository repository, HarnessWriter writer,
            PackRepository packs) {
        this.harness = harness;
        this.repository = repository;
        this.writer = writer;
        this.packs = packs;
    }

    public List<HarnessService.SharedProject> projects(UUID accountId) {
        return harness.projects(accountId);
    }

    /** 404 for a project another account owns, exactly as for one that does not exist. */
    public Snapshot snapshot(UUID accountId, UUID projectId) {
        return snapshot(accountId, projectId, false);
    }

    /** The snapshot, with the project's packs when the writer asks for them ({@code includePacks}). */
    public Snapshot snapshot(UUID accountId, UUID projectId, boolean includePacks) {
        HarnessService.ProjectHarness project = harness.project(accountId, projectId);
        UUID board = project.project().officiumProjectId();
        List<SnapshotFile> files = new ArrayList<>();
        List<String> always = new ArrayList<>();
        List<String> onDemand = new ArrayList<>();
        List<String> skills = new ArrayList<>();
        // card://JAVA-2009: with the atoms skill, roles, mods, steps and flows take the market's layout.
        boolean atoms = AtomsLayout.wanted(project.items());
        for (HarnessService.Entry entry : project.items()) {
            HarnessItem item = entry.catalog();
            Map<String, Object> params = withBuiltins(entry.item().params(), board);
            if (atoms && AtomsLayout.handles(item)) {
                continue;
            }
            switch (item.kind()) {
                case DIRECTIVE, HOOK -> {
                    String path = ".harness/rules/" + item.key() + ".md";
                    boolean hook = item.kind() == HarnessItemKind.HOOK;
                    String text = hook ? (String) item.spec().get("fallback") : item.body();
                    files.add(generated(path, render(text, params), item.key(), Mode.FILE));
                    if (hook) {
                        files.addAll(hookFiles(item, params, path));
                    }
                    // A hook's fallback stands in for a hook, which always runs: it is always read.
                    // The writer leaves it out of the block on a machine that wired the hook (JAVA-556).
                    if (hook || "always".equals(item.spec().get("activation"))) {
                        always.add("@" + path);
                    } else {
                        onDemand.add("- `" + path + "`: " + item.title());
                    }
                }
                case SKILL -> {
                    files.addAll(skillFiles(item, params));
                    if (!entry.item().params().isEmpty()) {
                        files.add(configFile(item, entry.item().params(), params));
                    }
                    skills.add("- `.harness/skills/" + item.key() + "/`: " + item.title());
                }
                case FILES -> files.addAll(OwnFiles.of(item));
                case PRESET -> throw new IllegalStateException("A preset is never a project item: " + item.key());
            }
        }
        if (atoms) {
            files.addAll(AtomsLayout.files(project.items(), repository.findItem(AtomsLayout.ENGINE, null)));
        }
        files.add(generated("AGENTS.md", agentsBlock(always, onDemand, skills), null, Mode.BLOCK));
        files.add(generated("CLAUDE.md", "@AGENTS.md\n", null, Mode.FILE));
        // Claude Code expands AGENTS.md's imports itself, so its session start prints only the packs' cores.
        files.add(generated(".claude/settings.json", sessionStart(withMachineWriter("\"$CLAUDE_PROJECT_DIR/" + WRITER
                + "\"", PYTHON, "pull" + (includePacks ? " --print-packs" : "")), null), null, Mode.JSON_MERGE));
        // Codex has a Windows override instead, the one the writer gives a hook with a PowerShell script.
        String codexPull = WRITER + " pull --print-directives";
        files.add(generated(".codex/hooks.json", sessionStart(withMachineWriter(WRITER, "python3",
                "pull --print-directives"), "python " + codexPull), null, Mode.JSON_MERGE));
        files.add(new SnapshotFile(WRITER, writer.sha256(), writer.size(), true, null, Mode.FILE.wire, writer.text()));
        if (includePacks) {
            // A pack is its person's (card://JAVA-286): a reader of a shared project gets only their own.
            packs.findAttached(projectId).stream().filter(pack -> pack.accountId().equals(accountId))
                    .forEach(pack -> files.addAll(PackSnapshotFiles.of(pack)));
        }
        OwnFiles.requireDistinctPaths(files);
        files.sort(Comparator.comparing(SnapshotFile::path));
        HarnessProject meta = project.project();
        return new Snapshot(FORMAT, meta.id(), meta.revision(), hash(files), List.copyOf(files));
    }

    /** A blob only some catalog item lists: the store serves catalog files, nothing else. */
    public byte[] blob(UUID accountId, String sha256) {
        if (sha256 == null || !sha256.matches("[0-9a-f]{64}")) {
            throw blobNotFound(sha256);
        }
        // card://JAVA-2007: a file only an own item lists goes to an account that can see that item.
        List<HarnessItem> listers = repository.findItemsListing(sha256);
        if (listers.stream().allMatch(HarnessItem::own)
                && listers.stream().noneMatch(harness.audience(accountId)::canSee)) {
            throw blobNotFound(sha256);
        }
        return repository.findBlob(sha256).orElseThrow(() -> blobNotFound(sha256));
    }

    /** sha256 over the sorted {@code path<TAB>sha256<TAB>executable} lines, each ending in a newline. */
    static String hash(List<SnapshotFile> files) {
        StringBuilder lines = new StringBuilder();
        files.stream().sorted(Comparator.comparing(SnapshotFile::path)).forEach(f -> lines.append(f.path())
                .append('\t').append(f.sha256()).append('\t').append(f.executable()).append('\n'));
        return DeviceTokens.sha256Hex(lines.toString());
    }

    /** {@code {{NAME}}} becomes the param's value; a placeholder with no param is left as written. */
    static String render(String text, Map<String, Object> params) {
        Matcher matcher = PARAM.matcher(text == null ? "" : text);
        StringBuilder out = new StringBuilder();
        while (matcher.find()) {
            Object value = params.get(matcher.group(1));
            matcher.appendReplacement(out,
                    Matcher.quoteReplacement(value == null ? matcher.group() : String.valueOf(value)));
        }
        return matcher.appendTail(out).toString();
    }

    /** The item's params, plus {@value #OFFICIUM_PROJECT_ID} when the project is linked; the item's own win. */
    private static Map<String, Object> withBuiltins(Map<String, Object> params, UUID board) {
        if (board == null || params.containsKey(OFFICIUM_PROJECT_ID)) {
            return params;
        }
        Map<String, Object> all = new HashMap<>(params);
        all.put(OFFICIUM_PROJECT_ID, board.toString());
        return all;
    }

    /**
     * A skill's config file (card://JAVA-835): its params ARE the file, as sorted-key JSON, every string
     * rendered. The name is the {@code config.file} the seed copies from the market manifest; a row
     * seeded before it did falls back to {@code <key>.json}, which every market skill's config is
     * named. The {@code projectId} param the {@code officium} preset gave {@code backlog} before 1.1.0,
     * which a project set up then still carries, is the config's {@code project.id}.
     */
    private static SnapshotFile configFile(HarnessItem item, Map<String, Object> params, Map<String, Object> vars) {
        String name = item.spec().get("config") instanceof Map<?, ?> config && config.get("file") instanceof String file
                ? file
                : item.key() + ".json";
        if (!HOOK_KEY.matcher(name).matches() || name.contains("..")) {
            throw new IllegalStateException(
                    "Skill " + item.key() + " names a config file that is not a safe file name: "
                            + name);
        }
        Map<String, Object> content = new TreeMap<>(params);
        if (content.get("projectId") instanceof String id && !content.containsKey("project")) {
            content.remove("projectId");
            content.put("project", Map.of("id", id));
        }
        try {
            return generated(CONFIG + name, CONFIG_JSON.writeValueAsString(renderAll(content, vars)) + "\n",
                    item.key(), Mode.FILE);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Skill " + item.key() + " has params that are not JSON", ex);
        }
    }

    /** Every string inside {@code value}, at any depth, rendered. */
    private static Object renderAll(Object value, Map<String, Object> vars) {
        return switch (value) {
            case String text -> render(text, vars);
            case Map<?, ?> map -> {
                Map<String, Object> out = new TreeMap<>();
                map.forEach((k, v) -> out.put(String.valueOf(k), renderAll(v, vars)));
                yield out;
            }
            case List<?> list -> list.stream().map(v -> renderAll(v, vars)).toList();
            case null, default -> value;
        };
    }

    private static List<SnapshotFile> skillFiles(HarnessItem item, Map<String, Object> params) {
        String dir = ".harness/skills/" + item.key() + "/";
        if (!(item.spec().get("files") instanceof List<?> listed) || listed.isEmpty()) {
            // A step, or a skill seeded before the market listed its files: its SKILL.md is all of it.
            return List.of(generated(dir + "SKILL.md", render(item.body(), params), item.key(), Mode.FILE));
        }
        List<SnapshotFile> files = new ArrayList<>();
        for (Object entry : listed) {
            if (!(entry instanceof Map<?, ?> file) || !(file.get("path") instanceof String path)
                    || !(file.get("sha256") instanceof String sha256) || !(file.get("size") instanceof Number size)) {
                throw new IllegalStateException("Skill " + item.key() + " lists a malformed file: " + entry);
            }
            if (path.isEmpty() || path.startsWith("/") || path.contains("\\")
                    || List.of(path.split("/")).contains("..")) {
                throw new IllegalStateException("Skill " + item.key() + " lists a path outside its folder: " + path);
            }
            files.add(new SnapshotFile(dir + path, sha256, size.longValue(),
                    Boolean.TRUE.equals(file.get("executable")), item.key(), Mode.FILE.wire, null));
        }
        return files;
    }

    /**
     * A hook's scripts ({@code spec.sh}, {@code spec.ps1}, rendered with the item's params) under
     * {@code .harness/hooks/}, and its manifest: what the writer wires, and the bytes whose sha256 the
     * user consents to (JAVA-556, ADR 0020). The manifest names each script's sha256, so a changed
     * script or a changed wiring both change that hash. A hook with no script is only its fallback.
     */
    private static List<SnapshotFile> hookFiles(HarnessItem item, Map<String, Object> params, String fallback) {
        if (!HOOK_KEY.matcher(item.key()).matches()) {
            throw new IllegalStateException("Hook key is not a safe file name: " + item.key());
        }
        Map<String, Object> scripts = new TreeMap<>();
        List<SnapshotFile> files = new ArrayList<>();
        for (String kind : List.of("sh", "ps1")) {
            if (item.spec().get(kind) instanceof String text) {
                String path = ".harness/hooks/" + item.key() + "." + kind;
                SnapshotFile script = generated(path, render(text, params), item.key(), Mode.FILE, kind.equals("sh"));
                files.add(script);
                scripts.put(kind, Map.of("path", path, "sha256", script.sha256()));
            }
        }
        if (scripts.isEmpty()) {
            return files;
        }
        Map<String, Object> manifest = new TreeMap<>();
        manifest.put("key", item.key());
        manifest.put("title", item.title());
        manifest.put("description", item.description());
        manifest.put("fallback", fallback);
        manifest.put("scripts", scripts);
        for (String field : List.of("event", "tools", "notifications", "timeoutMs")) {
            if (item.spec().get(field) != null) {
                manifest.put(field, item.spec().get(field));
            }
        }
        try {
            files.add(generated(".harness/hooks/" + item.key() + ".json",
                    MANIFEST_JSON.writeValueAsString(manifest) + "\n", item.key(), Mode.HOOK, false));
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Hook " + item.key() + " has a spec that is not JSON", ex);
        }
        return files;
    }

    private static String agentsBlock(List<String> always, List<String> onDemand, List<String> skills) {
        StringBuilder block = new StringBuilder(BLOCK_BEGIN).append('\n')
                .append("<!-- Managed by Fluxor (fluxor-sync): this block is replaced on every pull. -->\n");
        section(block, "Rules", always);
        section(block, "Rules to read when the task calls for them", onDemand);
        section(block, "Skills", skills);
        return block.append(BLOCK_END).append('\n').toString();
    }

    private static void section(StringBuilder block, String title, List<String> lines) {
        if (!lines.isEmpty()) {
            block.append("\n## ").append(title).append("\n\n");
            lines.forEach(line -> block.append(line).append('\n'));
        }
    }

    /**
     * Runs the project's writer, else this machine's copy (card://JAVA-2010): a fresh clone or worktree
     * of an enrolled machine has no {@code .harness/} yet, and pulls it at its first session. With
     * neither, it says how to set the machine up instead of failing.
     */
    static String withMachineWriter(String projectWriter, String python, String args) {
        return "f=" + projectWriter + "; [ -f \"$f\" ] || f=\"$HOME/.config/fluxor/bin/fluxor-sync.py\"; "
                + "if [ -f \"$f\" ]; then " + python + " \"$f\" " + args
                + "; else echo \"fluxor-sync: this machine never "
                + "pulled this project's harness. Ask your agent to configure Officium.\"; fi";
    }

    private static String sessionStart(String command, String commandWindows) {
        String windows = commandWindows == null ? "" : ", \"commandWindows\": \"" + quoted(commandWindows) + "\"";
        return "{\n  \"hooks\": {\n    \"SessionStart\": [\n      {\n        \"hooks\": [\n"
                + "          { \"type\": \"command\", \"command\": \"" + quoted(command) + "\"" + windows + " }\n"
                + "        ]\n      }\n    ]\n  }\n}\n";
    }

    private static String quoted(String text) {
        return text.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    static SnapshotFile generated(String path, String content, String item, Mode mode) {
        return generated(path, content, item, mode, false);
    }

    private static SnapshotFile generated(String path, String content, String item, Mode mode, boolean executable) {
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        return new SnapshotFile(path, DeviceTokens.sha256Hex(bytes), bytes.length, executable, item, mode.wire,
                content);
    }

    private static FluxorException blobNotFound(String sha256) {
        return new FluxorException("harness_blob_not_found", "No catalog file has sha256 " + sha256, 404);
    }

    /**
     * How the writer applies a file: whole, as its managed block, merged into a JSON file, or whole
     * as a hook's manifest (which a writer before JAVA-556 writes as a plain file and wires nothing).
     */
    enum Mode {
        FILE("file"), BLOCK("block"), JSON_MERGE("json-merge"), HOOK("hook");

        final String wire;

        Mode(String wire) {
            this.wire = wire;
        }
    }

    public record Snapshot(int format, UUID projectId, long revision, String hash, List<SnapshotFile> files) {
    }

    /** {@code item} is null on wiring no single item owns; {@code content} only on generated files. */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record SnapshotFile(String path, String sha256, long size, boolean executable, String item, String mode,
            String content) {
    }
}
