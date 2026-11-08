package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects.Access;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * card://JAVA-2008: a person saves a project's harness as a preset of their own, with a visibility,
 * and applies it to other projects; what the applier cannot see is named and skipped.
 */
class HarnessSavedPresetTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final FakeOfficiumProjects officium = new FakeOfficiumProjects();
    private final HarnessService harness = new HarnessService(repo, officium);
    private final HarnessOwnItemService items = new HarnessOwnItemService(harness, repo, repo);
    private final UUID author = UUID.randomUUID();
    private final UUID colleague = UUID.randomUUID();
    private final UUID stranger = UUID.randomUUID();
    private final UUID board = UUID.randomUUID();
    private HarnessProject source;

    @BeforeEach
    void setUp() {
        IntStream.range(0, 11).forEach(i -> repo.addItem(new HarnessItem("rule-" + i, 1, HarnessItemKind.DIRECTIVE,
                "Rule " + i, "", "Rule " + i + ".\n", Map.of("activation", "always"), "test", null, null)));
        officium.grant(author, board, Access.OWNER);
        officium.owner(board, author);
        officium.grant(colleague, board, Access.VIEWER);
        officium.grant(stranger, board, Access.NONE);
        source = harness.createProject(author, "website", null);
        List<HarnessService.ItemChange> eleven = IntStream.range(0, 11)
                .mapToObj(
                        i -> new HarnessService.ItemChange("rule-" + i, null, i == 0 ? Map.of("MODE", "strict") : null))
                .toList();
        harness.update(author, source.id(), 0, eleven, List.of());
        items.createDirective(author, "carlos.notes", new HarnessOwnItemService.Directive("Notes", "", "Mine.",
                "always", null), new HarnessOwnItemService.Sharing("private", null, null));
        harness.update(author, source.id(), 1, List.of(new HarnessService.ItemChange("carlos.notes", null, null)),
                List.of());
    }

    private HarnessItem save(String visibility) {
        return items.saveAsPreset(author, source.id(), "carlos.web-harness", "My web harness", "What I use on sites",
                new HarnessOwnItemService.Sharing(visibility, null, null));
    }

    @Test
    void aSavedHarnessAppliedToAnEmptyProjectCarriesTheSameItemsAndParams() {
        save("private");
        HarnessProject empty = harness.createProject(author, "blog", null);

        var applied = harness.applyPreset(author, empty.id(), "carlos.web-harness", 0);

        assertThat(applied.items()).extracting(e -> e.item().itemKey())
                .containsExactlyInAnyOrderElementsOf(harness.project(author, source.id()).items().stream()
                        .map(e -> e.item().itemKey()).toList());
        assertThat(applied.items()).filteredOn(e -> e.item().itemKey().equals("rule-0"))
                .extracting(e -> e.item().params()).containsExactly(Map.of("MODE", "strict"));
        assertThat(applied.items()).filteredOn(e -> e.item().itemKey().equals("carlos.notes"))
                .allMatch(e -> e.item().followsLatest());
    }

    @Test
    void anOrganizationHarnessIsSeenAndAppliedByAColleagueAndNotByAStranger() {
        save("organization");
        HarnessProject theirs = harness.createProject(colleague, "theirs", null);

        assertThat(items.catalog(colleague, HarnessItemKind.PRESET)).extracting(HarnessItem::key)
                .contains("carlos.web-harness");
        assertThat(items.catalog(stranger, HarnessItemKind.PRESET)).extracting(HarnessItem::key)
                .doesNotContain("carlos.web-harness");
        assertThat(harness.applyPreset(colleague, theirs.id(), "carlos.web-harness", 0).items()).hasSize(11);
    }

    @Test
    void aPrivateItemOfTheAuthorIsNamedAsSkippedWhenSomeoneElseAppliesIt() {
        save("organization");
        HarnessProject theirs = harness.createProject(colleague, "theirs", null);

        assertThat(harness.presetSkips(colleague, "carlos.web-harness")).containsExactly("carlos.notes");
        assertThat(harness.applyPreset(colleague, theirs.id(), "carlos.web-harness", 0).items())
                .extracting(e -> e.item().itemKey()).doesNotContain("carlos.notes");
        assertThat(harness.presetSkips(author, "carlos.web-harness")).isEmpty();
    }

    @Test
    void savingAgainIsTheNextVersionAndAProjectThatAppliedItKeepsItsItems() {
        save("private");
        HarnessProject applied = harness.createProject(author, "blog", null);
        harness.applyPreset(author, applied.id(), "carlos.web-harness", 0);
        harness.update(author, source.id(), 2, List.of(), List.of("rule-10"));

        assertThat(save("private").version()).isEqualTo(2);
        assertThat(harness.project(author, applied.id()).items()).hasSize(12);
    }
}
