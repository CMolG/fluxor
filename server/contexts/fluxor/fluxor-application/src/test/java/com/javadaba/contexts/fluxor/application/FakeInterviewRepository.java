package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.Interview;
import com.javadaba.contexts.fluxor.domain.InterviewConsent;
import com.javadaba.contexts.fluxor.domain.ports.InterviewRepository;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** Only the consents: what publishing a pack reads. */
final class FakeInterviewRepository implements InterviewRepository {
    private final Map<String, InterviewConsent> consents = new HashMap<>();

    void consent(UUID accountId, String role) {
        grantConsent(InterviewConsent.grant(accountId, role, "Alex", List.of("work on my projects"), "local",
                List.of(), Instant.parse("2026-10-01T00:00:00Z")));
    }

    @Override
    public Optional<InterviewConsent> findCurrentConsent(UUID accountId, String role) {
        return Optional.ofNullable(consents.get(accountId + "/" + role));
    }

    @Override
    public void grantConsent(InterviewConsent consent) {
        consents.put(consent.accountId() + "/" + consent.role(), consent);
    }

    @Override
    public void withdrawConsent(UUID accountId, String role, Instant at) {
        consents.remove(accountId + "/" + role);
    }

    @Override
    public Optional<Interview> findInterview(UUID accountId, String role) {
        return Optional.empty();
    }

    @Override
    public Interview ensureInterview(Interview interview) {
        throw new UnsupportedOperationException();
    }

    @Override
    public List<Interview.Answer> findAnswers(UUID interviewId) {
        return List.of();
    }

    @Override
    public void saveAnswer(UUID interviewId, Interview.Answer answer, Instant at) {
        throw new UnsupportedOperationException();
    }

    @Override
    public void deleteInterview(UUID accountId, String role) {
    }
}
