package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;

/** A downloadable Fluxor build for a platform. */
public record Release(String version, String platform, String url, String notes, Instant publishedAt) {
}
