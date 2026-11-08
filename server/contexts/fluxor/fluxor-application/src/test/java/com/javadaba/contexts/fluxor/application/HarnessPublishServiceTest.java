package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects.Access;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * card://JAVA-2007: skills, hooks and files published from a folder, by sha256, as own items: each
 * file lands at its path on every reader's pull, an unchanged file is never sent twice, a path that
 * leaves where its kind may write is refused, and only someone who can see the item reads its bytes.
 */
class HarnessPublishServiceTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final FakeOfficiumProjects officium = new FakeOfficiumProjects();
    private final HarnessService harness = new HarnessService(repo, officium);
    private final HarnessOwnItemService items = new HarnessOwnItemService(harness, repo, repo);
    private final HarnessPublishService publish = new HarnessPublishService(items, repo, repo);
    private final HarnessSnapshotService snapshots = new HarnessSnapshotService(harness, repo, new HarnessWriter(),
            new FakePackRepository());
    private final UUID author = UUID.randomUUID();
    private final UUID reader = UUID.randomUUID();
    private final UUID stranger = UUID.randomUUID();
    private final UUID board = UUID.randomUUID();
    private HarnessProject project;

    @BeforeEach
    void setUp() {
        officium.grant(author, board, Access.OWNER);
        officium.grant(reader, board, Access.VIEWER);
        officium.grant(stranger, board, Access.NONE);
        project = harness.createProject(author, "javadaba", board);
    }

    private static HarnessPublishService.PublishedFile file(String path, byte[] content, boolean send) {
        return new HarnessPublishService.PublishedFile(path, DeviceTokens.sha256Hex(content), content.length, false,
                send ? content : null);
    }

    private static HarnessPublishService.PublishedFile text(String path, String content) {
        return file(path, content.getBytes(StandardCharsets.UTF_8), true);
    }

    private HarnessOwnItemService.Sharing visibility(String visibility) {
        return new HarnessOwnItemService.Sharing(visibility, "project".equals(visibility) ? project.id() : null, null);
    }

    private void carry(String key) {
        long revision = harness.project(author, project.id()).project().revision();
        harness.update(author, project.id(), revision, List.of(new HarnessService.ItemChange(key, null, null)),
                List.of());
    }

    private Map<String, HarnessSnapshotService.SnapshotFile> pull(UUID who) {
        return snapshots.snapshot(who, project.id()).files().stream()
                .collect(Collectors.toMap(HarnessSnapshotService.SnapshotFile::path, f -> f));
    }

    @Test
    void aFilesItemLandsEveryFileAtItsOwnPathOnAReadersPull() {
        byte[] image = {(byte) 0x89, 'P', 'N', 'G', 0, 1, 2};
        publish.publish(author, "javadaba.harness", new HarnessPublishService.Publication("files", "Javadaba harness",
                "", null,
                List.of(text(".harness/INDEX.md", "# Index\n"), file(".harness/references/a.png", image, true),
                        text(".claude/rules/architecture.md", "# Architecture\n"))),
                visibility("project"));
        carry("javadaba.harness");

        var files = pull(reader);

        assertThat(files.get(".harness/references/a.png").sha256()).isEqualTo(DeviceTokens.sha256Hex(image));
        assertThat(files.get(".harness/references/a.png").content()).isNull();
        assertThat(snapshots.blob(reader, DeviceTokens.sha256Hex(image))).isEqualTo(image);
        assertThat(files).containsKeys(".harness/INDEX.md", ".claude/rules/architecture.md");
        assertThat(snapshots.snapshot(author, project.id()).files()).isEqualTo(snapshots.snapshot(reader,
                project.id()).files());
    }

    @Test
    void publishingAnUnchangedFolderAgainSendsNoBytesAndMovesTheProjectToTheNewVersion() {
        var index = text(".harness/INDEX.md", "# Index\n");
        publish.publish(author, "javadaba.harness", new HarnessPublishService.Publication("files", null, "", null,
                List.of(index)), visibility("project"));
        carry("javadaba.harness");

        assertThat(publish.missing(List.of(index.sha256()))).isEmpty();
        var again = publish.publish(author, "javadaba.harness", new HarnessPublishService.Publication("files", null, "",
                null, List.of(file(".harness/INDEX.md", "# Index\n".getBytes(StandardCharsets.UTF_8), false),
                        text(".harness/INVARIANTS.md", "# Invariants\n"))),
                null);

        assertThat(again.version()).isEqualTo(2);
        assertThat(pull(reader)).containsKey(".harness/INVARIANTS.md");
    }

    @Test
    void aPathOutsideWhereTheKindMayWriteIsRefusedAndNothingIsSaved() {
        for (String path : List.of("../escape.md", "/etc/passwd", "docs/notes.md", ".harness/fluxor.json",
                ".harness/bin/fluxor-sync.py", ".harness/rules/../../x.md")) {
            assertThatThrownBy(() -> publish.publish(author, "javadaba.bad", new HarnessPublishService.Publication(
                    "files", null, "", null, List.of(text(path, "x"))), visibility("private")))
                    .as(path).isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.code())
                            .isEqualTo("harness_path_refused"));
        }
        assertThat(repo.findItem("javadaba.bad", null)).isEmpty();
    }

    @Test
    void aFileTheStoreLacksMustCarryItsBytesAndThoseBytesMustBeWhatTheyClaim() {
        assertThatThrownBy(() -> publish.publish(author, "javadaba.lost", new HarnessPublishService.Publication(
                "files", null, "", null, List.of(file(".harness/a.md", "a".getBytes(StandardCharsets.UTF_8), false))),
                visibility("private"))).isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("harness_blob_missing"));
        var forged = new HarnessPublishService.PublishedFile(".harness/a.md", "f".repeat(64), 1, false,
                new byte[]{'a'});
        assertThatThrownBy(() -> publish.publish(author, "javadaba.lost", new HarnessPublishService.Publication(
                "files", null, "", null, List.of(forged)), visibility("private")))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.code())
                        .isEqualTo("harness_blob_mismatch"));
    }

    @Test
    void aFileOverOneMegabyteOrAnItemOverSixIsTooLarge() {
        byte[] big = new byte[HarnessPublishService.MAX_FILE + 1];
        assertThatThrownBy(() -> publish.publish(author, "javadaba.big", new HarnessPublishService.Publication("files",
                null, "", null, List.of(file(".harness/big.bin", big, true))), visibility("private")))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(413));
        byte[] chunk = new byte[HarnessPublishService.MAX_FILE];
        List<HarnessPublishService.PublishedFile> seven = java.util.stream.IntStream.range(0, 7)
                .mapToObj(i -> {
                    chunk[0] = (byte) i;
                    return file(".harness/part" + i + ".bin", chunk.clone(), true);
                })
                .toList();
        assertThatThrownBy(() -> publish.publish(author, "javadaba.big", new HarnessPublishService.Publication("files",
                null, "", null, seven), visibility("private")))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(413));
    }

    @Test
    void aPrivateItemsBytesReachOnlyThoseWhoCanSeeIt() {
        byte[] secret = "only mine\n".getBytes(StandardCharsets.UTF_8);
        publish.publish(author, "carlos.notes", new HarnessPublishService.Publication("files", null, "", null,
                List.of(file(".harness/notes.md", secret, true))), visibility("private"));

        assertThat(snapshots.blob(author, DeviceTokens.sha256Hex(secret))).isEqualTo(secret);
        assertThatThrownBy(() -> snapshots.blob(stranger, DeviceTokens.sha256Hex(secret)))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(404));
    }

    @Test
    void aPublishedHookArrivesAsAManifestToConsentToWithItsFallbackStandingIn() {
        publish.publish(author, "javadaba.guard", new HarnessPublishService.Publication("hook", "Guard the shell", "",
                Map.of("event", "preTool", "tools", "shell", "timeoutMs", 5000),
                List.of(text("fallback.md", "Never push to main.\n"), text("hook.sh", "#!/bin/sh\nexit 0\n"))),
                visibility("project"));
        carry("javadaba.guard");

        var files = pull(reader);

        assertThat(files.get(".harness/hooks/javadaba.guard.json").mode()).isEqualTo("hook");
        assertThat(files.get(".harness/hooks/javadaba.guard.sh").executable()).isTrue();
        assertThat(files.get(".harness/rules/javadaba.guard.md").content()).isEqualTo("Never push to main.\n");
        assertThat(files.get("AGENTS.md").content()).contains("@.harness/rules/javadaba.guard.md");
    }

    @Test
    void aPublishedSkillIsAFolderUnderSkills() {
        publish.publish(author, "javadaba.positioning", new HarnessPublishService.Publication("skill", null, "", null,
                List.of(text("SKILL.md", "---\nname: positioning\n---\n"), text("scripts/run.py", "print(1)\n"))),
                visibility("project"));
        carry("javadaba.positioning");

        assertThat(pull(reader)).containsKeys(".harness/skills/javadaba.positioning/SKILL.md",
                ".harness/skills/javadaba.positioning/scripts/run.py");
    }

    // card://JAVA-2011: a workspace's own mod sits beside the market's, named by its card.
    @Test
    void aLocalModPublishedAsAnAtomLandsInTheAtomsLayoutUnderItsCardsName() {
        repo.addItem(new com.javadaba.contexts.fluxor.domain.HarnessItem("atoms", 1,
                com.javadaba.contexts.fluxor.domain.HarnessItemKind.SKILL, "Atoms", "", "# Atoms\n", Map.of(), "test",
                null, null));
        String card = "{\n  \"name\": \"ds-javadaba\",\n  \"description\": \"House design system.\"\n}";
        publish.publish(author, "javadaba.ds-javadaba", new HarnessPublishService.Publication("directive",
                "House design system", "", null, List.of(text("ds-javadaba.md", "# ds-javadaba: House\n")), "mod",
                card), visibility("project"));
        carry("atoms");
        carry("javadaba.ds-javadaba");

        var files = pull(reader);

        assertThat(files.get(".harness/market/mods/ds-javadaba.md").content()).isEqualTo("# ds-javadaba: House\n");
        assertThat(files.get(".harness/market/inventory.json").content()).contains("      \"name\": \"ds-javadaba\",");
        assertThat(files).doesNotContainKey(".harness/rules/javadaba.ds-javadaba.md");
    }

    @Test
    void anAtomWithoutItsCardIsRefused() {
        assertThatThrownBy(() -> publish.publish(author, "javadaba.bare", new HarnessPublishService.Publication(
                "directive", null, "", null, List.of(text("bare.md", "# bare\n")), "mod", null), visibility("private")))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("invalid_harness_item"));
    }

    @Test
    void twoItemsWritingOnePathMakeTheSnapshotRefuseNamingBoth() {
        for (String key : List.of("javadaba.one", "javadaba.two")) {
            publish.publish(author, key, new HarnessPublishService.Publication("files", null, "", null,
                    List.of(text(".harness/INDEX.md", "# " + key + "\n"))), visibility("project"));
            carry(key);
        }

        assertThatThrownBy(() -> snapshots.snapshot(reader, project.id()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.code()).isEqualTo("harness_path_conflict");
                    assertThat(ex.getMessage()).contains("javadaba.one", "javadaba.two");
                });
    }
}
