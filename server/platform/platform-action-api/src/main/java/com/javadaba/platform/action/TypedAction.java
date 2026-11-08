package com.javadaba.platform.action;

/**
 * Compatibility bridge with the original javadaba-core TypedAction signature.
 */
@Deprecated(since = "0.1.0", forRemoval = false)
public interface TypedAction<I, O> extends Action<I, O> {

    @Override
    O run(I input);

    @Override
    default O execute(I input, ActionContext ctx) {
        return run(input);
    }
}
