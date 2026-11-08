package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.HarnessEnrollment;
import com.javadaba.contexts.fluxor.domain.ports.HarnessEnrollmentRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class JdbcHarnessEnrollmentRepository implements HarnessEnrollmentRepository {

    private final DataSource dataSource;

    public JdbcHarnessEnrollmentRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void save(HarnessEnrollment enrollment) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_harness_enrollment (id, code_hash, account_id, expires_at, created_at) "
                                + "values (?, ?, ?, ?, ?)")) {
            statement.setObject(1, enrollment.id());
            statement.setString(2, enrollment.codeHash());
            statement.setObject(3, enrollment.accountId());
            statement.setTimestamp(4, Timestamp.from(enrollment.expiresAt()));
            statement.setTimestamp(5, Timestamp.from(enrollment.createdAt()));
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to save a harness enrollment", ex);
        }
    }

    @Override
    public Optional<HarnessEnrollment> findByCodeHash(String codeHash) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select id, code_hash, account_id, expires_at, consumed_at, device_id, created_at "
                                + "from fluxor_harness_enrollment where code_hash = ?")) {
            statement.setString(1, codeHash);
            try (ResultSet rs = statement.executeQuery()) {
                if (!rs.next()) {
                    return Optional.empty();
                }
                Timestamp consumed = rs.getTimestamp("consumed_at");
                return Optional.of(new HarnessEnrollment(
                        rs.getObject("id", UUID.class),
                        rs.getString("code_hash"),
                        rs.getObject("account_id", UUID.class),
                        rs.getTimestamp("expires_at").toInstant(),
                        consumed == null ? null : consumed.toInstant(),
                        rs.getObject("device_id", UUID.class),
                        rs.getTimestamp("created_at").toInstant()));
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read a harness enrollment", ex);
        }
    }

    @Override
    public boolean consume(UUID id, UUID deviceId, Instant now) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_harness_enrollment set consumed_at = ?, device_id = ? "
                                + "where id = ? and consumed_at is null and expires_at > ?")) {
            statement.setTimestamp(1, Timestamp.from(now));
            statement.setObject(2, deviceId);
            statement.setObject(3, id);
            statement.setTimestamp(4, Timestamp.from(now));
            return statement.executeUpdate() == 1;
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to consume a harness enrollment", ex);
        }
    }

    @Override
    public void deleteExpired(Instant now) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "delete from fluxor_harness_enrollment where expires_at <= ?")) {
            statement.setTimestamp(1, Timestamp.from(now));
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to sweep expired harness enrollments", ex);
        }
    }
}
