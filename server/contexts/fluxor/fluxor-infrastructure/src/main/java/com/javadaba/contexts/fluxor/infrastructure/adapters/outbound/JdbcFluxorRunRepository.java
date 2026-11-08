package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorRun;
import com.javadaba.contexts.fluxor.domain.RunStatus;
import com.javadaba.contexts.fluxor.domain.ports.FluxorRunRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class JdbcFluxorRunRepository implements FluxorRunRepository {

    private static final String SELECT = "select id, account_id, flow_id, device_id, status, started_at, "
            + "finished_at, summary from fluxor_run";

    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    public JdbcFluxorRunRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    @Override
    public void save(FluxorRun run) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_run (id, account_id, flow_id, device_id, status, started_at, finished_at, summary) "
                                + "values (?, ?, ?, ?, ?, ?, ?, ?::jsonb)")) {
            bindInsertOrUpdate(statement, run);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to save fluxor run", ex);
        }
    }

    @Override
    public void updateStatus(FluxorRun run) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_run set status = ?, finished_at = ?, summary = ?::jsonb where id = ?")) {
            statement.setString(1, run.status().toDb());
            statement.setTimestamp(2, run.finishedAt() == null ? null : Timestamp.from(run.finishedAt()));
            statement.setString(3, run.summary() == null ? null : writeJson(run.summary()));
            statement.setObject(4, run.id());
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to update fluxor run status", ex);
        }
    }

    @Override
    public Optional<FluxorRun> findById(UUID id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT + " where id = ?")) {
            statement.setObject(1, id);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor run", ex);
        }
    }

    @Override
    public List<FluxorRun> findByAccount(UUID accountId, UUID flowId, RunStatus status) {
        StringBuilder sql = new StringBuilder(SELECT).append(" where account_id = ?");
        if (flowId != null) {
            sql.append(" and flow_id = ?");
        }
        if (status != null) {
            sql.append(" and status = ?");
        }
        sql.append(" order by started_at desc");
        List<FluxorRun> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql.toString())) {
            int idx = 1;
            statement.setObject(idx++, accountId);
            if (flowId != null) {
                statement.setObject(idx++, flowId);
            }
            if (status != null) {
                statement.setString(idx, status.toDb());
            }
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list fluxor runs", ex);
        }
        return result;
    }

    private void bindInsertOrUpdate(PreparedStatement statement, FluxorRun run) throws SQLException {
        statement.setObject(1, run.id());
        statement.setObject(2, run.accountId());
        statement.setObject(3, run.flowId());
        statement.setObject(4, run.deviceId());
        statement.setString(5, run.status().toDb());
        statement.setTimestamp(6, Timestamp.from(run.startedAt()));
        statement.setTimestamp(7, run.finishedAt() == null ? null : Timestamp.from(run.finishedAt()));
        statement.setString(8, run.summary() == null ? null : writeJson(run.summary()));
    }

    private String writeJson(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to serialize run summary", ex);
        }
    }

    @SuppressWarnings("unchecked")
    private FluxorRun map(ResultSet rs) throws SQLException {
        String summaryRaw = rs.getString("summary");
        Map<String, Object> summary = null;
        if (summaryRaw != null) {
            try {
                summary = objectMapper.readValue(summaryRaw, Map.class);
            } catch (Exception ex) {
                throw new IllegalStateException("Unable to deserialize run summary", ex);
            }
        }
        Timestamp finishedAt = rs.getTimestamp("finished_at");
        return new FluxorRun(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getObject("flow_id", UUID.class),
                rs.getObject("device_id", UUID.class),
                RunStatus.fromDb(rs.getString("status")),
                rs.getTimestamp("started_at").toInstant(),
                finishedAt == null ? null : finishedAt.toInstant(),
                summary);
    }
}
