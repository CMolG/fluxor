package com.javadaba.contexts.fluxor.application;

import jakarta.enterprise.context.ApplicationScoped;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;

/**
 * {@code fluxor-sync}, the writer a project's machine runs to pull its harness (JAVA-162, ADR 0019).
 * The API holds it for three things that must agree byte for byte: the public download, the sha256
 * that {@code harness.bootstrap} hands the agent to check that download, and the copy every
 * snapshot carries at {@code .harness/bin/fluxor-sync.py}, which is how an installed writer updates
 * itself.
 *
 * <p>The source is the market's {@code packages/fluxor-market/tools/fluxor_sync.py}; this resource
 * is a copy, and {@code scripts/test/fluxor-sync-copy.test.mjs} fails when the two differ. It is
 * read when the bean is first used, never in a static initializer (native discipline).
 */
@ApplicationScoped
public class HarnessWriter {

    static final String RESOURCE = "javadaba/fluxor/fluxor-sync.py";
    /** Its public download, under the API's base URL ({@code FluxorWriterResource}). */
    public static final String ROUTE = "/fluxor/v1/writer/fluxor-sync.py";

    private final byte[] bytes;
    private final String sha256;

    public HarnessWriter() {
        try (InputStream in = HarnessWriter.class.getClassLoader().getResourceAsStream(RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("The writer is missing from the classpath: " + RESOURCE);
            }
            this.bytes = in.readAllBytes();
        } catch (IOException ex) {
            throw new UncheckedIOException("Unable to read " + RESOURCE, ex);
        }
        this.sha256 = DeviceTokens.sha256Hex(bytes);
    }

    public byte[] bytes() {
        return bytes.clone();
    }

    public String text() {
        return new String(bytes, StandardCharsets.UTF_8);
    }

    public String sha256() {
        return sha256;
    }

    public long size() {
        return bytes.length;
    }
}
