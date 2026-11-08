package com.javadaba.platform.action;

public interface Action<I, O> {

    ActionDescriptor descriptor();

    Class<I> inputType();

    Class<O> outputType();

    O execute(I input, ActionContext ctx);

    default O run(I input) {
        return execute(input, ActionContext.empty());
    }
}
