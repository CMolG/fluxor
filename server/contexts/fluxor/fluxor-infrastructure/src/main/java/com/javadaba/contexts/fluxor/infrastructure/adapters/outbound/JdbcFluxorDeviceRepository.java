package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.FluxorDevice;
import com.javadaba.contexts.fluxor.domain.ports.FluxorDeviceRepository;
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
public class JdbcFluxorDeviceRepository implements FluxorDeviceRepository {

    private final DataSource dataSource;

    public JdbcFluxorDeviceRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void save(FluxorDevice device) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_device (id, account_id, name, token_hash, created_at, last_seen_at, revoked_at, "
                                + "oauth_family_id) values (?, ?, ?, ?, ?, ?, ?, ?)")) {
            statement.setObject(1, device.id());
            statement.setObject(2, device.accountId());
            statement.setString(3, device.name());
            statement.setString(4, device.tokenHash());
            statement.setTimestamp(5, Timestamp.from(device.createdAt()));
            statement.setTimestamp(6, device.lastSeenAt() == null ? null : Timestamp.from(device.lastSeenAt()));
            statement.setTimestamp(7, device.revokedAt() == null ? null : Timestamp.from(device.revokedAt()));
            statement.setObject(8, device.signInFamily());
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to save fluxor device", ex);
        }
    }

    @Override
    public Optional<FluxorDevice> findById(UUID id) {
        return findOneBy("id", id);
    }

    @Override
    public Optional<FluxorDevice> findByTokenHash(String tokenHash) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT + " where token_hash = ?")) {
            statement.setString(1, tokenHash);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor device by token hash", ex);
        }
    }

    @Override
    public List<FluxorDevice> findByAccount(UUID accountId) {
        List<FluxorDevice> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        SELECT + " where account_id = ? order by created_at desc")) {
            statement.setObject(1, accountId);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list fluxor devices", ex);
        }
        return result;
    }

    @Override
    public void revoke(UUID id, UUID accountId, Instant revokedAt) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_device set revoked_at = ? where id = ? and account_id = ? and revoked_at is null")) {
            statement.setTimestamp(1, Timestamp.from(revokedAt));
            statement.setObject(2, id);
            statement.setObject(3, accountId);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to revoke fluxor device", ex);
        }
    }

    @Override
    public void touchLastSeen(UUID id, Instant lastSeenAt) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_device set last_seen_at = ? where id = ?")) {
            statement.setTimestamp(1, Timestamp.from(lastSeenAt));
            statement.setObject(2, id);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to touch fluxor device last_seen_at", ex);
        }
    }

    private Optional<FluxorDevice> findOneBy(String column, Object value) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT + " where " + column + " = ?")) {
            statement.setObject(1, value);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor device", ex);
        }
    }

    private static final String SELECT = "select id, account_id, name, token_hash, created_at, last_seen_at, revoked_at from fluxor_device";

    private static FluxorDevice map(ResultSet rs) throws SQLException {
        Timestamp lastSeen = rs.getTimestamp("last_seen_at");
        Timestamp revoked = rs.getTimestamp("revoked_at");
        return new FluxorDevice(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getString("name"),
                rs.getString("token_hash"),
                rs.getTimestamp("created_at").toInstant(),
                lastSeen == null ? null : lastSeen.toInstant(),
                revoked == null ? null : revoked.toInstant());
    }
}
