package com.javadaba.platform.shared;

/**
 * A string that cannot be a {@link ProductSlug}. Its own type so the HTTP edge can answer it as
 * the 404 it is — a path that names no product — instead of the 500 a bare
 * {@link IllegalArgumentException} escapes as ([[JDB-200]]). It still extends
 * {@code IllegalArgumentException}, so every caller already catching that keeps working.
 */
public class InvalidProductSlugException extends IllegalArgumentException {

    private final String slug;

    public InvalidProductSlugException(String slug) {
        super("Invalid product slug: " + slug);
        this.slug = slug;
    }

    public String slug() {
        return slug;
    }
}
