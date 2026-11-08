package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * A person's {@code files} item in a snapshot (card://JAVA-2007): each file at its own path, under
 * {@code .harness/} or {@code .claude/rules/}, served from the blob store by sha256; and the rule that
 * two items never write the same path.
 */
final class OwnFiles {

    /** Where a files item may write: the harness, and Claude Code's copies of path-scoped rules. */
    static final List<String> ROOTS = List.of(".harness/", ".claude/rules/");
    /** The writer's own files, and the folders it owns, are never an item's. */
    private static final Set<String> RESERVED = Set.of(".harness/fluxor.json", ".harness/harness.lock.json",
            ".harness/agents.md");
    private static final List<String> RESERVED_FOLDERS = List.of(".harness/bin/", ".harness/packs/");
    /** A relative path of plain segments (dot files included): no absolute path, no backslash. */
    private static final Pattern SEGMENT = Pattern.compile("[A-Za-z0-9._@+-]+");

    private OwnFiles() {
    }

    /** A relative path made only of plain segments, so it can never leave the folder it is joined to. */
    static boolean safe(String path) {
        if (path == null || path.isEmpty() || path.length() > 512) {
            return false;
        }
        for (String segment : path.split("/", -1)) {
            if (!SEGMENT.matcher(segment).matches() || segment.equals(".") || segment.equals("..")) {
                return false;
            }
        }
        return true;
    }

    /** Whether a files item may write {@code path}. */
    static boolean placeable(String path) {
        return safe(path) && ROOTS.stream().anyMatch(path::startsWith) && !RESERVED.contains(path)
                && RESERVED_FOLDERS.stream().noneMatch(path::startsWith);
    }

    /** The item's files at their own paths, as blob references. */
    static List<HarnessSnapshotService.SnapshotFile> of(HarnessItem item) {
        List<HarnessSnapshotService.SnapshotFile> files = new ArrayList<>();
        if (item.spec().get("files") instanceof List<?> listed) {
            for (Object entry : listed) {
                if (!(entry instanceof Map<?, ?> file) || !(file.get("path") instanceof String path)
                        || !placeable(path) || !(file.get("sha256") instanceof String sha256)
                        || !(file.get("size") instanceof Number size)) {
                    throw new IllegalStateException(item.key() + " lists a file it may not write: " + entry);
                }
                files.add(new HarnessSnapshotService.SnapshotFile(path, sha256, size.longValue(),
                        Boolean.TRUE.equals(file.get("executable")), item.key(), HarnessSnapshotService.Mode.FILE.wire,
                        null));
            }
        }
        return files;
    }

    /** Two items writing one path would overwrite each other on every pull: the snapshot refuses it. */
    static void requireDistinctPaths(List<HarnessSnapshotService.SnapshotFile> files) {
        Map<String, String> owners = new HashMap<>();
        for (HarnessSnapshotService.SnapshotFile file : files) {
            String before = owners.putIfAbsent(file.path(), String.valueOf(file.item()));
            if (before != null) {
                throw new FluxorException("harness_path_conflict", file.path() + " is written by both " + before
                        + " and " + file.item() + ": remove one of them from the project", 409);
            }
        }
    }
}
