package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessAccess;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.Pack;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects.Access;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.tuple;

/**
 * card://JAVA-2006: a harness project linked to an Officium project is read and pulled by that
 * project's people, and changed by its owners and editors; nobody else learns it exists.
 */
class HarnessServiceSharingTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final FakeOfficiumProjects officium = new FakeOfficiumProjects();
    private final HarnessService service = new HarnessService(repo, officium);
    private final FakePackRepository packs = new FakePackRepository();
    private final HarnessSnapshotService snapshots = new HarnessSnapshotService(service, repo, new HarnessWriter(),
            packs);
    private final UUID owner = UUID.randomUUID();
    private final UUID viewer = UUID.randomUUID();
    private final UUID editor = UUID.randomUUID();
    private final UUID stranger = UUID.randomUUID();
    private final UUID board = UUID.randomUUID();
    private HarnessProject project;

    @BeforeEach
    void setUp() {
        repo.addItem(new HarnessItem("english", 1, HarnessItemKind.DIRECTIVE, "English everywhere", "",
                "Everything is English.\n", Map.of("activation", "always"), "test", null, null));
        repo.addItem(new HarnessItem("review-diff", 1, HarnessItemKind.SKILL, "Review a diff", "",
                "# Review a diff\n", Map.of(), "test", null, null));
        officium.grant(owner, board, Access.OWNER);
        officium.grant(viewer, board, Access.VIEWER);
        officium.grant(editor, board, Access.EDITOR);
        officium.grant(stranger, board, Access.NONE);
        officium.name(board, "Javadaba, the Officium project with a name long enough to wrap twice on a phone");
        project = service.createProject(owner, "javadaba-webpage", board);
        project = service.update(owner, project.id(), 0,
                List.of(new HarnessService.ItemChange("english", null, null)), List.of()).project();
    }

    @Test
    void aViewerOfTheLinkedBoardListsTheProjectAsSharedThroughIt() {
        assertThat(service.projects(viewer))
                .extracting(s -> s.project().id(), HarnessService.SharedProject::access,
                        HarnessService.SharedProject::sharedThrough)
                .containsExactly(tuple(project.id(), HarnessAccess.VIEWER,
                        "Javadaba, the Officium project with a name long enough to wrap twice on a phone"));
        assertThat(service.projects(owner)).extracting(HarnessService.SharedProject::access,
                HarnessService.SharedProject::sharedThrough).containsExactly(tuple(HarnessAccess.OWNER, null));
    }

    @Test
    void aViewerPullsTheSameFilesAsTheOwner() {
        assertThat(snapshots.snapshot(viewer, project.id()).files())
                .isEqualTo(snapshots.snapshot(owner, project.id()).files());
        assertThat(service.changes(viewer, project.id(), 0).changed()).hasSize(1);
    }

    @Test
    void aViewerCannotChangeTheItems() {
        assertThatThrownBy(() -> service.update(viewer, project.id(), project.revision(),
                List.of(new HarnessService.ItemChange("review-diff", null, null)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.httpStatus()).isEqualTo(403);
                    assertThat(ex.code()).isEqualTo("harness_project_read_only");
                });
        assertThat(service.canEdit(viewer, project.id())).isFalse();
        assertThat(service.project(owner, project.id()).items()).hasSize(1);
    }

    @Test
    void anEditorChangesTheItemsAndBumpsTheRevision() {
        var changed = service.update(editor, project.id(), project.revision(),
                List.of(new HarnessService.ItemChange("review-diff", null, null)), List.of());

        assertThat(changed.project().revision()).isEqualTo(project.revision() + 1);
        assertThat(changed.access()).isEqualTo(HarnessAccess.EDITOR);
        assertThat(service.canEdit(editor, project.id())).isTrue();
    }

    @Test
    void someoneWithNoAccessToTheBoardIsAnsweredNotFoundEverywhere() {
        assertThat(service.projects(stranger)).isEmpty();
        for (Runnable read : List.<Runnable>of(
                () -> service.project(stranger, project.id()),
                () -> service.changes(stranger, project.id(), 0),
                () -> snapshots.snapshot(stranger, project.id()),
                () -> service.update(stranger, project.id(), project.revision(), List.of(), List.of()))) {
            assertThatThrownBy(read::run).isInstanceOfSatisfying(FluxorException.class,
                    ex -> assertThat(ex.httpStatus()).isEqualTo(404));
        }
    }

    @Test
    void anUnlinkedProjectStaysItsOwnersAlone() {
        HarnessProject mine = service.createProject(owner, "scratch", null);

        assertThat(service.projects(viewer)).extracting(s -> s.project().id()).doesNotContain(mine.id());
        assertThatThrownBy(() -> service.project(viewer, mine.id())).isInstanceOfSatisfying(FluxorException.class,
                ex -> assertThat(ex.httpStatus()).isEqualTo(404));
    }

    @Test
    void theOwnersPackDoesNotTravelToAReader() {
        String core = "# core\n";
        packs.publish(new Pack(UUID.randomUUID(), owner, PackServiceTest.PACK_ID, PackServiceTest.ROLE, "2.0.0",
                "1.0.0", "ceet-consent-2", Instant.now(),
                List.of(new Pack.File("core.md", DeviceTokens.sha256Hex(core), core))), project.id());

        assertThat(snapshots.snapshot(owner, project.id(), true).files())
                .anyMatch(f -> f.path().startsWith(".harness/packs/"));
        assertThat(snapshots.snapshot(viewer, project.id(), true).files())
                .noneMatch(f -> f.path().startsWith(".harness/packs/"));
    }
}
