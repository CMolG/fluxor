package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.Ticket;
import com.javadaba.contexts.fluxor.domain.TicketStatus;
import com.javadaba.contexts.fluxor.domain.ports.TicketRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class JdbcTicketRepository implements TicketRepository {

    private final DataSource dataSource;

    public JdbcTicketRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void save(Ticket ticket) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "insert into fluxor_ticket (id, subject, body, email, status) values (?, ?, ?, ?, ?)")) {
            statement.setObject(1, ticket.id());
            statement.setString(2, ticket.subject());
            statement.setString(3, ticket.body());
            statement.setString(4, ticket.email());
            statement.setString(5, ticket.status().name());
            statement.executeUpdate();
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to save ticket", ex);
        }
    }

    @Override
    public Optional<Ticket> findById(UUID id) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select id, subject, body, email, status, created_at from fluxor_ticket where id = ?")) {
            statement.setObject(1, id);
            try (ResultSet rs = statement.executeQuery()) {
                if (!rs.next()) {
                    return Optional.empty();
                }
                return Optional.of(new Ticket(
                        rs.getObject("id", UUID.class),
                        rs.getString("subject"),
                        rs.getString("body"),
                        rs.getString("email"),
                        TicketStatus.valueOf(rs.getString("status")),
                        rs.getTimestamp("created_at").toInstant()));
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read ticket", ex);
        }
    }
}
