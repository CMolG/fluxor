package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.javadaba.contexts.fluxor.domain.Pack;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The files a CEET pack (card://JAVA-286) adds to a snapshot: its shared files under
 * {@code .harness/packs/<pack-id>/}, and the manifests of the hooks its Claude Code adapter asks for.
 * Split from {@link HarnessSnapshotService} (card://JAVA-2006) so the snapshot's own layout has room.
 */
final class PackSnapshotFiles {

    private PackSnapshotFiles() {
    }

    /** Where a delivered pack lives: the default of ceet-core's pack contract. */
    static final String PACKS = ".harness/packs/";
    /** The adapter file a pack declares its Claude Code hooks in ({@code render_pack.py}). */
    static final String PACK_HOOKS_FILE = "adapters/claude-code/settings.hooks.json";
    /**
     * The pack hooks Fluxor knows how to run. A pack's own {@code settings.hooks.json} only says which
     * of these it wants: the writer builds the command from the manifest, never from the pack.
     */
    static final List<PackHook> PACK_HOOKS = List.of(
            new PackHook("ceet-check", "preTool", "PreToolUse", "shell", "bin/ceet_check.py", "claude-code",
                    "The pack's checks",
                    "Blocks a git commit whose added lines fail the checks the person stated (hooks/checks.json)"),
            new PackHook("examples", "promptSubmit", "UserPromptSubmit", null, "bin/examples.py", "inject",
                    "The pack's decisions",
                    "Adds the person's closest past decisions (examples/decisions.json) to each prompt"));

    /**
     * A pack's shared files, inline (they are the person's, never the shared blob store's), plus one
     * manifest per hook its Claude Code adapter asks for. The manifest names the sha256 of the script
     * the hook runs, so a changed script changes the hash the user consents to. Nothing of a pack is
     * written outside its folder, so no file a project commits names it.
     */
    static List<HarnessSnapshotService.SnapshotFile> of(Pack pack) {
        String dir = PACKS + pack.packId() + "/";
        List<HarnessSnapshotService.SnapshotFile> files = new ArrayList<>();
        Map<String, Pack.File> byPath = new HashMap<>();
        for (Pack.File file : pack.files()) {
            files.add(HarnessSnapshotService.generated(dir + file.path(), file.content(), pack.packId(),
                    HarnessSnapshotService.Mode.FILE));
            byPath.put(file.path(), file);
        }
        Pack.File wanted = byPath.get(PACK_HOOKS_FILE);
        for (PackHook hook : PACK_HOOKS) {
            Pack.File script = byPath.get(hook.script());
            if (script == null || wanted == null || !hook.wantedBy(wanted.content())) {
                continue;
            }
            Map<String, Object> manifest = new TreeMap<>();
            manifest.put("key", hook.key());
            manifest.put("pack", pack.packId());
            manifest.put("title", hook.title());
            manifest.put("description", hook.description());
            manifest.put("event", hook.event());
            if (hook.tools() != null) {
                manifest.put("tools", hook.tools());
            }
            manifest.put("run", Map.of("script", hook.script(), "args", List.of(hook.mode())));
            manifest.put("runs", List.of(Map.of("path", script.path(), "sha256", script.sha256())));
            try {
                files.add(HarnessSnapshotService.generated(dir + ".fluxor/hooks/" + hook.key() + ".json",
                        HarnessSnapshotService.MANIFEST_JSON.writeValueAsString(manifest) + "\n", pack.packId(),
                        HarnessSnapshotService.Mode.HOOK));
            } catch (JsonProcessingException ex) {
                throw new IllegalStateException("Pack hook " + hook.key() + " is not JSON", ex);
            }
        }
        return files;
    }

    /**
     * A hook a pack may ask for: {@code claudeEvent} is where the pack's {@code settings.hooks.json}
     * puts it, and {@code script} and {@code mode} the command it names there.
     */
    record PackHook(String key, String event, String claudeEvent, String tools, String script, String mode,
            String title, String description) {

        /** True when the pack's adapter declares this hook: its event lists a command running the script so. */
        boolean wantedBy(String settingsHooks) {
            try {
                for (JsonNode entry : HarnessSnapshotService.MANIFEST_JSON.readTree(settingsHooks).path("hooks")
                        .path(claudeEvent)) {
                    for (JsonNode handler : entry.path("hooks")) {
                        if (handler.path("command").asText("").contains(script + " " + mode)) {
                            return true;
                        }
                    }
                }
            } catch (JsonProcessingException ex) {
                return false; // an adapter file that is not JSON asks for nothing
            }
            return false;
        }
    }
}
