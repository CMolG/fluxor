package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.Pack;
import com.javadaba.contexts.fluxor.domain.ports.PackRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** card://JAVA-286. Nothing cascades: a pack's files and attachments go before the pack. */
@ApplicationScoped
public class JdbcPackRepository implements PackRepository {

    private static final String PACK_COLUMNS = "p.id, p.account_id, p.pack_id, p.role, p.form_version, "
            + "p.profile_version, p.statement_version, p.published_at";
    private static final List<String> DELETE_PACKS = List.of(
            "delete from fluxor_pack_project where pack in (select id from fluxor_pack where %s)",
            "delete from fluxor_pack_file where pack in (select id from fluxor_pack where %s)",
            "delete from fluxor_pack where %s");

    private final DataSource dataSource;

    public JdbcPackRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void publish(Pack pack, UUID projectId) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                UUID id = upsert(connection, pack);
                try (PreparedStatement delete = connection.prepareStatement(
                        "delete from fluxor_pack_file where pack = ?")) {
                    delete.setObject(1, id);
                    delete.executeUpdate();
                }
                try (PreparedStatement insert = connection.prepareStatement(
                        "insert into fluxor_pack_file (pack, path, sha256, content) values (?, ?, ?, ?)")) {
                    for (Pack.File file : pack.files()) {
                        insert.setObject(1, id);
                        insert.setString(2, file.path());
                        insert.setString(3, file.sha256());
                        insert.setString(4, file.content());
                        insert.addBatch();
                    }
                    insert.executeBatch();
                }
                try (PreparedStatement attach = connection.prepareStatement(
                        "insert into fluxor_pack_project (pack, project_id, attached_at) values (?, ?, ?) "
                                + "on conflict (pack, project_id) do nothing")) {
                    attach.setObject(1, id);
                    attach.setObject(2, projectId);
                    attach.setTimestamp(3, Timestamp.from(pack.publishedAt()));
                    attach.executeUpdate();
                }
                connection.commit();
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to publish pack " + pack.packId(), ex);
        }
    }

    /** The pack's row, created or brought to this publication; its id is kept, so attachments survive. */
    private static UUID upsert(Connection connection, Pack pack) throws SQLException {
        try (PreparedStatement upsert = connection.prepareStatement(
                "insert into fluxor_pack (id, account_id, pack_id, role, form_version, profile_version, "
                        + "statement_version, published_at) values (?, ?, ?, ?, ?, ?, ?, ?) "
                        + "on conflict (account_id, pack_id) do update set role = excluded.role, "
                        + "form_version = excluded.form_version, profile_version = excluded.profile_version, "
                        + "statement_version = excluded.statement_version, published_at = excluded.published_at "
                        + "returning id")) {
            upsert.setObject(1, pack.id());
            upsert.setObject(2, pack.accountId());
            upsert.setString(3, pack.packId());
            upsert.setString(4, pack.role());
            upsert.setString(5, pack.formVersion());
            upsert.setString(6, pack.profileVersion());
            upsert.setString(7, pack.statementVersion());
            upsert.setTimestamp(8, Timestamp.from(pack.publishedAt()));
            try (ResultSet rs = upsert.executeQuery()) {
                rs.next();
                return rs.getObject(1, UUID.class);
            }
        }
    }

    @Override
    public boolean detach(UUID accountId, String packId, UUID projectId) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "delete from fluxor_pack_project where project_id = ? and pack in "
                                + "(select id from fluxor_pack where account_id = ? and pack_id = ?)")) {
            statement.setObject(1, projectId);
            statement.setObject(2, accountId);
            statement.setString(3, packId);
            return statement.executeUpdate() > 0;
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to detach pack " + packId, ex);
        }
    }

    @Override
    public boolean delete(UUID accountId, String packId) {
        return deleteWhere("account_id = ? and pack_id = ?", accountId, packId) > 0;
    }

    @Override
    public void deleteRole(UUID accountId, String role) {
        deleteWhere("account_id = ? and role = ?", accountId, role);
    }

    /** Deletes the matching packs with their files and attachments, together; returns how many packs went. */
    private int deleteWhere(String where, UUID accountId, String value) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                int deleted = 0;
                for (String template : DELETE_PACKS) {
                    try (PreparedStatement statement = connection.prepareStatement(template.formatted(where))) {
                        statement.setObject(1, accountId);
                        statement.setString(2, value);
                        deleted = statement.executeUpdate();
                    }
                }
                connection.commit();
                return deleted;
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to delete packs (" + value + ")", ex);
        }
    }

    @Override
    public List<Pack> findAttached(UUID projectId) {
        try (Connection connection = dataSource.getConnection()) {
            List<Pack> packs = new ArrayList<>();
            try (PreparedStatement statement = connection.prepareStatement("select " + PACK_COLUMNS
                    + " from fluxor_pack p join fluxor_pack_project a on a.pack = p.id where a.project_id = ? "
                    + "order by p.pack_id")) {
                statement.setObject(1, projectId);
                try (ResultSet rs = statement.executeQuery()) {
                    while (rs.next()) {
                        UUID id = rs.getObject("id", UUID.class);
                        packs.add(new Pack(id, rs.getObject("account_id", UUID.class), rs.getString("pack_id"),
                                rs.getString("role"), rs.getString("form_version"), rs.getString("profile_version"),
                                rs.getString("statement_version"), rs.getTimestamp("published_at").toInstant(),
                                files(connection, id)));
                    }
                }
            }
            return packs;
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the packs of project " + projectId, ex);
        }
    }

    private static List<Pack.File> files(Connection connection, UUID pack) throws SQLException {
        List<Pack.File> files = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(
                "select path, sha256, content from fluxor_pack_file where pack = ? order by path")) {
            statement.setObject(1, pack);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    files.add(new Pack.File(rs.getString("path"), rs.getString("sha256"), rs.getString("content")));
                }
            }
        }
        return files;
    }
}
