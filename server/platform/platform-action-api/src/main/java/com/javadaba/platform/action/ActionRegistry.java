package com.javadaba.platform.action;

import java.util.List;
import java.util.Optional;

public interface ActionRegistry {

    <I, O> Optional<Action<I, O>> find(ActionId actionId);

    List<ActionDescriptor> descriptors();
}
