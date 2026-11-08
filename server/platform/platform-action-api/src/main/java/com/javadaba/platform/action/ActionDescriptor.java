package com.javadaba.platform.action;

import com.javadaba.platform.shared.Cost;
import com.javadaba.platform.shared.JsonSchema;

import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.SequencedSet;
import java.util.Set;
import java.util.TreeSet;

/**
 * Profile of an {@code Action}: identity, schemas, cost, and tags.
 *
 * <p>Same as {@link JsonSchema}, this gets published: its schemas end up at
 * {@code /public/v1/products/{slug}/schema} and from there in the landing's committed
 * documentation pages. That's why neither the schemas nor {@code tags} can depend on the
 * iteration order of a {@code Map.of}/{@code Set.of} (random per JVM startup). Schemas are
 * written with {@link JsonSchema#ordered(Object...)}; {@code tags} follows the same rule as
 * {@link JsonSchema}: the declared order is kept if the collection guarantees it
 * ({@link java.util.SequencedSet}), and if not, it's sorted alphabetically — ugly but stable,
 * which is what keeps {@code ActionRegistrationStartup} from rewriting the metadata of every
 * {@code action_registration} on every startup.
 */
public record ActionDescriptor(
        ActionId id,
        String displayName,
        JsonSchema inputSchema,
        JsonSchema outputSchema,
        Cost baseCost,
        Idempotency idempotency,
        Set<String> tags) {
    public ActionDescriptor {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(displayName, "displayName");
        Objects.requireNonNull(inputSchema, "inputSchema");
        Objects.requireNonNull(outputSchema, "outputSchema");
        Objects.requireNonNull(baseCost, "baseCost");
        Objects.requireNonNull(idempotency, "idempotency");
        tags = stableTags(tags);
    }

    private static Set<String> stableTags(Set<String> tags) {
        Set<String> source = tags == null ? Set.of() : tags;
        Collection<String> ordered = source.size() > 1 && !(source instanceof SequencedSet<String>)
                ? new TreeSet<>(source)
                : source;
        return Collections.unmodifiableSequencedSet(new LinkedHashSet<>(ordered));
    }
}
