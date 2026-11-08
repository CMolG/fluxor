package com.javadaba.contexts.fluxor.domain;

/** Matches the {@code fluxor_harness_item.kind} check constraint. A {@code PRESET} is a named bundle
 *  of the other three: it is applied to a project, never added to one as an item itself. */
public enum HarnessItemKind {
    /** {@code FILES} (card://JAVA-2007): a person's files, each written at its own path in the project. */
    DIRECTIVE, SKILL, HOOK, PRESET, FILES;

    public String toDb() {
        return name().toLowerCase();
    }

    public static HarnessItemKind fromDb(String value) {
        return HarnessItemKind.valueOf(value.toUpperCase());
    }
}
