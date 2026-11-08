package com.javadaba.contexts.fluxor.domain;

/** Matches the {@code fluxor_run.status} check constraint. Once {@code PASSED}/{@code
 *  FAILED}/{@code CANCELLED}, immutable -- {@code RunMonitorService#close} is the only
 *  transition out of {@code RUNNING} (plan #19, Task 5 Step 4: "cierre fija status inmutable"). */
public enum RunStatus {
    RUNNING, PASSED, FAILED, CANCELLED;

    public String toDb() {
        return name().toLowerCase();
    }

    public static RunStatus fromDb(String value) {
        return RunStatus.valueOf(value.toUpperCase());
    }

    public boolean isTerminal() {
        return this != RUNNING;
    }
}
