package com.javadaba.contexts.fluxor.domain;

/** Matches the {@code fluxor_flow.status} check constraint -- {@code DRAFT} (console-authored,
 *  not yet materialized by the IDE) transitions to {@code SYNCED} the moment the IDE re-publishes
 *  it after pulling it (plan #19, Task 5 Step 2: "the draft dies there -- a single owner of the
 *  final state"). An IDE-originated flow is {@code SYNCED} from the moment it exists. */
public enum FlowStatus {
    DRAFT, SYNCED;

    public String toDb() {
        return name().toLowerCase();
    }

    public static FlowStatus fromDb(String value) {
        return FlowStatus.valueOf(value.toUpperCase());
    }
}
