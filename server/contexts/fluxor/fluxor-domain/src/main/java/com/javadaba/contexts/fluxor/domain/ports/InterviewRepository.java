package com.javadaba.contexts.fluxor.domain.ports;

import com.javadaba.contexts.fluxor.domain.Interview;
import com.javadaba.contexts.fluxor.domain.InterviewConsent;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** The CEET interviews an account answers in Fluxor online, and its consents (card://JAVA-285). */
public interface InterviewRepository {

    Optional<Interview> findInterview(UUID accountId, String role);

    /** Starts the account's interview for the role, or returns the one already there. */
    Interview ensureInterview(Interview interview);

    /** Every answered or skipped question, ordered by question id. */
    List<Interview.Answer> findAnswers(UUID interviewId);

    /** Writes the question's row (insert or overwrite) and moves the interview's {@code updatedAt}, together. */
    void saveAnswer(UUID interviewId, Interview.Answer answer, Instant at);

    /** Deletes the interview and every answer in it. Nothing to delete is not an error. */
    void deleteInterview(UUID accountId, String role);

    Optional<InterviewConsent> findCurrentConsent(UUID accountId, String role);

    /** Ends the current consent as replaced, if any, and records this one as current, together. */
    void grantConsent(InterviewConsent consent);

    /** Ends the current consent as withdrawn and deletes the interview, together. */
    void withdrawConsent(UUID accountId, String role, Instant at);
}
