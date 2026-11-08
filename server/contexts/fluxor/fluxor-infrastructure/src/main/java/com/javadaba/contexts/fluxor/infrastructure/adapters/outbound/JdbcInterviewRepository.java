package com.javadaba.contexts.fluxor.infrastructure.adapters.outbound;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.Interview;
import com.javadaba.contexts.fluxor.domain.InterviewConsent;
import com.javadaba.contexts.fluxor.domain.ports.InterviewRepository;
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
public class JdbcInterviewRepository implements InterviewRepository {

    private static final TypeReference<List<String>> STRINGS = new TypeReference<>() {
    };
    private static final TypeReference<List<Map<String, String>>> FOLLOW_UPS = new TypeReference<>() {
    };
    private static final String INTERVIEW_SELECT = "select id, account_id, role, form_version, started_at, updated_at "
            + "from fluxor_interview where account_id = ? and role = ?";
    private static final String CONSENT_SELECT = "select id, account_id, role, statement_version, subject, uses, "
            + "storage, shared_with, retention, excluded_uses, granted_at, ended_at, end_reason "
            + "from fluxor_interview_consent where account_id = ? and role = ? and ended_at is null";
    private static final String DELETE_ANSWERS = "delete from fluxor_interview_answer where interview_id in "
            + "(select id from fluxor_interview where account_id = ? and role = ?)";
    private static final String DELETE_INTERVIEW = "delete from fluxor_interview where account_id = ? and role = ?";
    private static final String END_CONSENT = "update fluxor_interview_consent set ended_at = ?, end_reason = ? "
            + "where account_id = ? and role = ? and ended_at is null";

    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    public JdbcInterviewRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    @Override
    public Optional<Interview> findInterview(UUID accountId, String role) {
        try (Connection connection = dataSource.getConnection()) {
            return findInterview(connection, accountId, role);
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the " + role + " interview", ex);
        }
    }

    @Override
    public Interview ensureInterview(Interview interview) {
        try (Connection connection = dataSource.getConnection()) {
            try (PreparedStatement insert = connection.prepareStatement(
                    "insert into fluxor_interview (id, account_id, role, form_version, started_at, updated_at) "
                            + "values (?, ?, ?, ?, ?, ?) on conflict (account_id, role) do nothing")) {
                insert.setObject(1, interview.id());
                insert.setObject(2, interview.accountId());
                insert.setString(3, interview.role());
                insert.setString(4, interview.formVersion());
                insert.setTimestamp(5, Timestamp.from(interview.startedAt()));
                insert.setTimestamp(6, Timestamp.from(interview.updatedAt()));
                insert.executeUpdate();
            }
            return findInterview(connection, interview.accountId(), interview.role()).orElseThrow(
                    () -> new IllegalStateException("The " + interview.role() + " interview vanished as it started"));
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to start the " + interview.role() + " interview", ex);
        }
    }

