package com.javadaba.contexts.fluxor.domain;

import java.util.Locale;

/**
 * What an account may do with a harness project (card://JAVA-2006). Its owner holds it; the people of
 * the Officium project it is linked to read it, and that project's owners and editors also change it.
 * Ordered from most to least capable.
 */
public enum HarnessAccess {
    OWNER, EDITOR, VIEWER;

    /** Whether the account may change the project's items: everyone but a viewer. */
    public boolean canEdit() {
        return this != VIEWER;
    }

    /** The lower-case name the API answers ({@code owner}, {@code editor}, {@code viewer}). */
    public String wire() {
        return name().toLowerCase(Locale.ROOT);
    }
}
