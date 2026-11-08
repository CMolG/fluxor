package com.javadaba.contexts.fluxor.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * One consent a person gave for a CEET interview Fluxor online keeps (card://JAVA-285), with
 * {@code ceet-core}'s consent fields ({@code references/consent.md}). Only a record with no
 * {@code endedAt} is current; an ended one stays as proof of what was agreed.
 */
public record InterviewConsent(
        UUID id,
        UUID accountId,
        String role,
        String statementVersion,
        String subject,
        List<String> uses,
        String storage,
        List<String> sharedWith,
        String retention,
        List<String> excludedUses,
        Instant grantedAt,
        Instant endedAt,
        String endReason) {

    /** The statement for answers Fluxor online keeps: ceet-core's {@code HOSTED_CONSENT_STATEMENT_VERSION}. */
    public static final String STATEMENT_VERSION = "ceet-consent-2";

    /** ceet-core's {@code EXCLUDED_USES}: every record carries all five, whatever else was agreed. */
    public static final List<String> EXCLUDED_USES = List.of("performance-evaluation", "hiring-or-screening",
            "task-allocation-by-traits", "promotion-or-termination", "monitoring");

    /** The account retention policy ({@code doc://contracts/data-retention}), as the statement says it. */
    public static final String RETENTION = "Until erased in Fluxor online, or after two years of account inactivity";

    public static final String REPLACED = "replaced";
    public static final String WITHDRAWN = "withdrawn";

    public InterviewConsent {
        uses = List.copyOf(uses);
        sharedWith = List.copyOf(sharedWith);
        excludedUses = List.copyOf(excludedUses);
        if (!excludedUses.containsAll(EXCLUDED_USES)) {
            throw new IllegalArgumentException("A CEET consent always excludes " + EXCLUDED_USES);
        }
    }

    /** A consent to the current statement, given now. */
    public static InterviewConsent grant(UUID accountId, String role, String subject, List<String> uses,
            String storage, List<String> sharedWith, Instant at) {
        return new InterviewConsent(UUID.randomUUID(), accountId, role, STATEMENT_VERSION, subject, uses, storage,
                sharedWith, RETENTION, EXCLUDED_USES, at, null, null);
    }

    /** Current, and given to the statement this server asks for: the only kind that admits answers. */
    public boolean admitsAnswers() {
        return endedAt == null && STATEMENT_VERSION.equals(statementVersion);
    }
}
