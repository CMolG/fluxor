package com.javadaba.platform.shared;

import java.util.Objects;
import java.util.regex.Pattern;

public record ProductSlug(String value) {
    private static final Pattern VALID = Pattern.compile("[a-z0-9]+(?:-[a-z0-9]+)*");

    public ProductSlug {
        Objects.requireNonNull(value, "value");
        if (!VALID.matcher(value).matches()) {
            throw new InvalidProductSlugException(value);
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
