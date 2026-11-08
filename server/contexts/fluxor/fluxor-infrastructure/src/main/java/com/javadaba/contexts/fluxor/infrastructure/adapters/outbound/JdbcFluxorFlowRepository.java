package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FlowOrigin;
import com.javadaba.contexts.fluxor.domain.FlowStatus;
import com.javadaba.contexts.fluxor.domain.FluxorFlow;
import com.javadaba.contexts.fluxor.domain.ports.FluxorFlowRepository;
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
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class JdbcFluxorFlowRepository implements FluxorFlowRepository {

    private static final String SELECT = "select id, account_id, name, definition, canvas, origin, status, version, "
            + "updated_at from fluxor_flow";

    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    public JdbcFluxorFlowRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    @Override
    public void upsert(FluxorFlow flow) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_flow (id, account_id, name, definition, canvas, origin, status, version, "
                                + "updated_at) values (?, ?, ?, ?::jsonb, ?::jsonb, ?, ?, ?, ?) "
                                + "on conflict (id) do update set "
                                + "name = excluded.name, definition = excluded.definition, canvas = excluded.canvas, "
                                + "origin = excluded.origin, "
                                + "status = excluded.status, version = excluded.version, updated_at = excluded.updated_at")) {
            statement.setObject(1, flow.id());
            statement.setObject(2, flow.accountId());
            statement.setString(3, flow.name());
            statement.setString(4, writeJson(flow.definition()));
            statement.setString(5, writeJson(flow.canvas()));
            statement.setString(6, flow.origin().toDb());
            statement.setString(7, flow.status().toDb());
            statement.setInt(8, flow.version());
            statement.setTimestamp(9, Timestamp.from(flow.updatedAt()));
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to upsert fluxor flow", ex);
        }
    }

    @Override
    public boolean update(FluxorFlow flow, int expectedVersion) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_flow set name = ?, definition = ?::jsonb, canvas = ?::jsonb, origin = ?, "
                                + "status = ?, version = ?, updated_at = ? "
                                + "where id = ? and account_id = ? and version = ?")) {
            statement.setString(1, flow.name());
            statement.setString(2, writeJson(flow.definition()));
            statement.setString(3, writeJson(flow.canvas()));
            statement.setString(4, flow.origin().toDb());
            statement.setString(5, flow.status().toDb());
            statement.setInt(6, flow.version());
            statement.setTimestamp(7, Timestamp.from(flow.updatedAt()));
            statement.setObject(8, flow.id());
            statement.setObject(9, flow.accountId());
            statement.setInt(10, expectedVersion);
            return statement.executeUpdate() == 1;
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to update fluxor flow", ex);
        }
    }

    @Override
    public Optional<FluxorFlow> findById(UUID id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT + " where id = ?")) {
            statement.setObject(1, id);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor flow", ex);
        }
    }

    @Override
    public List<FluxorFlow> findByAccount(UUID accountId) {
        List<FluxorFlow> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        SELECT + " where account_id = ? order by updated_at desc")) {
            statement.setObject(1, accountId);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list fluxor flows", ex);
        }
        return result;
    }

    @Override
    public List<FluxorFlow> findSince(UUID accountId, Instant sinceUpdatedAt, UUID sinceId, int limit) {
        String sql = SELECT + " where account_id = ? and definition is not null"
                + (sinceUpdatedAt != null ? " and (updated_at, id) > (?, ?)" : "")
                + " order by updated_at, id limit ?";
        List<FluxorFlow> result = new ArrayList<>();
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
            throw new IllegalStateException("Unable to read fluxor flow sync page", ex);
        }
        return result;
    }

    @Override
    public void delete(UUID id) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                for (String sql : List.of(
                        "delete from fluxor_run_event where run_id in (select id from fluxor_run where flow_id = ?)",
                        "delete from fluxor_run where flow_id = ?",
                        "delete from fluxor_flow where id = ?")) {
                    try (PreparedStatement statement = connection.prepareStatement(sql)) {
                        statement.setObject(1, id);
                        statement.executeUpdate();
                    }
                }
                connection.commit();
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            } finally {
                connection.setAutoCommit(true);
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to delete fluxor flow", ex);
        }
    }

    private String writeJson(Map<String, Object> value) {
        if (value == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to serialize flow JSON", ex);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readJson(String json) {
        if (json == null) {
            return null;
        }
        try {
            return objectMapper.readValue(json, Map.class);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to deserialize flow JSON", ex);
        }
    }

    private FluxorFlow map(ResultSet rs) throws SQLException {
        return new FluxorFlow(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getString("name"),
                readJson(rs.getString("definition")),
                readJson(rs.getString("canvas")),
                FlowOrigin.fromDb(rs.getString("origin")),
                FlowStatus.fromDb(rs.getString("status")),
                rs.getInt("version"),
                rs.getTimestamp("updated_at").toInstant());
    }
}
