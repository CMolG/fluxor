package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.InterviewConsent;
import com.javadaba.contexts.fluxor.domain.InterviewForm;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** card://JAVA-285: every CEET role's form in Fluxor's market reads as the interview needs it. */
class InterviewFormTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void everyRoleFormInTheMarketParses() throws IOException {
        List<Path> forms;
        try (Stream<Path> roles = Files.list(marketDir().resolve("meta-skills"))) {
            forms = roles.map(dir -> dir.resolve("interview/form.json")).filter(Files::isRegularFile).toList();
        }
        assertThat(forms).hasSizeGreaterThanOrEqualTo(15);
        for (Path file : forms) {
            Map<String, Object> raw = objectMapper.readValue(file.toFile(), new TypeReference<>() {
            });
            InterviewForm form = InterviewForm.of(raw);
            assertThat(form.role()).isEqualTo(file.getParent().getParent().getFileName().toString());
            assertThat(form.questions()).isNotEmpty();
            assertThat(form.questions()).extracting(InterviewForm.Question::id)
                    .doesNotHaveDuplicates().allMatch(id -> id.matches("Q[1-9][0-9]*"));
            assertThat(form.questions()).anyMatch(InterviewForm.Question::required);
        }
    }

    @Test
    void theBackendFormKeepsItsOrderAndProbes() throws IOException {
        Map<String, Object> raw = objectMapper.readValue(
                marketDir().resolve("meta-skills/ceet-backend-engineer/interview/form.json").toFile(),
                new TypeReference<>() {
                });
        InterviewForm form = InterviewForm.of(raw);
        assertThat(form.modules().get(0).id()).isEqualTo("core");
        assertThat(form.questions().get(0).id()).isEqualTo("Q1");
        assertThat(form.has("Q4")).isTrue();
        assertThat(form.has("Q9999")).isFalse();
        assertThat(form.questions().stream().filter(q -> q.id().equals("Q4")).findFirst().orElseThrow().probes())
                .isNotEmpty();
    }

    @Test
    void aConsentAlwaysExcludesTheFiveUses() {
        InterviewConsent granted = InterviewConsent.grant(UUID.randomUUID(), "ceet-backend-engineer", "Alex",
                List.of("help me review code"), "local", List.of(), Instant.now());
        assertThat(granted.excludedUses()).containsExactlyElementsOf(InterviewConsent.EXCLUDED_USES);
        assertThat(granted.admitsAnswers()).isTrue();
        assertThatThrownBy(() -> new InterviewConsent(UUID.randomUUID(), UUID.randomUUID(), "ceet-backend-engineer",
                InterviewConsent.STATEMENT_VERSION, "Alex", List.of("x y z"), "local", List.of(),
                InterviewConsent.RETENTION, List.of("monitoring"), Instant.now(), null, null))
                .isInstanceOf(IllegalArgumentException.class);
        InterviewConsent older = new InterviewConsent(UUID.randomUUID(), UUID.randomUUID(), "ceet-backend-engineer",
                "ceet-consent-1", "Alex", List.of("x y z"), "local", List.of(), InterviewConsent.RETENTION,
                InterviewConsent.EXCLUDED_USES, Instant.now(), null, null);
        assertThat(older.admitsAnswers()).isFalse();
    }

    @Test
    void aPackIdPersonIsKebabCase() {
        assertThat(InterviewService.slug("Alex")).isEqualTo("alex");
        assertThat(InterviewService.slug("  Mary-Ann O'Neil ")).isEqualTo("mary-ann-o-neil");
        assertThat(InterviewService.slug("李")).isEqualTo("me");
    }

    private static Path marketDir() {
        for (Path dir = Path.of("").toAbsolutePath(); dir != null; dir = dir.getParent()) {
            Path market = dir.resolve("packages/fluxor-market");
            if (Files.isRegularFile(market.resolve("marketplace.json"))) {
                return market;
            }
        }
        throw new IllegalStateException("No packages/fluxor-market above " + Path.of("").toAbsolutePath());
    }
}
