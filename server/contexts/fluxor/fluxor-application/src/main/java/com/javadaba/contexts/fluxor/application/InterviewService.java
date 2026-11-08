package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.Interview;
import com.javadaba.contexts.fluxor.domain.InterviewConsent;
import com.javadaba.contexts.fluxor.domain.InterviewForm;
import com.javadaba.contexts.fluxor.domain.ports.HarnessRepository;
import com.javadaba.contexts.fluxor.domain.ports.InterviewRepository;
import com.javadaba.contexts.fluxor.domain.ports.PackRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * A CEET interview answered in Fluxor online and kept per account and role (card://JAVA-285), the
 * server side of what {@code ceet-core}'s {@code interview.py} does on a person's machine: consent
 * before the first answer, answers verbatim, skips with a reason, export as {@code answers.json},
 * and erasure. The form and the consent statement are read from Fluxor's catalog, never copied.
 */
@ApplicationScoped
public class InterviewService {

    /** The longest answer, follow-up or reason kept: a long interview answer is ~2,000 characters. */
    static final int MAX_TEXT = 20_000;

    private static final TypeReference<Map<String, Object>> JSON_OBJECT = new TypeReference<>() {
    };
    private static final Pattern STATEMENT_BLOCK = Pattern.compile("```text\\n(.*?)\\n```", Pattern.DOTALL);
    private static final String CORE = "ceet-core";
    private static final String CONSENT_DOC = "references/consent.md";

    private final HarnessRepository harness;
    private final InterviewRepository interviews;
    private final PackRepository packs;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Inject
    public InterviewService(HarnessRepository harness, InterviewRepository interviews, PackRepository packs,
            ObjectMapper objectMapper) {
        this(harness, interviews, packs, objectMapper, Clock.systemUTC());
    }

    InterviewService(HarnessRepository harness, InterviewRepository interviews, PackRepository packs,
            ObjectMapper objectMapper, Clock clock) {
        this.harness = harness;
        this.interviews = interviews;
        this.packs = packs;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    /** The role's form, from the newest catalog version of its meta-skill. */
    public InterviewForm form(String role) {
        HarnessItem item = harness.findItem(role, null)
                .filter(i -> i.kind() == HarnessItemKind.SKILL)
                .orElseThrow(() -> unknownRole(role));
        if (!(item.spec().get("form") instanceof Map<?, ?> form) || !(form.get("questions") instanceof String path)) {
            throw unknownRole(role);
        }
        try {
            return InterviewForm.of(objectMapper.readValue(file(item, path), JSON_OBJECT));
        } catch (IOException ex) {
            throw new IllegalStateException("The catalog's " + role + " form is not JSON", ex);
        }
    }

    /** The statement a person agrees to before the first answer: ceet-core's own block for it. */
    public Statement statement(String role) {
        form(role);
        HarnessItem core = harness.findItem(CORE, null)
                .orElseThrow(() -> new IllegalStateException("The catalog has no " + CORE));
        String doc = new String(file(core, CONSENT_DOC), StandardCharsets.UTF_8);
        Matcher block = STATEMENT_BLOCK.matcher(doc);
        while (block.find()) {
            String text = block.group(1);
            if (text.lines().findFirst().orElse("").contains("version " + InterviewConsent.STATEMENT_VERSION + ")")) {
                return new Statement(InterviewConsent.STATEMENT_VERSION, text);
            }
        }
        throw new IllegalStateException(CORE + "'s " + CONSENT_DOC + " has no statement "
                + InterviewConsent.STATEMENT_VERSION);
    }

    public Status status(UUID accountId, String role) {
        InterviewForm form = form(role);
        Optional<Interview> interview = interviews.findInterview(accountId, role);
        List<Interview.Answer> rows = interview.map(i -> interviews.findAnswers(i.id())).orElse(List.of());
        Map<String, Interview.Answer> byQuestion = rows.stream()
                .collect(Collectors.toMap(Interview.Answer::questionId, Function.identity()));
        List<ModuleProgress> modules = new ArrayList<>();
        List<String> requiredLeft = new ArrayList<>();
        int minutesLeft = 0;
        int requiredMinutesLeft = 0;
        for (InterviewForm.Module module : form.modules()) {
            int answered = 0;
            int skipped = 0;
            int total = 0;
            for (InterviewForm.Section section : module.sections()) {
                for (InterviewForm.Question question : section.questions()) {
                    total++;
                    Interview.Answer row = byQuestion.get(question.id());
                    if (row == null) {
                        minutesLeft += question.minutes();
                        if (question.required()) {
                            requiredLeft.add(question.id());
                            requiredMinutesLeft += question.minutes();
                        }
                    } else if (row.isAnswered()) {
                        answered++;
                    } else {
                        skipped++;
                    }
                }
            }
            modules.add(new ModuleProgress(module.id(), module.title(), module.optional(), total, answered, skipped));
        }
        return new Status(role, form.title(), form.formVersion(),
                interview.map(Interview::formVersion).orElse(null),
                interviews.findCurrentConsent(accountId, role).filter(InterviewConsent::admitsAnswers).orElse(null),
                rows, modules, requiredLeft, minutesLeft, requiredMinutesLeft, requiredLeft.isEmpty());
    }

    /**
     * The questions still open (neither answered nor skipped), in form order: where the person
     * resumes, whichever surface they stopped on (JAVA-699). Unlike {@code interview.py next}, it
     * does not rank optional questions by the profile gaps they close: the server's form leaves
     * {@code feeds} out.
     */
    public List<NextQuestion> next(UUID accountId, String role, int limit) {
        InterviewForm form = form(role);
        Set<String> done = interviews.findInterview(accountId, role)
                .map(i -> interviews.findAnswers(i.id()).stream().map(Interview.Answer::questionId)
                        .collect(Collectors.toSet()))
                .orElse(Set.of());
        List<NextQuestion> next = new ArrayList<>();
        for (InterviewForm.Module module : form.modules()) {
            for (InterviewForm.Section section : module.sections()) {
                for (InterviewForm.Question question : section.questions()) {
                    if (!done.contains(question.id()) && next.size() < limit) {
                        next.add(new NextQuestion(module.id(), module.title(), module.optional(), section.title(),
                                question));
                    }
                }
            }
        }
        return next;
    }

    /** Whether the person agreed to the current statement for this role (an unknown role is 404). */
    public boolean consented(UUID accountId, String role) {
        form(role);
        return interviews.findCurrentConsent(accountId, role).filter(InterviewConsent::admitsAnswers).isPresent();
    }

    /** Records consent to the current statement; one already given is replaced, keeping the answers. */
    public InterviewConsent grant(UUID accountId, String role, Grant grant) {
        form(role);
        if (grant == null || grant.subject() == null || grant.subject().isBlank() || grant.subject().length() > 200) {
            throw invalid("invalid_consent", "'subject' is the name or alias the person chose, up to 200 characters");
        }
        List<String> uses = grant.uses() == null ? List.of() : grant.uses().stream().map(String::strip).toList();
        if (uses.isEmpty() || uses.stream().anyMatch(u -> u.length() < 3 || u.length() > 500)) {
            throw invalid("invalid_consent",
                    "'uses' names at least one use the person agreed to, 3 to 500 characters each");
        }
        String storage = grant.storage() == null ? "local" : grant.storage();
        if (!storage.equals("local") && !storage.equals("repository")) {
            throw invalid("invalid_consent", "'storage' is local or repository");
        }
        List<String> sharedWith = grant.sharedWith() == null
                ? List.of()
                : grant.sharedWith().stream().map(String::strip).toList();
        if (sharedWith.stream().anyMatch(String::isEmpty)) {
            throw invalid("invalid_consent", "'sharedWith' names each person or group");
        }
        InterviewConsent consent = InterviewConsent.grant(accountId, role, grant.subject().strip(), uses, storage,
                sharedWith, Instant.now(clock));
        interviews.grantConsent(consent);
        return consent;
    }

    /**
     * Withdraws the consent and erases the interview with it, and the packs published under it
     * (card://JAVA-286); withdrawing none is not an error.
     */
    public void withdraw(UUID accountId, String role) {
        form(role);
        interviews.withdrawConsent(accountId, role, Instant.now(clock));
        packs.deleteRole(accountId, role);
    }

    public Status answer(UUID accountId, String role, String questionId, String text, boolean replace) {
        InterviewForm form = requireConsented(accountId, role, questionId);
        requireText("text", text);
        Interview interview = start(accountId, form);
        Optional<Interview.Answer> existing = row(interview, questionId);
        if (existing.isPresent() && existing.get().isAnswered() && !replace) {
            throw alreadyAnswered(questionId);
        }
        Instant now = Instant.now(clock);
        interviews.saveAnswer(interview.id(), Interview.Answer.answered(questionId, text, now), now);
        return status(accountId, role);
    }

    public Status followUp(UUID accountId, String role, String questionId, String probe, String text) {
        InterviewForm form = requireConsented(accountId, role, questionId);
        requireText("probe", probe);
        requireText("text", text);
        Interview interview = start(accountId, form);
        Interview.Answer answer = row(interview, questionId).filter(Interview.Answer::isAnswered)
                .orElseThrow(() -> new FluxorException("not_answered",
                        questionId + " has no answer yet to follow up on", 409));
        List<Interview.FollowUp> followUps = new ArrayList<>(answer.followUps());
        followUps.add(new Interview.FollowUp(probe, text));
        interviews.saveAnswer(interview.id(), new Interview.Answer(questionId, answer.text(), followUps, null,
                answer.recordedAt()), Instant.now(clock));
        return status(accountId, role);
    }

    public Status skip(UUID accountId, String role, String questionId, String reason, boolean replace) {
        InterviewForm form = requireConsented(accountId, role, questionId);
        requireText("reason", reason);
        Interview interview = start(accountId, form);
        if (row(interview, questionId).filter(Interview.Answer::isAnswered).isPresent() && !replace) {
            throw alreadyAnswered(questionId);
        }
        Instant now = Instant.now(clock);
        interviews.saveAnswer(interview.id(), Interview.Answer.skipped(questionId, reason, now), now);
        return status(accountId, role);
    }

    /**
     * The interview as ceet-core's {@code answers.json} ({@code schemas/answers.schema.json}), the
     * file {@code render_pack.py} reads: the person's copy of everything they gave, and the bridge
     * to a pack on their machine.
     */
    public Map<String, Object> export(UUID accountId, String role) {
        form(role);
        Interview interview = interviews.findInterview(accountId, role).orElseThrow(() -> new FluxorException(
                "interview_not_found", "No interview for " + role + " on this account", 404));
        InterviewConsent consent = interviews.findCurrentConsent(accountId, role).orElseThrow(() -> new FluxorException(
                "consent_required", "The interview has no current consent to export with", 409));
        Map<String, Object> answers = new LinkedHashMap<>();
        Map<String, Object> skipped = new LinkedHashMap<>();
        for (Interview.Answer row : interviews.findAnswers(interview.id())) {
            if (row.isAnswered()) {
                Map<String, Object> entry = new LinkedHashMap<>();
                entry.put("text", row.text());
                if (!row.followUps().isEmpty()) {
                    entry.put("followUps", row.followUps().stream()
                            .map(f -> Map.of("probe", f.probe(), "text", f.text())).toList());
                }
                entry.put("answeredAt", date(row.recordedAt()));
                answers.put(row.questionId(), entry);
            } else {
                skipped.put(row.questionId(), row.skippedReason());
            }
        }
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("statementVersion", consent.statementVersion());
        record.put("subject", consent.subject());
        record.put("basis", "consent");
        record.put("recordedAt", date(consent.grantedAt()));
        record.put("recordedBy", "Fluxor online");
        record.put("uses", consent.uses());
        record.put("storage", consent.storage());
        record.put("sharedWith", consent.sharedWith());
        record.put("retention", consent.retention());
        record.put("excludedUses", consent.excludedUses());
        Map<String, Object> export = new LinkedHashMap<>();
        export.put("schemaVersion", "1.0.0");
        export.put("role", role);
        export.put("formVersion", interview.formVersion());
        export.put("packId", role.replaceFirst("^ceet-", "") + "-" + slug(consent.subject()));
        export.put("startedAt", date(interview.startedAt()));
        export.put("consent", record);
        export.put("answers", answers);
        export.put("skipped", skipped);
        return export;
    }

    /**
     * Erases the interview and the packs rendered from it (card://JAVA-286); the consent stays
     * current, so the person can start again.
     */
    public void erase(UUID accountId, String role) {
        form(role);
        interviews.deleteInterview(accountId, role);
        packs.deleteRole(accountId, role);
    }

    private InterviewForm requireConsented(UUID accountId, String role, String questionId) {
        InterviewForm form = form(role);
        if (interviews.findCurrentConsent(accountId, role).filter(InterviewConsent::admitsAnswers).isEmpty()) {
            throw new FluxorException("consent_required", "Agree to the statement " + InterviewConsent.STATEMENT_VERSION
                    + " before the first answer", 409);
        }
        if (questionId == null || !form.has(questionId)) {
            throw new FluxorException("unknown_question", questionId + " is not a question of " + role + " form "
                    + form.formVersion(), 422);
        }
        return form;
    }

    private Interview start(UUID accountId, InterviewForm form) {
        Instant now = Instant.now(clock);
        return interviews.ensureInterview(new Interview(UUID.randomUUID(), accountId, form.role(), form.formVersion(),
                now, now));
    }

    private Optional<Interview.Answer> row(Interview interview, String questionId) {
        return interviews.findAnswers(interview.id()).stream().filter(a -> a.questionId().equals(questionId))
                .findFirst();
    }

    private byte[] file(HarnessItem item, String path) {
        if (item.spec().get("files") instanceof List<?> files) {
            for (Object file : files) {
                if (file instanceof Map<?, ?> entry && path.equals(entry.get("path"))
                        && entry.get("sha256") instanceof String sha256) {
                    return harness.findBlob(sha256).orElseThrow(() -> new IllegalStateException(
                            "The catalog lists " + item.key() + "/" + path + " but has no blob " + sha256));
                }
            }
        }
        throw new IllegalStateException("The catalog's " + item.key() + "@" + item.version() + " has no file " + path);
    }

    private static void requireText(String field, String value) {
        if (value == null || value.isBlank() || value.length() > MAX_TEXT) {
            throw invalid("invalid_answer", "'" + field + "' is required, up to " + MAX_TEXT + " characters");
        }
    }

    /** {@code <person>} of a pack id: kebab-case from the name the person chose. */
    static String slug(String subject) {
        String slug = subject.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", "-").replaceAll("^-|-$", "");
        return slug.isEmpty() ? "me" : slug;
    }

    private static String date(Instant at) {
        return at.atZone(ZoneOffset.UTC).toLocalDate().toString();
    }

    private static FluxorException unknownRole(String role) {
        return new FluxorException("unknown_role", "No CEET role " + role + " in the catalog", 404);
    }

    private static FluxorException alreadyAnswered(String questionId) {
        return new FluxorException("already_answered", questionId
                + " is already answered: add a follow-up, or send replace when the person restated it", 409);
    }

    private static FluxorException invalid(String code, String message) {
        return new FluxorException(code, message, 422);
    }

    public record Grant(String subject, List<String> uses, String storage, List<String> sharedWith) {
    }

    public record Statement(String version, String text) {
    }

    public record ModuleProgress(String id, String title, boolean optional, int questions, int answered, int skipped) {
    }

    /** An open question with where it sits in the form. */
    public record NextQuestion(String moduleId, String moduleTitle, boolean optionalModule, String section,
            InterviewForm.Question question) {
    }

    /**
     * Where an interview stands: {@code consent} is null until the person agrees to the current
     * statement, {@code formVersion} is the role's form now and {@code startedOnFormVersion} the one
     * the answers were given to (null before the first answer). {@code minutesLeft} counts every open
     * question, {@code requiredMinutesLeft} only the required ones.
     */
    public record Status(String role, String title, String formVersion, String startedOnFormVersion,
            InterviewConsent consent, List<Interview.Answer> answers, List<ModuleProgress> modules,
            List<String> requiredLeft, int minutesLeft, int requiredMinutesLeft, boolean readyToSynthesize) {
    }
}
