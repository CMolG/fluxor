package com.javadaba.contexts.fluxor.domain;

import java.util.Arrays;
import java.util.Locale;

/**
 * Who sees an item a person wrote (card://JAVA-750, the owner's decision of 2026-11-03): its author
 * alone, the people of one harness project, the people of the owner's organization, or everyone.
 */
public enum HarnessVisibility {
    PRIVATE, PROJECT, ORGANIZATION, PUBLIC;

    public String wire() {
        return name().toLowerCase(Locale.ROOT);
    }

    /** Null for an unknown value, so the caller answers it as a 422 of its own. */
    public static HarnessVisibility fromWire(String value) {
        return Arrays.stream(values()).filter(v -> v.wire().equals(value)).findFirst().orElse(null);
    }
}
