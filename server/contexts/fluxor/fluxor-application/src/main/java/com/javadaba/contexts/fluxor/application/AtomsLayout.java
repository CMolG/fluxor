package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

/**
 * The layout the market's {@code atoms} skill reads (card://JAVA-2009): a project that carries it gets
 * its roles, mods, steps and flows the way {@code marketplace.py install} writes them, under
 * {@code .harness/market/<kind>s/<id>.md}, with the engine ({@code motor.py}, {@code lexicon.json}) and
 * {@code inventory.json}, the projection of what the project carries. Those atoms then stay out of
 * {@code AGENTS.md}: the prompt hook mounts one role and its mods per batch, so none is always read.
 *
 * <p>Byte parity with the market's install is the contract: each item's body is written verbatim
 * (never rendered), and the inventory is assembled from the cards the seed stores already rendered by
 * Python ({@code spec.card}), so this file only nests them as {@code json.dumps(indent=2)} would.
 */
final class AtomsLayout {

    /** The skill whose presence switches the layout on. */
    static final String SKILL = "atoms";
    /** The catalog item that carries the engine's files (seeded from {@code market/engine.json}). */
    static final String ENGINE = "atoms-engine";
    private static final String MARKET = ".harness/market/";
    /** Each atom's folder, in the order {@code inventory.json} lists them. */
    private static final Map<String, String> FOLDERS = folders();

    private AtomsLayout() {
    }

    private static Map<String, String> folders() {
        Map<String, String> folders = new LinkedHashMap<>();
        folders.put("flow", "flows");
        folders.put("role", "roles");
        folders.put("mod", "mods");
        folders.put("step", "steps");
        return folders;
    }

    /** Whether the project carries the {@code atoms} skill, which switches the layout on. */
    static boolean wanted(List<HarnessService.Entry> entries) {
        return entries.stream().anyMatch(e -> SKILL.equals(e.catalog().key()));
    }

    /** An item this layout writes in place of the usual directive or skill paths. */
    static boolean handles(HarnessItem item) {
        return item.spec().get("atom") instanceof String atom && FOLDERS.containsKey(atom);
    }

    private static final java.util.regex.Pattern NAME = java.util.regex.Pattern.compile(
            "\\A\\{\\s*\"name\":\\s*\"([a-z0-9][a-z0-9-]{0,63})\"");

    /** The card's {@code name}, its first key as Python renders it; a plain file name, else the key. */
    static String cardName(String card, String key) {
        java.util.regex.Matcher matcher = NAME.matcher(card);
        return matcher.find() ? matcher.group(1) : key;
    }

    /** The atoms' files, the engine's (blob references) and the inventory of what the project carries. */
    static List<HarnessSnapshotService.SnapshotFile> files(List<HarnessService.Entry> entries,
            Optional<HarnessItem> engine) {
        List<HarnessSnapshotService.SnapshotFile> files = new ArrayList<>();
        Map<String, TreeMap<String, String>> cards = new LinkedHashMap<>();
        FOLDERS.values().forEach(folder -> cards.put(folder, new TreeMap<>()));
        for (HarnessService.Entry entry : entries) {
            HarnessItem item = entry.catalog();
            if (!handles(item)) {
                continue;
            }
            String folder = FOLDERS.get((String) item.spec().get("atom"));
            if (!(item.spec().get("card") instanceof String card)) {
                throw new IllegalStateException("Atom " + item.key() + " has no inventory card: seed it again");
            }
            // A market atom's card is named by its key; a person's own (JAVA-2011) by the card, which the
            // engine reads its file by, so a local mod lands where `marketplace.py install` puts it.
            String name = cardName(card, item.key());
            files.add(HarnessSnapshotService.generated(MARKET + folder + "/" + name + ".md", item.body(),
                    item.key(), HarnessSnapshotService.Mode.FILE));
            cards.get(folder).put(name, card);
            files.addAll(blobFiles(item, "marketFiles", MARKET + folder + "/"));
        }
        engine.ifPresent(e -> files.addAll(blobFiles(e, "files", MARKET)));
        files.add(HarnessSnapshotService.generated(MARKET + "inventory.json", inventory(cards), null,
                HarnessSnapshotService.Mode.FILE));
        return files;
    }

    /**
     * The files an item lists under {@code key} (the engine's {@code files}, an atom's companion
     * {@code marketFiles}), served from the blob store by sha256 like a skill's, each a plain file name
     * placed in {@code dir}.
     */
    private static List<HarnessSnapshotService.SnapshotFile> blobFiles(HarnessItem item, String key, String dir) {
        List<HarnessSnapshotService.SnapshotFile> files = new ArrayList<>();
        if (item.spec().get(key) instanceof List<?> listed) {
            for (Object entry : listed) {
                if (!(entry instanceof Map<?, ?> file) || !(file.get("path") instanceof String path)
                        || !path.matches("[A-Za-z0-9._-]+") || !(file.get("sha256") instanceof String sha256)
                        || !(file.get("size") instanceof Number size)) {
                    throw new IllegalStateException(item.key() + " lists a malformed file: " + entry);
                }
                files.add(new HarnessSnapshotService.SnapshotFile(dir + path, sha256, size.longValue(),
                        Boolean.TRUE.equals(file.get("executable")), item.key(),
                        HarnessSnapshotService.Mode.FILE.wire, null));
            }
        }
        return files;
    }

    /**
     * {@code json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"}: each list's cards, sorted by
     * name, nested two levels deep, so every line of a card gains four spaces.
     */
    static String inventory(Map<String, TreeMap<String, String>> cards) {
        List<String> lists = new ArrayList<>();
        cards.forEach((folder, byName) -> {
            if (byName.isEmpty()) {
                lists.add("  \"" + folder + "\": []");
                return;
            }
            List<String> nested = byName.values().stream().map(card -> card.indent(4).stripTrailing()).toList();
            lists.add("  \"" + folder + "\": [\n" + String.join(",\n", nested) + "\n  ]");
        });
        return "{\n" + String.join(",\n", lists) + "\n}\n";
    }
}
