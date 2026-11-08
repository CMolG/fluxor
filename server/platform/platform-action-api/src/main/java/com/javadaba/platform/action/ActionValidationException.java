package com.javadaba.platform.action;

/**
 * Thrown by an {@link Action} when the CALLER's request is what's wrong -- a bad SQL statement, an
 * oversized response, a resource in a state that doesn't allow the requested operation -- as
 * opposed to {@link ActionUnavailableException} (an upstream dependency, e.g. the clients cluster
 * or an LLM provider, is unreachable/unconfigured: always a clean {@code 503}).
 *
 * <p>Added for {@code db.query@1} (plan 2026-07-09-dbaas-bases-de-datos-on-demand.md, #17, Task 5):
 * the first Action whose caller-facing errors genuinely need more than {@code 503}/{@code 500} to
 * be a usable API (a client's own SQL syntax error is not a generic {@code 500 product_invocation_
 * failed}, and pretending otherwise would make {@code db-query} confusing to actually use). This
 * closes the gap the platform ALREADY carried as BACKLOG debt (documented against {@code
 * mail-send}'s {@code recipient_suppressed} landing on a generic 500: "a sibling type of
 * ActionUnavailableException ... plus an additional catch in ProductInvocationResource") -- purely
 * additive: {@link com.javadaba.platform.action.Action} implementations that never throw this keep
 * their exact previous behavior (any other {@code RuntimeException} still falls through to the
 * generic {@code 500}).
 *
 * <p>Like {@code ActionUnavailableException}, the Tokens J hold is released without charging
 * regardless of exception type -- {@code httpStatus} only changes what status/body the caller
 * sees, never the billing outcome.
 */
public class ActionValidationException extends RuntimeException {

    private final String code;
    private final int httpStatus;

    public ActionValidationException(String code, String message, int httpStatus) {
        this(code, message, httpStatus, null);
    }

    public ActionValidationException(String code, String message, int httpStatus, Throwable cause) {
        super(message, cause);
        this.code = code == null || code.isBlank() ? "invalid_request" : code;
        this.httpStatus = httpStatus;
    }

    /** Machine-readable error code (e.g. {@code "sql_error"}), surfaced as {@code error} in the JSON body. */
    public String code() {
        return code;
    }

    /** The exact status the gateway should answer with (e.g. {@code 400}, {@code 409}, {@code 413}). */
    public int httpStatus() {
        return httpStatus;
    }
}
