package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects.Access;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * card://JAVA-750: a person writes their own directives, each private, project, organization or
 * public (the owner's decision of 2026-11-03), edits them as new versions that the projects following
 * them move to, and retires them; everyone else sees exactly what the visibility allows.
 */
class HarnessOwnItemServiceTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final FakeOfficiumProjects officium = new FakeOfficiumProjects();
    private final HarnessService harness = new HarnessService(repo, officium);
    private final HarnessOwnItemService items = new HarnessOwnItemService(harness, repo, repo);
    private final HarnessSnapshotService snapshots = new HarnessSnapshotService(harness, repo, new HarnessWriter(),
            new FakePackRepository());
    private final UUID author = UUID.randomUUID();
    private final UUID reader = UUID.randomUUID();
    private final UUID stranger = UUID.randomUUID();
    private final UUID board = UUID.randomUUID();
    private HarnessProject shared;

    @BeforeEach
    void setUp() {
        repo.addItem(new HarnessItem("english", 1, HarnessItemKind.DIRECTIVE, "English", "", "English.\n",
                Map.of("activation", "always"), "test", null, null));
        officium.grant(author, board, Access.OWNER);
        officium.owner(board, author);
        officium.grant(reader, board, Access.VIEWER);
        officium.grant(stranger, board, Access.NONE);
        shared = harness.createProject(author, "javadaba", board);
    }

    private HarnessItem write(UUID who, String key, String visibility, UUID project) {
        return items.createDirective(who, key, new HarnessOwnItemService.Directive("Rule " + key, "",
                "Follow " + key + ".", "always", null), new HarnessOwnItemService.Sharing(visibility, project, null));
    }

    private void carry(String key, Integer version) {
        long revision = harness.project(author, shared.id()).project().revision();
        harness.update(author, shared.id(), revision, List.of(new HarnessService.ItemChange(key, version, null)),
                List.of());
    }

    private List<String> paths(UUID who) {
        return snapshots.snapshot(who, shared.id()).files().stream().map(HarnessSnapshotService.SnapshotFile::path)
                .toList();
    }

    private List<String> catalogKeys(UUID who) {
        return items.catalog(who, null).stream().map(HarnessItem::key).toList();
    }

    @Test
    void aPrivateDirectiveRidesOnlyInItsAuthorsSnapshot() {
        write(author, "carlos.notes", "private", null);
        carry("carlos.notes", null);

        assertThat(paths(author)).contains(".harness/rules/carlos.notes.md");
        assertThat(paths(reader)).doesNotContain(".harness/rules/carlos.notes.md");
        assertThat(harness.project(reader, shared.id()).items()).extracting(e -> e.item().itemKey())
                .doesNotContain("carlos.notes");
        assertThat(catalogKeys(reader)).doesNotContain("carlos.notes");
    }

    @Test
    void aProjectDirectiveIsSeenByThePeopleOfThatProjectOnly() {
        write(author, "team.review", "project", shared.id());
        carry("team.review", null);

        assertThat(paths(reader)).contains(".harness/rules/team.review.md");
        assertThat(catalogKeys(reader)).contains("team.review");
        assertThat(catalogKeys(stranger)).doesNotContain("team.review");
        assertThatThrownBy(() -> write(reader, "reader.rule", "project", shared.id()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.code())
                        .isEqualTo("harness_project_not_editable"));
    }

    @Test
    void anOrganizationDirectiveIsSeenByEveryoneWithAccessToTheOwnersProjects() {
        write(author, "acme.style", "organization", null);

        assertThat(catalogKeys(author)).contains("acme.style");
        assertThat(catalogKeys(reader)).contains("acme.style");
        assertThat(catalogKeys(stranger)).doesNotContain("acme.style");
    }

    @Test
    void aPublicDirectiveIsSeenByEveryoneAndChangedOnlyByItsAuthor() {
        write(author, "carlos.public", "public", null);

        assertThat(catalogKeys(stranger)).contains("carlos.public").contains("english");
        for (Runnable change : List.<Runnable>of(
                () -> items.newVersion(stranger, "carlos.public",
                        new HarnessOwnItemService.Directive("Mine now", "", "Mine.", "always", null)),
                () -> items.share(stranger, "carlos.public", null, true))) {
            assertThatThrownBy(change::run).isInstanceOfSatisfying(FluxorException.class, ex -> {
                assertThat(ex.httpStatus()).isEqualTo(403);
                assertThat(ex.code()).isEqualTo("harness_item_not_yours");
            });
        }
    }

    @Test
    void aKeyWithoutADotOrOneTakenIsRefusedAndNothingIsSaved() {
        assertThatThrownBy(() -> write(author, "english", "private", null))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(422));
        write(author, "team.rule", "private", null);
        assertThatThrownBy(() -> write(stranger, "team.rule", "public", null))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.httpStatus()).isEqualTo(409);
                    assertThat(ex.code()).isEqualTo("harness_item_key_taken");
                });
        assertThat(items.item(author, "team.rule", null).ownership().ownerAccountId()).isEqualTo(author);
    }

    @Test
    void aNewVersionReachesTheProjectsThatFollowItAndNotThePinnedOnes() {
        write(author, "team.follow", "project", shared.id());
        write(author, "team.pinned", "project", shared.id());
        carry("team.follow", null);
        carry("team.pinned", 1);
        long before = harness.project(author, shared.id()).project().revision();

        items.newVersion(author, "team.follow", new HarnessOwnItemService.Directive("Rule v2", "", "Follow v2.",
                "always", null));
        items.newVersion(author, "team.pinned", new HarnessOwnItemService.Directive("Rule v2", "", "Pinned v2.",
                "always", null));

        var now = harness.project(reader, shared.id());
        assertThat(now.project().revision()).isEqualTo(before + 1);
        assertThat(now.items()).extracting(e -> e.item().itemKey() + "@" + e.item().itemVersion())
                .contains("team.follow@2", "team.pinned@1");
        assertThat(snapshots.snapshot(reader, shared.id()).files()).filteredOn(
                f -> f.path().equals(".harness/rules/team.follow.md")).extracting(f -> f.content())
                .containsExactly("Follow v2.\n");
    }

    @Test
    void aRetiredDirectiveStaysWhereItIsAndJoinsNoNewProject() {
        write(author, "team.old", "public", null);
        carry("team.old", null);
        items.share(author, "team.old", null, true);
        HarnessProject other = harness.createProject(author, "other", null);

        assertThat(paths(author)).contains(".harness/rules/team.old.md");
        assertThat(catalogKeys(stranger)).doesNotContain("team.old");
        assertThat(items.item(author, "team.old", null).ownership().retired()).isTrue();
        assertThatThrownBy(() -> harness.update(author, other.id(), 0,
                List.of(new HarnessService.ItemChange("team.old", null, null)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.code())
                        .isEqualTo("harness_item_retired"));
    }

    @Test
    void anItemTheEditorCannotSeeIsAnsweredLikeOneThatDoesNotExist() {
        write(stranger, "stranger.secret", "private", null);

        assertThatThrownBy(() -> carry("stranger.secret", null)).isInstanceOfSatisfying(FluxorException.class,
                ex -> assertThat(ex.code()).isEqualTo("unknown_harness_item"));
        assertThatThrownBy(() -> items.item(author, "stranger.secret", null))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(404));
    }
}
