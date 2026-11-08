package com.javadaba.platform.shared.ops;

import java.math.BigDecimal;

/**
 * Signals a context emits so the OPERATOR finds out about something, without knowing or caring
 * how it gets notified.
 *
 * <h2>Why CDI events instead of a direct call</h2>
 * The consumer lives in {@code apps/app-api} (the topmost module), and the contexts that emit
 * these signals sit below it: {@code billing} cannot — and should not — depend on the HTTP
 * application layer. A CDI event inverts that dependency without introducing a port and an
 * adapter for every notification, which for a one-way signal with no response would be pure
 * ceremony.
 *
 * <p>Desired consequence: if nobody observes these signals — for example, in a deployment where
 * notifications are turned off — emitting them <b>costs nothing and never fails</b>. The emitter
 * never finds out.
 *
 * <h2>What does NOT go here</h2>
 * Nothing aimed at the customer: that's what {@code PlatformNotifier} is for, the single
 * platform → customer channel that goes through the delivery queue with retries. These signals
 * are internal.
 */
public final class OperatorSignals {

    private OperatorSignals() {
    }

    /**
     * A payment confirmed by the gateway. Emitted <b>after</b> the balance is credited, never
     * before: a notification for a charge that later fails to credit would be worse than not
     * notifying at all.
     *
     * @param eur       actual amount charged, exactly as the gateway reports it (not computed).
     * @param tokensJ   balance credited.
     * @param reference payment session identifier, so it can be reconciled.
     * @param testAccount the owner's own test account paid: the alert says so.
     */
    public record PaymentReceived(BigDecimal eur, BigDecimal tokensJ, String reference, boolean testAccount) {
    }

    /**
     * A refund Stripe reported (JAVA-1194). Emitted after the reversal was applied or skipped, never
     * on its failure path. The four money signals below share these fields.
     *
     * @param eventId        the Stripe event id, which is also the dedupe key.
     * @param livemode       false for a Stripe test-mode event.
     * @param organizationId the account, null when the charge is not a top-up.
     * @param product        what it paid for: {@code top-up}, or {@code other} (a charge not made for a top-up).
     * @param amountCents    the amount exactly as Stripe sent it, in {@code currency}'s minor unit.
     * @param tokensJ        the Tokens J taken back, null when none were.
     * @param testAccount    the owner's test account, whose Tokens J are kept on purpose.
     */
    public record PaymentRefunded(String eventId, boolean livemode, java.util.UUID organizationId, String product,
            long amountCents, String currency, BigDecimal tokensJ, boolean testAccount) {
    }

    /** A dispute (chargeback) opened. {@code dueBy} is when the evidence is due, null if Stripe sent none. */
    public record DisputeOpened(String eventId, boolean livemode, java.util.UUID organizationId, String product,
            long amountCents, String currency, BigDecimal tokensJ, boolean testAccount, java.time.Instant dueBy) {
    }

    /** A dispute closed; {@code status} is Stripe's ({@code won}, {@code lost}, {@code warning_closed}, ...). */
    public record DisputeClosed(String eventId, boolean livemode, java.util.UUID organizationId, String product,
            long amountCents, String currency, BigDecimal tokensJ, boolean testAccount, String status) {
    }

    /**
     * A payment that failed. No money moved. {@code delayed} marks a delayed method (SEPA) whose
     * failure arrives days after the customer submitted it; {@code reason} is the decline message.
     */
    public record PaymentFailed(String eventId, boolean livemode, java.util.UUID organizationId, String product,
            long amountCents, String currency, boolean testAccount, String reason, boolean delayed) {
    }

    /**
     * A Stripe webhook answered something other than 2xx.
     *
     * @param endpoint  {@code topup} or {@code tributa-purchase}.
     * @param code      the wire error code the endpoint answered.
     * @param eventId   null when the request was never verified (bad signature, malformed body, not
     *                  configured): nothing in it can be trusted.
     * @param eventType null together with {@code eventId}.
     */
    public record StripeWebhookFailed(String endpoint, int status, String code, String message, String eventId,
            String eventType) {
    }

