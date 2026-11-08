package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.FluxorTask;
import com.javadaba.contexts.fluxor.domain.TaskSource;
import com.javadaba.contexts.fluxor.domain.ports.FluxorTaskRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class JdbcFluxorTaskRepository implements FluxorTaskRepository {

    private static final String SELECT = "select id, account_id, title, body, state, priority, epic_ref, "
            + "source, external_ref, version, updated_at, updated_by, deleted from fluxor_task";

    private final DataSource dataSource;

    public JdbcFluxorTaskRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void upsert(FluxorTask task) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_task (id, account_id, title, body, state, priority, epic_ref, source, "
                                + "external_ref, version, updated_at, updated_by, deleted) "
                                + "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                                + "on conflict (id) do update set "
                                + "title = excluded.title, body = excluded.body, state = excluded.state, "
                                + "priority = excluded.priority, epic_ref = excluded.epic_ref, "
                                + "external_ref = excluded.external_ref, version = excluded.version, "
                                + "updated_at = excluded.updated_at, updated_by = excluded.updated_by, "
                                + "deleted = excluded.deleted")) {
            statement.setObject(1, task.id());
            statement.setObject(2, task.accountId());
            statement.setString(3, task.title());
            statement.setString(4, task.body());
            statement.setString(5, task.state());
            statement.setInt(6, task.priority());
            statement.setString(7, task.epicRef());
            statement.setString(8, task.source().toDb());
            statement.setString(9, task.externalRef());
            statement.setInt(10, task.version());
            statement.setTimestamp(11, Timestamp.from(task.updatedAt()));
            statement.setString(12, task.updatedBy());
            statement.setBoolean(13, task.deleted());
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to upsert fluxor task", ex);
        }
    }

    @Override
    public Optional<FluxorTask> findById(UUID id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT + " where id = ?")) {
            statement.setObject(1, id);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor task", ex);
        }
    }

    @Override
    public List<FluxorTask> findByAccount(UUID accountId, boolean includeDeleted) {
        String sql = SELECT + " where account_id = ?" + (includeDeleted ? "" : " and deleted = false")
                + " order by updated_at desc";
        List<FluxorTask> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setObject(1, accountId);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list fluxor tasks", ex);
        }
        return result;
    }

    @Override
    public Optional<FluxorTask> findByExternalRef(UUID accountId, String externalRef) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        SELECT + " where account_id = ? and external_ref = ?")) {
            statement.setObject(1, accountId);
            statement.setString(2, externalRef);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor task by external ref", ex);
        }
    }

    @Override
    public List<FluxorTask> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit) {
        String sql = SELECT + " where account_id = ?"
                + (sinceUpdatedAt != null ? " and (updated_at, id) > (?, ?)" : "")
                + " order by updated_at, id limit ?";
        List<FluxorTask> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            int idx = 1;
            statement.setObject(idx++, accountId);
            if (sinceUpdatedAt != null) {
                statement.setTimestamp(idx++, Timestamp.from(sinceUpdatedAt));
                statement.setObject(idx++, sinceId);
            }
            statement.setInt(idx, limit);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor task sync page", ex);
        }
        return result;
    }

    private static FluxorTask map(ResultSet rs) throws SQLException {
        return new FluxorTask(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getString("title"),
                rs.getString("body"),
                rs.getString("state"),
                rs.getInt("priority"),
                rs.getString("epic_ref"),
                TaskSource.fromDb(rs.getString("source")),
                rs.getString("external_ref"),
                rs.getInt("version"),
                rs.getTimestamp("updated_at").toInstant(),
                rs.getString("updated_by"),
                rs.getBoolean("deleted"));
    }
}
