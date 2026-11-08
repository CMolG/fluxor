package com.javadaba.contexts.fluxor.domain;

import java.util.List;

/**
 * Domain-level business error across the Fluxor bridge (backlog/flows/runs) -- same pattern as
 * {@code SocialException}: {@code code}/{@code httpStatus} set explicitly at each throw site,
 * serving BOTH inbound adapters that need the exact same mapping: {@code FluxorExceptionMapper}
 * (fluxor-infrastructure/apps-api JAX-RS {@code @Provider}s) and {@code FluxorTaskIntakeAction}
 * (apps-api, translates into {@code ActionValidationException} for the metered gateway's {@code
 * POST /v1/fluxor-task-intake}). {@code problems} says, in words, why a flow does not compile
 * ({@code flow_not_compilable}); empty for every other error.
 */
public class FluxorException extends RuntimeException {

    private final String code;
    private final int httpStatus;
    private final List<String> problems;

    public FluxorException(String code, String message, int httpStatus) {
        this(code, message, httpStatus, List.of());
    }

    public FluxorException(String code, String message, int httpStatus, List<String> problems) {
        super(message);
        this.code = code;
        this.httpStatus = httpStatus;
        this.problems = List.copyOf(problems);
    }

    public String code() {
        return code;
    }

    public int httpStatus() {
        return httpStatus;
    }

    public List<String> problems() {
        return problems;
    }
}