    /**
     * A page published automatically on the site (no human involved). It matters because it's
     * content going out under our name that nobody has reviewed before publishing.
     */
    public record PagePublished(String title, String url) {
    }

    /**
     * The AI provider rejected a call for lack of balance or quota. It's the most urgent signal
     * of all: while it lasts, <b>every</b> generation fails, and the SEO engine is the only paid
     * product with delivery.
     *
     * @param detail provider message, if any. Can be null.
     */
    public record AiBalanceDepleted(String provider, String detail) {
    }

    /**
     * An AI incident was opened (a plan exhausted or circuit-open, no plan available, a job not
     * delivered). Emitted once per open incident: a repeat while it stays open is not a new signal.
     *
     * @param scope   {@code plan:<name>}, {@code job:<uuid>} or {@code pool}.
     * @param code    one of the platform AI incident codes.
     * @param severity wire value of the incident's severity.
     * @param message what the call site said went wrong.
     * @param context call-site details (job, product, ...).
     */
    public record AiIncidentOpened(
            String scope,
            String code,
            String severity,
            String message,
            java.util.Map<String, Object> context) {
    }

    /**
     * An open AI incident closed itself.
     *
     * @param occurrences how many times it happened while it was open.
     */
    public record AiIncidentResolved(
            String scope,
            String code,
            int occurrences,
            java.time.Instant openedAt,
            java.time.Instant resolvedAt) {
    }

    /**
     * A metered hold was refused: the organization has too few Tokens J, or its own monthly cap
     * would be crossed. Emitted after the refusal is recorded, so the alert's daily count can be
     * read back from the record.
     *
     * @param reason       the wire code: {@code insufficient_balance} or {@code budget_exhausted}.
     * @param origin       the door the call came through (api, mcp, panel, app, job).
     * @param monthlyLimit the organization's cap, only for {@code budget_exhausted}.
     * @param spent        spent against that cap this month, only for {@code budget_exhausted}.
     */
    public record TokensJRefused(
            java.util.UUID organizationId,
            String reason,
            String operation,
            String origin,
            BigDecimal requested,
            BigDecimal balance,
            BigDecimal monthlyLimit,
            BigDecimal spent) {
    }

    /**
     * The site-integrity watchdog finished a run and found pages whose server-rendered HTML is
     * incomplete. Only emitted when there ARE failures: a daily "everything is fine" is a message
     * nobody reads, and it teaches people to skip the ones that do matter.
     *
     * <p>It carries the <b>failing URLs</b>, not just the counts. The equivalent watchdog in
     * {@code ../legally} sends only the breakdown and points at a panel to see the list — a panel
     * that was never built, so the alert names a place where the information isn't. The list
     * travels here so the message is actionable on its own.
     *
     * <p>Since JAVA-2024 it also goes out when articles only carry warnings: the new-domain manuscript's writing
     * checks (title promise, self-contained sections), which say a page reads worse, not that it is broken.
     *
     * @param checked    pages actually fetched (one sample per page shape, not the whole sitemap).
     * @param failed     how many of those came back with at least one error.
     * @param breakdown  issue code → how many pages carry it, warnings included. A page can carry several.
     * @param failedUrls the failing URLs, in the order they were checked.
     * @param warnedUrls the pages with warnings and no error.
     */
    public record SiteIntegrityChecked(
            int checked,
            int failed,
            java.util.Map<String, Long> breakdown,
            java.util.List<String> failedUrls,
            java.util.List<String> warnedUrls) {
    }

    /**
     * SEO Brain read our Search Console data the way the new-domain manuscript reads it (JAVA-2024). Each list holds
     * one line per diagnosis, "subject: evidence → action": content fixes the system may apply itself within its
     * brakes, structural proposals (301, 410, merges) that only a person executes, and observations, which ask on
     * purpose for no action.
     * {@code admission} is the per-template admission table, one line per template, header first (JAVA-2031). Emitted
     * when something was found or the table is not empty.
     */
    public record SearchConsoleDiagnosed(
            String property,
            java.util.List<String> contentFixes,
            java.util.List<String> proposals,
            java.util.List<String> observations,
            java.util.List<String> admission) {
    }
}
