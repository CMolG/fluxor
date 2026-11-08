package com.javadaba.contexts.fluxor.domain;

/** Matches the {@code fluxor_task.source} check constraint -- provenance of the write, immutable
 *  once a task exists (an IDE sync PUT on a console-created task keeps {@code CONSOLE}). */
public enum TaskSource {
    API, CONSOLE, IDE;

    public String toDb() {
        return name().toLowerCase();
    }

    public static TaskSource fromDb(String value) {
        return TaskSource.valueOf(value.toUpperCase());
    }
}
