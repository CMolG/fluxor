package com.javadaba.platform.action;

import java.util.Objects;
import java.util.regex.Pattern;

public record ActionId(String value) {
    private static final Pattern VALID = Pattern.compile("[a-z0-9]+(?:[.-][a-z0-9]+)*@[1-9][0-9]*");

    public ActionId {
        Objects.requireNonNull(value, "value");
        if (!VALID.matcher(value).matches()) {
            throw new IllegalArgumentException("Invalid action id: " + value);
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
