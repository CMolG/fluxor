package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;
import com.javadaba.contexts.fluxor.domain.HarnessVisibility;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;

/** One {@code fluxor_harness_item} row as an item, market or own (card://JAVA-750), for both repositories. */
final class HarnessItemRows {

    static final String COLUMNS = "key, version, kind, title, description, body, spec, provenance, "
            + "market_version, content_hash, owner_account_id, visibility, harness_project_id, "
            + "organization_account_id, retired_at";

    private HarnessItemRows() {
    }

    static HarnessItem map(ResultSet rs, Function<String, Map<String, Object>> json) throws SQLException {
        UUID owner = rs.getObject("owner_account_id", UUID.class);
        Timestamp retired = rs.getTimestamp("retired_at");
        HarnessOwnership ownership = owner == null
                ? null
                : new HarnessOwnership(owner,
                        HarnessVisibility.fromWire(rs.getString("visibility")),
                        rs.getObject("harness_project_id", UUID.class),
                        rs.getObject("organization_account_id", UUID.class),
                        retired == null ? null : retired.toInstant());
        return new HarnessItem(
                rs.getString("key"),
                rs.getInt("version"),
                HarnessItemKind.fromDb(rs.getString("kind")),
                rs.getString("title"),
                rs.getString("description"),
                rs.getString("body"),
                json.apply(rs.getString("spec")),
                rs.getString("provenance"),
                rs.getString("market_version"),
                rs.getString("content_hash"),
                ownership);
    }
}
