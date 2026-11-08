package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.FluxorPairing;
import com.javadaba.contexts.fluxor.domain.PairingStatus;
import com.javadaba.contexts.fluxor.domain.ports.PairingRepository;
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
public class JdbcPairingRepository implements PairingRepository {

    private static final String SELECT = "select id, pairing_token_hash, pin_hash, poll_token_hash, status, "
            + "account_id, device_id, device_name_hint, expires_at, created_at from fluxor_pairing";

    private final DataSource dataSource;

    public JdbcPairingRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void save(FluxorPairing pairing) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_pairing (id, pairing_token_hash, pin_hash, poll_token_hash, status, "
                                + "account_id, device_id, device_name_hint, expires_at, created_at) "
                                + "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")) {
            statement.setObject(1, pairing.id());
            statement.setString(2, pairing.pairingTokenHash());
            statement.setString(3, pairing.pinHash());
            statement.setString(4, pairing.pollTokenHash());
            statement.setString(5, pairing.status().toDb());
            statement.setObject(6, pairing.accountId());
            statement.setObject(7, pairing.deviceId());
            statement.setString(8, pairing.deviceNameHint());
            statement.setTimestamp(9, Timestamp.from(pairing.expiresAt()));
            statement.setTimestamp(10, Timestamp.from(pairing.createdAt()));
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to save fluxor pairing", ex);
        }
    }

    @Override
    public Optional<FluxorPairing> findByPairingTokenHash(String pairingTokenHash) {
        return findOneBy("pairing_token_hash", pairingTokenHash);
    }

    @Override
    public Optional<FluxorPairing> findByPollTokenHash(String pollTokenHash) {
        return findOneBy("poll_token_hash", pollTokenHash);
    }

    @Override
    public List<FluxorPairing> findPendingByPinHash(String pinHash) {
        List<FluxorPairing> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        SELECT + " where pin_hash = ? and status = 'pending'")) {
            statement.setString(1, pinHash);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    result.add(map(rs));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to find pending fluxor pairings by pin hash", ex);
        }
        return result;
    }

    @Override
    public void updateStatus(UUID id, PairingStatus status) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_pairing set status = ? where id = ?")) {
            statement.setString(1, status.toDb());
            statement.setObject(2, id);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to update fluxor pairing status", ex);
        }
    }

    @Override
    public void markClaimed(UUID id, UUID accountId, UUID deviceId) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_pairing set status = 'claimed', account_id = ?, device_id = ? "
                                + "where id = ? and status = 'pending'")) {
            statement.setObject(1, accountId);
            statement.setObject(2, deviceId);
            statement.setObject(3, id);
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to mark fluxor pairing claimed", ex);
        }
    }

    @Override
    public void markExpiredIfPast(UUID id, Instant now) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "update fluxor_pairing set status = 'expired' "
                                + "where id = ? and status = 'pending' and expires_at < ?")) {
            statement.setObject(1, id);
            statement.setTimestamp(2, Timestamp.from(now));
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to mark fluxor pairing expired", ex);
        }
    }

    private Optional<FluxorPairing> findOneBy(String column, String value) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(SELECT + " where " + column + " = ?")) {
            statement.setString(1, value);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read fluxor pairing", ex);
        }
    }

    private static FluxorPairing map(ResultSet rs) throws SQLException {
        return new FluxorPairing(
                rs.getObject("id", UUID.class),
                rs.getString("pairing_token_hash"),
                rs.getString("pin_hash"),
                rs.getString("poll_token_hash"),
                PairingStatus.fromDb(rs.getString("status")),
                rs.getObject("account_id", UUID.class),
                rs.getObject("device_id", UUID.class),
                rs.getString("device_name_hint"),
                rs.getTimestamp("expires_at").toInstant(),
                rs.getTimestamp("created_at").toInstant());
    }
}
