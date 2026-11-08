package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.HarnessProjectItem;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
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
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class JdbcHarnessRepository implements HarnessRepository {

    private static final TypeReference<Map<String, Object>> JSON_OBJECT = new TypeReference<>() {
    };
    private static final String UNIQUE_VIOLATION = "23505";
    private static final String PROJECT_SELECT = "select id, account_id, name, officium_project_id, revision, "
            + "updated_at from fluxor_harness_project";

    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    public JdbcHarnessRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    @Override
    public List<HarnessItem> latestCatalog(HarnessItemKind kind) {
        // The market's catalog: an own item (card://JAVA-750) is listed by HarnessOwnItemRepository.
        String sql = "select distinct on (key) " + HarnessItemRows.COLUMNS + " from fluxor_harness_item"
                + " where owner_account_id is null" + (kind != null ? " and kind = ?" : "")
                + " order by key, version desc";
        List<HarnessItem> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            if (kind != null) {
                statement.setString(1, kind.toDb());
            }
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(mapItem(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list the harness catalog", ex);
        }
        return result;
    }

    @Override
    public Optional<HarnessItem> findItem(String key, Integer version) {
        String sql = "select " + HarnessItemRows.COLUMNS + " from fluxor_harness_item where key = ?"
                + (version != null ? " and version = ?" : "")
                + " order by version desc limit 1";
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, key);
            if (version != null) {
                statement.setInt(2, version);
            }
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(mapItem(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read harness item " + key, ex);
        }
    }

    @Override
    public void insertProject(HarnessProject project) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_harness_project (id, account_id, name, officium_project_id, revision, "
                                + "created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?)")) {
            statement.setObject(1, project.id());
            statement.setObject(2, project.accountId());
            statement.setString(3, project.name());
            statement.setObject(4, project.officiumProjectId(), Types.OTHER);
            statement.setLong(5, project.revision());
            statement.setTimestamp(6, Timestamp.from(project.updatedAt()));
            statement.setTimestamp(7, Timestamp.from(project.updatedAt()));
            statement.executeUpdate();
        } catch (SQLException ex) {
            if (UNIQUE_VIOLATION.equals(ex.getSQLState())) {
                throw new FluxorException("officium_project_already_linked",
                        "A harness project is already linked to this Officium project", 409);
            }
            throw new IllegalStateException("Unable to insert harness project", ex);
        }
    }

    @Override
    public Optional<HarnessProject> findByOfficiumProject(UUID officiumProjectId) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        PROJECT_SELECT + " where officium_project_id = ?")) {
            statement.setObject(1, officiumProjectId);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(mapProject(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the harness project linked to an Officium project", ex);
        }
    }

    @Override
    public List<HarnessProject> findByOfficiumProjects(Collection<UUID> officiumProjectIds) {
        if (officiumProjectIds.isEmpty()) {
            return List.of();
        }
        List<HarnessProject> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        PROJECT_SELECT + " where officium_project_id = any(?) order by name, id")) {
            statement.setArray(1, connection.createArrayOf("uuid", officiumProjectIds.toArray()));
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(mapProject(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list the harness projects linked to Officium projects", ex);
        }
        return result;
    }

    @Override
    public Optional<HarnessProject> findProject(UUID id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(PROJECT_SELECT + " where id = ?")) {
            statement.setObject(1, id);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(mapProject(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read harness project", ex);
        }
    }

    @Override
    public List<HarnessProject> findProjects(UUID accountId) {
        List<HarnessProject> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        PROJECT_SELECT + " where account_id = ? order by updated_at desc")) {
            statement.setObject(1, accountId);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(mapProject(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list harness projects", ex);
        }
        return result;
    }

    @Override
    public List<HarnessProjectItem> findProjectItems(UUID projectId) {
        List<HarnessProjectItem> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select project_id, item_key, item_version, params, changed_revision, removed_revision, "
                                + "follows_latest from fluxor_harness_project_item where project_id = ? order by item_key")) {
            statement.setObject(1, projectId);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(new HarnessProjectItem(
                            rs.getObject("project_id", UUID.class),
                            rs.getString("item_key"),
                            rs.getInt("item_version"),
                            readJson(rs.getString("params")),
                            rs.getLong("changed_revision"),
                            rs.getObject("removed_revision", Long.class),
                            rs.getBoolean("follows_latest")));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read harness project items", ex);
        }
        return result;
    }

    @Override
    public boolean commit(UUID projectId, long expectedRevision, long newRevision, List<HarnessProjectItem> items) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement bump = connection.prepareStatement(
                    "update fluxor_harness_project set revision = ?, updated_at = now() where id = ? and revision = ?")) {
                bump.setLong(1, newRevision);
                bump.setObject(2, projectId);
                bump.setLong(3, expectedRevision);
                if (bump.executeUpdate() != 1) {
                    connection.rollback();
                    return false;
                }
            }
            try (PreparedStatement upsert = connection.prepareStatement(
                    "insert into fluxor_harness_project_item (project_id, item_key, item_version, params, "
                            + "changed_revision, removed_revision, follows_latest) values (?, ?, ?, ?::jsonb, ?, ?, ?) "
                            + "on conflict (project_id, item_key) do update set item_version = excluded.item_version, "
                            + "params = excluded.params, changed_revision = excluded.changed_revision, "
                            + "removed_revision = excluded.removed_revision, follows_latest = excluded.follows_latest")) {
                for (HarnessProjectItem item : items) {
                    upsert.setObject(1, item.projectId());
                    upsert.setString(2, item.itemKey());
                    upsert.setInt(3, item.itemVersion());
                    upsert.setString(4, writeJson(item.params()));
                    upsert.setLong(5, item.changedRevision());
                    upsert.setObject(6, item.removedRevision(), Types.BIGINT);
                    upsert.setBoolean(7, item.followsLatest());
                    upsert.addBatch();
                }
                upsert.executeBatch();
            }
            connection.commit();
            return true;
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to commit harness revision " + newRevision, ex);
        }
    }

    @Override
    public Optional<byte[]> findBlob(String sha256) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        // An atom's companion files (card://JAVA-2009) are listed under marketFiles.
                        "select b.content from fluxor_harness_blob b where b.sha256 = ? and exists ("
                                + "select 1 from fluxor_harness_item i where i.spec -> 'files' @> "
                                + "jsonb_build_array(jsonb_build_object('sha256', b.sha256)) or i.spec -> 'marketFiles' @> "
                                + "jsonb_build_array(jsonb_build_object('sha256', b.sha256)))")) {
            statement.setString(1, sha256);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(rs.getBytes("content")) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read harness blob " + sha256, ex);
        }
    }

    @Override
    public List<HarnessItem> findItemsListing(String sha256) {
        List<HarnessItem> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement("select " + HarnessItemRows.COLUMNS
                        + " from fluxor_harness_item where spec -> 'files' @> jsonb_build_array(jsonb_build_object("
                        + "'sha256', ?::text)) or spec -> 'marketFiles' @> jsonb_build_array(jsonb_build_object("
                        + "'sha256', ?::text))")) {
            statement.setString(1, sha256);
            statement.setString(2, sha256);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(mapItem(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the items listing blob " + sha256, ex);
        }
        return result;
    }

    private HarnessItem mapItem(ResultSet rs) throws SQLException {
        return HarnessItemRows.map(rs, this::readJson);
    }

    private static HarnessProject mapProject(ResultSet rs) throws SQLException {
        return new HarnessProject(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getString("name"),
                rs.getObject("officium_project_id", UUID.class),
                rs.getLong("revision"),
                rs.getTimestamp("updated_at").toInstant());
    }

    private Map<String, Object> readJson(String json) {
        try {
            return objectMapper.readValue(json, JSON_OBJECT);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to deserialize harness JSON", ex);
        }
    }

    private String writeJson(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to serialize harness params", ex);
        }
    }
}
