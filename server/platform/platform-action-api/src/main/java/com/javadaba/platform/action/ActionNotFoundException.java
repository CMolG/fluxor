package com.javadaba.platform.action;

public class ActionNotFoundException extends RuntimeException {
    public ActionNotFoundException(ActionId actionId) {
        super("Action not found: " + actionId.value());
    }
}
