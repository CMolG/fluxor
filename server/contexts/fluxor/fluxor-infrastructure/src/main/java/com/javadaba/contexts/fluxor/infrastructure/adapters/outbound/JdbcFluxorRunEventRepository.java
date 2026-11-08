package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorRunEvent;
import com.javadaba.contexts.fluxor.domain.ports.FluxorRunEventRepository;
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
import java.util.UUID;

@ApplicationScoped
public class JdbcFluxorRunEventRepository implements FluxorRunEventRepository {

    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    public JdbcFluxorRunEventRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    @Override
    public void appendAll(List<FluxorRunEvent> events) {
        if (events.isEmpty()) {
            return;
        }
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_run_event (run_id, seq, step_id, type, payload, at) "
                                + "values (?, ?, ?, ?, ?::jsonb, ?)")) {
            for (FluxorRunEvent event : events) {
                statement.setObject(1, event.runId());
                statement.setInt(2, event.seq());
                statement.setString(3, event.stepId());
                statement.setString(4, event.type());
                statement.setString(5, writeJson(event.payload()));
                statement.setTimestamp(6, Timestamp.from(event.at()));
                statement.addBatch();
            }
            statement.executeBatch();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to append fluxor run events", ex);
        }
    }

    @Override
    public List<FluxorRunEvent> findAfterSeq(UUID runId, int afterSeq) {
        List<FluxorRunEvent> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select run_id, seq, step_id, type, payload, at from fluxor_run_event "
                                + "where run_id = ? and seq > ? order by seq")) {
            statement.setObject(1, runId);
            statement.setInt(2, afterSeq);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor run events", ex);
        }
        return result;
    }

    @Override
    public int maxSeq(UUID runId) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select coalesce(max(seq), -1) as max_seq from fluxor_run_event where run_id = ?")) {
            statement.setObject(1, runId);
            try (ResultSet rs = statement.executeQuery()) {
                rs.next();
                return rs.getInt("max_seq");
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor run event max seq", ex);
        }
    }

    private String writeJson(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to serialize run event payload", ex);
        }
    }

    @SuppressWarnings("unchecked")
    private FluxorRunEvent map(ResultSet rs) throws SQLException {
        Map<String, Object> payload;
        try {
            payload = objectMapper.readValue(rs.getString("payload"), Map.class);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to deserialize run event payload", ex);
        }
        return new FluxorRunEvent(
                rs.getObject("run_id", UUID.class),
                rs.getInt("seq"),
                rs.getString("step_id"),
                rs.getString("type"),
                payload,
                rs.getTimestamp("at").toInstant());
    }
}
