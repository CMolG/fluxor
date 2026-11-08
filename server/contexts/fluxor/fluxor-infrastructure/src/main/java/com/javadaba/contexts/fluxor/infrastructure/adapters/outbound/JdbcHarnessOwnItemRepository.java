package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessOwnership;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;
import com.javadaba.contexts.fluxor.domain.ports.HarnessOwnItemRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.sql.Types;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** The items people write (card://JAVA-750), in {@code fluxor_harness_item} beside the market's. */
@ApplicationScoped
public class JdbcHarnessOwnItemRepository implements HarnessOwnItemRepository {

    private static final TypeReference<Map<String, Object>> JSON_OBJECT = new TypeReference<>() {
    };
    private static final String UNIQUE_VIOLATION = "23505";

    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    public JdbcHarnessOwnItemRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    @Override
    public List<HarnessItem> latestVisible(UUID accountId, Collection<UUID> readableProjects,
            Collection<UUID> organizations, HarnessItemKind kind) {
        // Visibility and retirement are the same on every version of a key, so the newest row decides.
        String sql = "select distinct on (key) " + HarnessItemRows.COLUMNS + " from fluxor_harness_item"
                + " where owner_account_id is not null" + (kind != null ? " and kind = ?" : "")
                + " and (owner_account_id = ? or (retired_at is null and (visibility = 'public'"
                + " or (visibility = 'project' and harness_project_id = any(?))"
                + " or (visibility = 'organization' and organization_account_id = any(?)))))"
                + " order by key, version desc";
        List<HarnessItem> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            int i = 1;
            if (kind != null) {
                statement.setString(i++, kind.toDb());
            }
            statement.setObject(i++, accountId);
            statement.setArray(i++, connection.createArrayOf("uuid", readableProjects.toArray()));
            statement.setArray(i, connection.createArrayOf("uuid", organizations.toArray()));
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(HarnessItemRows.map(rs, this::readJson));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list the own harness items an account can see", ex);
        }
        return result;
    }

    @Override
    public void insert(HarnessItem item) {
        HarnessOwnership own = item.ownership();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_harness_item (key, version, kind, title, description, body, spec, "
                                + "provenance, owner_account_id, visibility, harness_project_id, "
                                + "organization_account_id) values (?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?)")) {
            statement.setString(1, item.key());
            statement.setInt(2, item.version());
            statement.setString(3, item.kind().toDb());
            statement.setString(4, item.title());
            statement.setString(5, item.description());
            statement.setString(6, item.body());
            statement.setString(7, objectMapper.writeValueAsString(item.spec()));
            statement.setString(8, item.provenance());
            statement.setObject(9, own.ownerAccountId());
            statement.setString(10, own.visibility().wire());
            statement.setObject(11, own.harnessProjectId(), Types.OTHER);
            statement.setObject(12, own.organizationAccountId(), Types.OTHER);
            statement.executeUpdate();
        } catch (SQLException ex) {
            if (UNIQUE_VIOLATION.equals(ex.getSQLState())) {
                throw new FluxorException("harness_item_key_taken",
                        "The key " + item.key() + " is taken: pick another one", 409);
            }
            throw new IllegalStateException("Unable to insert harness item " + item.key(), ex);
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize the spec of " + item.key(), ex);
        }
    }

    @Override
    public void updateOwnership(String key, HarnessOwnership ownership) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_harness_item set visibility = ?, harness_project_id = ?, "
                                + "organization_account_id = ?, retired_at = ? where key = ? and owner_account_id = ?")) {
            statement.setString(1, ownership.visibility().wire());
            statement.setObject(2, ownership.harnessProjectId(), Types.OTHER);
            statement.setObject(3, ownership.organizationAccountId(), Types.OTHER);
            statement.setTimestamp(4, ownership.retiredAt() == null ? null : Timestamp.from(ownership.retiredAt()));
            statement.setString(5, key);
            statement.setObject(6, ownership.ownerAccountId());
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to change who sees harness item " + key, ex);
        }
    }

    @Override
    public List<HarnessProjectItem> followers(String key) {
        List<HarnessProjectItem> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select project_id, item_key, item_version, params, changed_revision, removed_revision "
                                + "from fluxor_harness_project_item where item_key = ? and follows_latest "
                                + "and removed_revision is null order by project_id")) {
            statement.setString(1, key);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(new HarnessProjectItem(rs.getObject("project_id", UUID.class),
                            rs.getString("item_key"), rs.getInt("item_version"), readJson(rs.getString("params")),
                            rs.getLong("changed_revision"), null, true));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the projects following harness item " + key, ex);
        }
        return result;
    }

    @Override
    public java.util.Set<String> knownBlobs(Collection<String> sha256s) {
        java.util.Set<String> known = new java.util.HashSet<>();
        if (sha256s.isEmpty()) {
            return known;
        }
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select sha256 from fluxor_harness_blob where sha256 = any(?)")) {
            statement.setArray(1, connection.createArrayOf("text", sha256s.toArray()));
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    known.add(rs.getString(1));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read which harness blobs are stored", ex);
        }
        return known;
    }

    @Override
    public void insertBlob(String sha256, byte[] content) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement("insert into fluxor_harness_blob "
                        + "(sha256, content, size) values (?, ?, ?) on conflict (sha256) do nothing")) {
            statement.setString(1, sha256);
            statement.setBytes(2, content);
            statement.setInt(3, content.length);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to store harness blob " + sha256, ex);
        }
    }

    private Map<String, Object> readJson(String json) {
        try {
            return objectMapper.readValue(json, JSON_OBJECT);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to deserialize harness JSON", ex);
        }
    }
}
