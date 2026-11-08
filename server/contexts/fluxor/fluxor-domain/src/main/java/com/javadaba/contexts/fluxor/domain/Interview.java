package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * A CEET interview an account answers in Fluxor online, one per role (card://JAVA-285).
 * {@code formVersion} is the form it was started on; the role's form may move on after it.
 */
public record Interview(UUID id, UUID accountId, String role, String formVersion, Instant startedAt,
        Instant updatedAt) {

    /**
     * One question's row: its verbatim answer with the follow-ups to it, or the reason it was skipped.
     * {@code recordedAt} is when the answer or the skip was given.
     */
    public record Answer(String questionId, String text, List<FollowUp> followUps, String skippedReason,
            Instant recordedAt) {

        public Answer {
            followUps = List.copyOf(followUps);
        }

        public static Answer answered(String questionId, String text, Instant at) {
            return new Answer(questionId, text, List.of(), null, at);
        }

        public static Answer skipped(String questionId, String reason, Instant at) {
            return new Answer(questionId, null, List.of(), reason, at);
        }

        public boolean isAnswered() {
            return text != null;
        }
    }

    public record FollowUp(String probe, String text) {
    }
}
