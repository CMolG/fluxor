package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.javadaba.contexts.fluxor.domain.Release;
import com.javadaba.contexts.fluxor.domain.ports.ReleaseRepository;
import jakarta.enterprise.context.ApplicationScoped;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@ApplicationScoped
public class JdbcReleaseRepository implements ReleaseRepository {

    private static final String SELECT = "select version, platform, url, notes, published_at from fluxor_release";

    private final DataSource dataSource;

    public JdbcReleaseRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public List<Release> all() {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection
                        .prepareStatement(SELECT + " order by published_at desc, platform asc");
                ResultSet rs = statement.executeQuery()) {
            List<Release> releases = new ArrayList<>();
            while (rs.next()) {
                releases.add(map(rs));
            }
            return releases;
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to list releases", ex);
        }
    }

    @Override
    public Optional<Release> latest(String platform) {
        boolean byPlatform = platform != null && !platform.isBlank();
        String sql = SELECT + (byPlatform ? " where platform = ?" : "") + " order by published_at desc limit 1";
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            if (byPlatform) {
                statement.setString(1, platform);
            }
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(map(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read latest release", ex);
        }
    }

    private Release map(ResultSet rs) throws SQLException {
        return new Release(
                rs.getString("version"),
                rs.getString("platform"),
                rs.getString("url"),
                rs.getString("notes"),
                rs.getTimestamp("published_at").toInstant());
    }
}