    @Override
    public List<Interview.Answer> findAnswers(UUID interviewId) {
        List<Interview.Answer> result = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "select question_id, text, follow_ups, skipped_reason, recorded_at "
                                + "from fluxor_interview_answer where interview_id = ? "
                                + "order by length(question_id), question_id")) {
            statement.setObject(1, interviewId);
            try (ResultSet rs = statement.executeQuery()) {
                while (rs.next()) {
                    List<Interview.FollowUp> followUps = read(rs.getString("follow_ups"), FOLLOW_UPS).stream()
                            .map(f -> new Interview.FollowUp(f.get("probe"), f.get("text")))
                            .toList();
                    result.add(new Interview.Answer(rs.getString("question_id"), rs.getString("text"), followUps,
                            rs.getString("skipped_reason"), rs.getTimestamp("recorded_at").toInstant()));
                }
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the interview's answers", ex);
        }
        return result;
    }

    @Override
    public void saveAnswer(UUID interviewId, Interview.Answer answer, Instant at) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement upsert = connection.prepareStatement(
                    "insert into fluxor_interview_answer (interview_id, question_id, text, follow_ups, skipped_reason, "
                            + "recorded_at) values (?, ?, ?, ?::jsonb, ?, ?) on conflict (interview_id, question_id) "
                            + "do update set text = excluded.text, follow_ups = excluded.follow_ups, "
                            + "skipped_reason = excluded.skipped_reason, recorded_at = excluded.recorded_at");
                    PreparedStatement touch = connection.prepareStatement(
                            "update fluxor_interview set updated_at = ? where id = ?")) {
                upsert.setObject(1, interviewId);
                upsert.setString(2, answer.questionId());
                upsert.setString(3, answer.text());
                upsert.setString(4, write(answer.followUps().stream()
                        .map(f -> Map.of("probe", f.probe(), "text", f.text())).toList()));
                upsert.setString(5, answer.skippedReason());
                upsert.setTimestamp(6, Timestamp.from(answer.recordedAt()));
                upsert.executeUpdate();
                touch.setTimestamp(1, Timestamp.from(at));
                touch.setObject(2, interviewId);
                touch.executeUpdate();
                connection.commit();
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to save answer " + answer.questionId(), ex);
        }
    }

    @Override
    public void deleteInterview(UUID accountId, String role) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                deleteInterview(connection, accountId, role);
                connection.commit();
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to erase the " + role + " interview", ex);
        }
    }

    @Override
    public Optional<InterviewConsent> findCurrentConsent(UUID accountId, String role) {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(CONSENT_SELECT)) {
            statement.setObject(1, accountId);
            statement.setString(2, role);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next() ? Optional.of(mapConsent(rs)) : Optional.empty();
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to read the " + role + " consent", ex);
        }
    }

    @Override
    public void grantConsent(InterviewConsent consent) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement insert = connection.prepareStatement(
                    "insert into fluxor_interview_consent (id, account_id, role, statement_version, subject, uses, "
                            + "storage, shared_with, retention, excluded_uses, granted_at) "
                            + "values (?, ?, ?, ?, ?, ?::jsonb, ?, ?::jsonb, ?, ?::jsonb, ?)")) {
                endConsent(connection, consent.accountId(), consent.role(), consent.grantedAt(),
                        InterviewConsent.REPLACED);
                insert.setObject(1, consent.id());
                insert.setObject(2, consent.accountId());
                insert.setString(3, consent.role());
                insert.setString(4, consent.statementVersion());
                insert.setString(5, consent.subject());
                insert.setString(6, write(consent.uses()));
                insert.setString(7, consent.storage());
                insert.setString(8, write(consent.sharedWith()));
                insert.setString(9, consent.retention());
                insert.setString(10, write(consent.excludedUses()));
                insert.setTimestamp(11, Timestamp.from(consent.grantedAt()));
                insert.executeUpdate();
                connection.commit();
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to record the " + consent.role() + " consent", ex);
        }
    }

    @Override
    public void withdrawConsent(UUID accountId, String role, Instant at) {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                endConsent(connection, accountId, role, at, InterviewConsent.WITHDRAWN);
                deleteInterview(connection, accountId, role);
                connection.commit();
            } catch (SQLException ex) {
                connection.rollback();
                throw ex;
            }
        } catch (SQLException ex) {
            throw new IllegalStateException("Unable to withdraw the " + role + " consent", ex);
        }
    }

    private static Optional<Interview> findInterview(Connection connection, UUID accountId, String role)
            throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(INTERVIEW_SELECT)) {
            statement.setObject(1, accountId);
            statement.setString(2, role);
            try (ResultSet rs = statement.executeQuery()) {
                return rs.next()
                        ? Optional.of(new Interview(rs.getObject("id", UUID.class),
                                rs.getObject("account_id", UUID.class), rs.getString("role"),
                                rs.getString("form_version"), rs.getTimestamp("started_at").toInstant(),
                                rs.getTimestamp("updated_at").toInstant()))
                        : Optional.empty();
            }
        }
    }

    private static void deleteInterview(Connection connection, UUID accountId, String role) throws SQLException {
        for (String sql : List.of(DELETE_ANSWERS, DELETE_INTERVIEW)) {
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setObject(1, accountId);
                statement.setString(2, role);
                statement.executeUpdate();
            }
        }
    }

    private static void endConsent(Connection connection, UUID accountId, String role, Instant at, String reason)
            throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(END_CONSENT)) {
            statement.setTimestamp(1, Timestamp.from(at));
            statement.setString(2, reason);
            statement.setObject(3, accountId);
            statement.setString(4, role);
            statement.executeUpdate();
        }
    }

    private InterviewConsent mapConsent(ResultSet rs) throws SQLException {
        Timestamp ended = rs.getTimestamp("ended_at");
        return new InterviewConsent(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getString("role"),
                rs.getString("statement_version"),
                rs.getString("subject"),
                read(rs.getString("uses"), STRINGS),
                rs.getString("storage"),
                read(rs.getString("shared_with"), STRINGS),
                rs.getString("retention"),
                read(rs.getString("excluded_uses"), STRINGS),
                rs.getTimestamp("granted_at").toInstant(),
                ended == null ? null : ended.toInstant(),
                rs.getString("end_reason"));
    }

    private <T> T read(String json, TypeReference<T> type) {
        try {
            return objectMapper.readValue(json, type);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to deserialize interview JSON", ex);
        }
    }

    private String write(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to serialize interview JSON", ex);
        }
    }
}
