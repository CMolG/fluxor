package com.javadaba.contexts.fluxor.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.Pack;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** card://JAVA-286: a CEET pack published to Fluxor online, every hash proven before it is kept. */
class PackServiceTest {

    static final String ROLE = "ceet-backend-engineer";
    static final String PACK_ID = "backend-engineer-alex";

    private final FakeHarnessRepository catalog = new FakeHarnessRepository();
    private final HarnessService harness = new HarnessService(catalog, new FakeOfficiumProjects());
    private final FakeInterviewRepository interviews = new FakeInterviewRepository();
    private final FakePackRepository repository = new FakePackRepository();
    private final ObjectMapper json = new ObjectMapper();
    private final PackService packs = new PackService(harness, catalog, interviews, repository, json);
    private final UUID account = UUID.randomUUID();
    private UUID project;

    @BeforeEach
    void setUp() {
        catalog.addItem(new HarnessItem(ROLE, 1, HarnessItemKind.SKILL, "Backend engineer", "", "",
                Map.of("packaging", "meta"), "test", null, null));
        catalog.addItem(new HarnessItem("review-diff", 1, HarnessItemKind.SKILL, "Review a diff", "", "",
                Map.of("packaging", "traditional"), "test", null, null));
        project = harness.createProject(account, "app", null).id();
        interviews.consent(account, ROLE);
    }

    /** A rendered pack's shared files, its pack.json hashing them, and its root .gitignore. */
    static Map<String, String> renderedPack(Map<String, Object> overrides) {
        Map<String, String> shared = new LinkedHashMap<>();
        shared.put("core.md", "# Alex's core\n\nI decide with data [Q1].\n");
        shared.put("cognitive-profile.json", "{\"role\": \"ceet-backend-engineer\"}\n");
        shared.put("bin/ceet_check.py", "print('check')\n");
        shared.put("adapters/claude-code/settings.hooks.json", "{\"hooks\": {\"PreToolUse\": [{\"matcher\": \"Bash\", "
                + "\"hooks\": [{\"type\": \"command\", \"command\": \"python3 .harness/packs/" + PACK_ID
                + "/bin/ceet_check.py claude-code --pack .harness/packs/" + PACK_ID + "\"}]}]}}\n");
        List<Map<String, String>> listed = new ArrayList<>();
        shared.forEach((path, text) -> listed.add(Map.of("path", path, "sha256", DeviceTokens.sha256Hex(text))));
        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("schemaVersion", "1.0.0");
        manifest.put("packId", PACK_ID);
        manifest.put("metaSkill", ROLE + "@2.0.0");
        manifest.put("formVersion", "2.0.0");
        manifest.put("source", "interview");
        manifest.put("profileVersion", "1.0.0");
        manifest.put("renderedAt", "2026-10-01");
        manifest.put("consent", Map.of("statementVersion", "ceet-consent-2", "storage", "local"));
        manifest.put("templatesHash", "c".repeat(64));
        manifest.put("files", listed);
        manifest.putAll(overrides);
        Map<String, String> files = new LinkedHashMap<>(shared);
        try {
            files.put("pack.json", new ObjectMapper().writeValueAsString(manifest));
        } catch (Exception ex) {
            throw new IllegalStateException(ex);
        }
        files.put(".gitignore", "*\n");
        return files;
    }

    static List<PackService.Upload> uploads(Map<String, String> files) {
        return files.entrySet().stream().map(e -> new PackService.Upload(e.getKey(), e.getValue())).toList();
    }

    private Pack publish(Map<String, String> files) {
        return packs.publish(account, project, PACK_ID, uploads(files));
    }

    private void refused(Map<String, String> files, String code) {
        assertThatThrownBy(() -> publish(files)).isInstanceOf(FluxorException.class)
                .extracting(e -> ((FluxorException) e).code()).isEqualTo(code);
    }

    @Test
    void aRenderedPackIsKeptAsHashedAndAttachedToTheProject() {
        Pack pack = publish(renderedPack(Map.of()));

        assertThat(pack.role()).isEqualTo(ROLE);
        assertThat(pack.formVersion()).isEqualTo("2.0.0");
        assertThat(pack.statementVersion()).isEqualTo("ceet-consent-2");
        assertThat(pack.files()).extracting(Pack.File::path).containsExactly(".gitignore",
                "adapters/claude-code/settings.hooks.json", "bin/ceet_check.py", "cognitive-profile.json", "core.md",
                "pack.json");
        assertThat(packs.attached(project)).extracting(Pack::packId).containsExactly(PACK_ID);
    }

    @Test
    void publishingAgainReplacesTheFiles() {
        publish(renderedPack(Map.of()));
        Map<String, String> next = renderedPack(Map.of("profileVersion", "1.1.0"));

        publish(next);

        Pack pack = packs.attached(project).get(0);
        assertThat(pack.profileVersion()).isEqualTo("1.1.0");
        assertThat(pack.files()).filteredOn(f -> f.path().equals("pack.json")).singleElement()
                .extracting(Pack.File::content).isEqualTo(next.get("pack.json"));
    }

    @Test
    void thePrivateFolderNeverLeavesTheMachine() {
        Map<String, String> files = renderedPack(Map.of());
        files.put("private/answers.json", "{\"answers\": {}}");
        refused(files, "pack_private_path");
    }

