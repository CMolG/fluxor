package com.javadaba.platform.action;

import java.util.Map;
import java.util.Optional;

enum EmptyActionContext implements ActionContext {
    INSTANCE;

    @Override
    public <I, O> Optional<Action<I, O>> resolve(ActionId actionId) {
        return Optional.empty();
    }

    @Override
    public Map<String, Object> attributes() {
        return Map.of();
    }
}
