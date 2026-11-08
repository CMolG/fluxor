package com.javadaba.platform.action;

import java.util.Map;
import java.util.Optional;

public interface ActionContext {

    <I, O> Optional<Action<I, O>> resolve(ActionId actionId);

    Map<String, Object> attributes();

    static ActionContext empty() {
        return EmptyActionContext.INSTANCE;
    }
}