    @Test
    void aFileThatDoesNotMatchItsHashIsRefused() {
        Map<String, String> files = renderedPack(Map.of());
        files.put("core.md", "# Edited after the render\n");
        refused(files, "pack_hash_mismatch");
    }

    @Test
    void onlyWhatPackJsonListsIsKept() {
        Map<String, String> extra = renderedPack(Map.of());
        extra.put("notes.md", "not rendered\n");
        refused(extra, "invalid_pack");

        Map<String, String> missing = renderedPack(Map.of());
        missing.remove("core.md");
        refused(missing, "invalid_pack");

        Map<String, String> noManifest = renderedPack(Map.of());
        noManifest.remove("pack.json");
        refused(noManifest, "invalid_pack");
    }

    @Test
    void aPathThatLeavesThePackIsRefused() {
        for (String path : List.of("../AGENTS.md", "/etc/passwd", "core\\md", "a//b", ".fluxor/lock.json",
                "./core.md")) {
            Map<String, String> files = renderedPack(Map.of());
            files.put(path, "x");
            assertThatThrownBy(() -> publish(files)).as(path).isInstanceOf(FluxorException.class);
        }
    }

    @Test
    void aSimulatedPackIsRefused() {
        refused(renderedPack(Map.of("source", "simulation")), "pack_not_interview");
    }

    @Test
    void aPackKeptUnderAnotherStatementIsRefused() {
        refused(renderedPack(Map.of("consent", Map.of("statementVersion", "ceet-consent-1"))), "pack_consent");
    }

    @Test
    void aPackKeptLocalTravelsWithTheGitignoreThatKeepsItOutOfCommits() {
        Map<String, String> files = renderedPack(Map.of());
        files.remove(".gitignore");
        assertThatThrownBy(() -> publish(files)).isInstanceOf(FluxorException.class).hasMessageContaining(".gitignore");

        Map<String, String> committed = renderedPack(Map.of("consent",
                Map.of("statementVersion", "ceet-consent-2", "storage", "repository")));
        committed.remove(".gitignore");
        assertThat(publish(committed).files()).extracting(Pack.File::path).doesNotContain(".gitignore");
    }

    @Test
    void aPackIsRefusedWhenTheAccountHoldsNoCurrentConsentForTheRole() {
        interviews.withdrawConsent(account, ROLE, null);
        refused(renderedPack(Map.of()), "consent_required");
    }

    @Test
    void theRoleMustBeAMetaSkillOfTheCatalogAndPrefixThePackId() {
        refused(renderedPack(Map.of("metaSkill", "ceet-astronaut")), "pack_unknown_role");
        refused(renderedPack(Map.of("metaSkill", "review-diff")), "pack_unknown_role");
        assertThatThrownBy(() -> packs.publish(account, project, "copywriter-alex",
                uploads(renderedPack(Map.of("packId", "copywriter-alex")))))
                .isInstanceOf(FluxorException.class).hasMessageContaining("starts with backend-engineer-");
    }

    @Test
    void thePackIdIsSafeAndTheOnePackJsonNames() {
        assertThatThrownBy(() -> packs.publish(account, project, "Backend_Alex", uploads(renderedPack(Map.of()))))
                .isInstanceOf(FluxorException.class).hasMessageContaining("is not a pack id");
        assertThatThrownBy(() -> packs.publish(account, project, "backend-engineer-sam",
                uploads(renderedPack(Map.of())))).isInstanceOf(FluxorException.class)
                .hasMessageContaining("names pack backend-engineer-alex");
    }

    @Test
    void anotherAccountsProjectIsNotFound() {
        assertThatThrownBy(() -> packs.publish(UUID.randomUUID(), project, PACK_ID, uploads(renderedPack(Map.of()))))
                .isInstanceOf(FluxorException.class).extracting(e -> ((FluxorException) e).httpStatus()).isEqualTo(404);
    }

    @Test
    void aFileOverTheCapIsRefused() {
        Map<String, String> files = renderedPack(Map.of());
        files.put("core.md", "x".repeat(PackService.MAX_FILE_BYTES + 1));
        refused(files, "pack_too_large");
    }

    @Test
    void detachingKeepsThePackAndUnpublishingDeletesIt() {
        publish(renderedPack(Map.of()));
        UUID other = harness.createProject(account, "other", null).id();
        packs.publish(account, other, PACK_ID, uploads(renderedPack(Map.of())));

        packs.detach(account, project, PACK_ID);
        assertThat(packs.attached(project)).isEmpty();
        assertThat(packs.attached(other)).hasSize(1);

        packs.unpublish(account, PACK_ID);
        assertThat(packs.attached(other)).isEmpty();
        assertThatThrownBy(() -> packs.unpublish(account, PACK_ID)).isInstanceOf(FluxorException.class)
                .extracting(e -> ((FluxorException) e).httpStatus()).isEqualTo(404);
        assertThatThrownBy(() -> packs.detach(account, project, PACK_ID)).isInstanceOf(FluxorException.class)
                .extracting(e -> ((FluxorException) e).httpStatus()).isEqualTo(404);
    }
}
