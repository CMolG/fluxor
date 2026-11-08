package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** What a preset adds (JAVA-161), market or saved (card://JAVA-2008): its listed items as changes. */
final class PresetItems {

    private PresetItems() {
    }

    @SuppressWarnings("unchecked")
    static List<HarnessService.ItemChange> of(HarnessItem preset) {
        if (!(preset.spec().get("items") instanceof List<?> listed)) {
            throw new IllegalStateException("Preset " + preset.key() + " has no items list");
        }
        List<HarnessService.ItemChange> changes = new ArrayList<>();
        for (Object entry : listed) {
            if (!(entry instanceof Map<?, ?> map) || !(map.get("key") instanceof String key)) {
                throw new IllegalStateException("Preset " + preset.key() + " lists an item with no key: " + entry);
            }
            Integer version = map.get("version") instanceof Number n ? n.intValue() : null;
            Map<String, Object> params = map.get("params") instanceof Map<?, ?> p ? (Map<String, Object>) p : null;
            changes.add(new HarnessService.ItemChange(key, version, params));
        }
        return changes;
    }
}
