package com.javadaba.platform.action;

/**
 * Thrown by an {@link Action} when it cannot run because an upstream
 * dependency (typically a third-party provider) is not configured or is
 * currently down — as opposed to a generic execution failure.
 *
 * <p>Distinguishing this from a plain {@link RuntimeException} lets callers
 * (see {@code ProductInvocationService}/{@code ProductInvocationResource} in
 * {@code contexts/execution}) surface a clean, retryable {@code 503} instead
 * of a generic {@code 500}, while the Tokens J hold is still released
 * without charge exactly like any other failed invocation — releasing the
 * hold does not depend on the exception type, only on the fact that the
 * invocation threw.
 */
public class ActionUnavailableException extends RuntimeException {

    private final String code;

    public ActionUnavailableException(String code, String message) {
        this(code, message, null);
    }

    public ActionUnavailableException(String code, String message, Throwable cause) {
        super(message, cause);
        this.code = code == null || code.isBlank() ? "provider_unavailable" : code;
    }

    /** Machine-readable error code (e.g. {@code "provider_unavailable"}), surfaced as {@code error} in the JSON body. */
    public String code() {
        return code;
    }
}
