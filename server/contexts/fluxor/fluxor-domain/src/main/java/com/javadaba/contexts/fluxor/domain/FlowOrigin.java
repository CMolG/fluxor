package com.javadaba.contexts.fluxor.domain;

/** Matches the {@code fluxor_flow.origin} check constraint. */
public enum FlowOrigin {
    IDE, CONSOLE, DESIGNER;

    public String toDb() {
        return name().toLowerCase();
    }

    public static FlowOrigin fromDb(String value) {
        return FlowOrigin.valueOf(value.toUpperCase());
    }
}
