package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.tuple;

/** JAVA-157: a project's harness moves one revision per effective change, and a client that knows
 *  revision N gets only what changed after it. */
class HarnessServiceTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final HarnessService service = new HarnessService(repo, new FakeOfficiumProjects());
    private final UUID account = UUID.randomUUID();
    private HarnessProject project;

    @BeforeEach
    void setUp() {
        repo.addItem(item("backlog", 1, HarnessItemKind.SKILL, Map.of()));
        repo.addItem(item("backlog", 2, HarnessItemKind.SKILL, Map.of()));
        repo.addItem(item("english", 1, HarnessItemKind.DIRECTIVE, Map.of()));
        repo.addItem(item("final-cycle", 1, HarnessItemKind.HOOK, Map.of("fallback", "Report what was tested.")));
        repo.addItem(item("officium", 1, HarnessItemKind.PRESET, Map.of("items", List.of(
                Map.of("key", "backlog", "params", Map.of("OFFICIUM_PROJECT_ID", "p-1")),
                Map.of("key", "english", "version", 1)))));
        project = service.createProject(account, "  javadaba-webpage ", null);
    }

    @Test
    void aNewProjectIsEmptyAtRevisionZero() {
        assertThat(project.name()).isEqualTo("javadaba-webpage");
        assertThat(project.revision()).isZero();
        assertThat(service.project(account, project.id()).items()).isEmpty();
    }

    @Test
    void theCatalogListsTheNewestVersionOfEachKey() {
        assertThat(service.catalog(null)).extracting(HarnessItem::key, HarnessItem::version)
                .containsExactly(
                        tuple("backlog", 2),
                        tuple("english", 1),
                        tuple("final-cycle", 1),
                        tuple("officium", 1));
        assertThat(service.catalog(HarnessItemKind.HOOK)).extracting(HarnessItem::key).containsExactly("final-cycle");
    }

    @Test
    void anItemPutWithoutAVersionTakesTheNewest() {
        var harness = service.update(account, project.id(), 0, List.of(put("backlog", null)), List.of());

        assertThat(harness.project().revision()).isEqualTo(1);
        assertThat(harness.items()).singleElement()
                .satisfies(e -> assertThat(e.item().itemVersion()).isEqualTo(2));
    }

    @Test
    void oneChangeWithManyItemsIsOneRevision() {
        var harness = service.update(account, project.id(), 0,
                List.of(put("backlog", 1), put("english", null), put("final-cycle", null)), List.of());

        assertThat(harness.project().revision()).isEqualTo(1);
        assertThat(harness.items()).hasSize(3);
    }

    @Test
    void aChangeThatChangesNothingDoesNotBumpTheRevision() {
        service.update(account, project.id(), 0, List.of(put("backlog", 2)), List.of());

        var again = service.update(account, project.id(), 1, List.of(put("backlog", 2)), List.of("english"));

        assertThat(again.project().revision()).isEqualTo(1);
        assertThat(repo.commits).isEqualTo(1);
    }

    @Test
    void aStaleRevisionIsAConflictAndWritesNothing() {
        assertThatThrownBy(() -> service.update(account, project.id(), 3, List.of(put("backlog", null)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.code()).isEqualTo("harness_revision_conflict");
                    assertThat(ex.httpStatus()).isEqualTo(409);
                });
        assertThat(repo.commits).isZero();
    }

    @Test
    void aClientThatMovedTheProjectBetweenOurReadAndOurWriteIsAConflict() {
        repo.bumpBehindTheServicesBack(project.id());

        assertThatThrownBy(() -> service.update(account, project.id(), 0, List.of(put("backlog", null)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("harness_revision_conflict"));
    }

    @Test
    void anItemTheCatalogDoesNotHaveIsRejected() {
        assertThatThrownBy(() -> service.update(account, project.id(), 0, List.of(put("backlog", 9)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.code()).isEqualTo("unknown_harness_item");
                    assertThat(ex.httpStatus()).isEqualTo(422);
                });
    }

    @Test
    void aPresetIsAppliedNeverAdded() {
        assertThatThrownBy(() -> service.update(account, project.id(), 0, List.of(put("officium", null)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("harness_item_is_preset"));
    }

    @Test
    void aKeyAppearsOncePerChange() {
        assertThatThrownBy(() -> service.update(account, project.id(), 0, List.of(put("backlog", null)),
                List.of("backlog")))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("invalid_harness_change"));
    }

    @Test
    void applyingAPresetAddsItsItemsWithTheirParamsAsOneRevision() {
        var harness = service.applyPreset(account, project.id(), "officium", 0);

        assertThat(harness.project().revision()).isEqualTo(1);
        assertThat(harness.items()).extracting(e -> e.item().itemKey()).containsExactly("backlog", "english");
        assertThat(harness.items().get(0).item().params()).isEqualTo(Map.of("OFFICIUM_PROJECT_ID", "p-1"));
    }

    @Test
    void onlyAPresetCanBeApplied() {
        assertThatThrownBy(() -> service.applyPreset(account, project.id(), "backlog", 0))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("harness_item_not_preset"));
    }

    /** card://JAVA-563: setting a machine up never re-versions what the owner pinned in Fluxor. */
    @Test
    void ensuringAPresetAddsOnlyTheItemsTheProjectLacks() {
        service.update(account, project.id(), 0, List.of(put("backlog", 1)), List.of());

        var harness = service.ensurePreset(account, project.id(), "officium");

        assertThat(harness.project().revision()).isEqualTo(2);
        assertThat(harness.items()).extracting(e -> e.item().itemKey(), e -> e.item().itemVersion(),
                e -> e.item().params())
                .containsExactlyInAnyOrder(tuple("backlog", 1, Map.of()), tuple("english", 1, Map.of()));
    }

    @Test
    void ensuringAPresetTheProjectAlreadyCarriesChangesNothing() {
        service.ensurePreset(account, project.id(), "officium");

        assertThat(service.ensurePreset(account, project.id(), "officium").project().revision()).isEqualTo(1);
        assertThatThrownBy(() -> service.ensurePreset(account, project.id(), "backlog"))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("harness_item_not_preset"));
    }

    /** card://JAVA-676: the public read lists what applying the preset adds, item for item. */
    @Test
    void aPresetReadsAsTheItemsApplyingItAdds() {
        var contents = service.preset("officium");
        var applied = service.applyPreset(account, project.id(), "officium", 0);

        assertThat(contents.preset().key()).isEqualTo("officium");
        assertThat(contents.items()).extracting(HarnessItem::key, HarnessItem::version)
                .containsExactlyElementsOf(applied.items().stream()
                        .map(e -> tuple(e.item().itemKey(), e.item().itemVersion())).toList());
        assertThat(contents.items()).extracting(HarnessItem::key, HarnessItem::version)
                .containsExactly(tuple("backlog", 2), tuple("english", 1));
    }

    @Test
    void onlyAPresetIsReadPublicly() {
        for (String key : List.of("backlog", "nothing-by-this-name")) {
            assertThatThrownBy(() -> service.preset(key)).as(key)
                    .isInstanceOfSatisfying(FluxorException.class, ex -> {
                        assertThat(ex.code()).isEqualTo("harness_preset_not_found");
                        assertThat(ex.httpStatus()).isEqualTo(404);
                    });
        }
    }

    @Test
    void changesSinceARevisionAreOnlyWhatCameAfterIt() {
        service.update(account, project.id(), 0, List.of(put("backlog", 1), put("english", null)), List.of());
        service.update(account, project.id(), 1, List.of(put("backlog", 2)), List.of());
        service.update(account, project.id(), 2, List.of(put("final-cycle", null)), List.of("english"));

        var changes = service.changes(account, project.id(), 1);

        assertThat(changes.full()).isFalse();
        assertThat(changes.project().revision()).isEqualTo(3);
        assertThat(changes.changed()).extracting(e -> e.item().itemKey(), e -> e.item().itemVersion())
                .containsExactly(
                        tuple("backlog", 2),
                        tuple("final-cycle", 1));
        assertThat(changes.removed()).containsExactly("english");
        assertThat(service.changes(account, project.id(), 3).changed()).isEmpty();
    }

    @Test
    void noRevisionOrAnUnreachedOneGetsTheWholeHarness() {
        service.update(account, project.id(), 0, List.of(put("backlog", null), put("english", null)), List.of());
        service.update(account, project.id(), 1, List.of(), List.of("english"));

        for (long since : new long[]{0, 42}) {
            var changes = service.changes(account, project.id(), since);
            assertThat(changes.full()).isTrue();
            assertThat(changes.changed()).extracting(e -> e.item().itemKey()).containsExactly("backlog");
            assertThat(changes.removed()).isEmpty();
        }
    }

    @Test
    void aRemovedItemCanComeBack() {
        service.update(account, project.id(), 0, List.of(put("english", null)), List.of());
        service.update(account, project.id(), 1, List.of(), List.of("english"));

        var harness = service.update(account, project.id(), 2, List.of(put("english", null)), List.of());

        assertThat(harness.items()).extracting(e -> e.item().itemKey()).containsExactly("english");
        assertThat(service.changes(account, project.id(), 2).changed()).hasSize(1);
    }

    @Test
    void anotherAccountsProjectIsNotFound() {
        UUID stranger = UUID.randomUUID();
        assertThatThrownBy(() -> service.project(stranger, project.id()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(404));
        assertThatThrownBy(() -> service.update(stranger, project.id(), 0, List.of(put("backlog", null)), List.of()))
                .isInstanceOfSatisfying(FluxorException.class, ex -> assertThat(ex.httpStatus()).isEqualTo(404));
        assertThat(service.projects(stranger)).isEmpty();
    }

    @Test
    void aProjectNeedsAName() {
        assertThatThrownBy(() -> service.createProject(account, " ", null))
                .isInstanceOfSatisfying(FluxorException.class,
                        ex -> assertThat(ex.code()).isEqualTo("invalid_harness_project_name"));
    }

    private static HarnessService.ItemChange put(String key, Integer version) {
        return new HarnessService.ItemChange(key, version, null);
    }

    private static HarnessItem item(String key, int version, HarnessItemKind kind, Map<String, Object> spec) {
        return new HarnessItem(key, version, kind, key + " v" + version, "", "# " + key, spec, "test", null, null);
    }
}
