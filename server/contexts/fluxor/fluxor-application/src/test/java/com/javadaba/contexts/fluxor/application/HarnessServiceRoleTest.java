package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects.Access;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** JAVA-404: a role reads at the version its linked harness project pins, else the newest. */
class HarnessServiceRoleTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final FakeOfficiumProjects officium = new FakeOfficiumProjects();
    private final HarnessService service = new HarnessService(repo, officium);
    private final UUID account = UUID.randomUUID();
    private final UUID board = UUID.randomUUID();

    @Test
    void aBoardWithoutAHarnessReadsTheNewestVersion() {
        repo.addItem(role("code-reviewer", 1));
        repo.addItem(role("code-reviewer", 2));

        Optional<HarnessService.PinnedItem> read = service.pinnedItem(board, "code-reviewer", null);

        assertThat(read).get().satisfies(pinned -> {
            assertThat(pinned.item().version()).isEqualTo(2);
            assertThat(pinned.linked()).isFalse();
        });
    }

    @Test
    void theVersionTheLinkedHarnessPinsWins() {
        officium.grant(account, board, Access.OWNER);
        repo.addItem(role("code-reviewer", 1));
        repo.addItem(role("code-reviewer", 2));
        var project = service.createProject(account, "javadaba", board);
        service.update(account, project.id(), 0,
                List.of(new HarnessService.ItemChange("code-reviewer", 1, null)), List.of());

        Optional<HarnessService.PinnedItem> read = service.pinnedItem(board, "code-reviewer", null);

        assertThat(read).get().satisfies(pinned -> {
            assertThat(pinned.item().version()).isEqualTo(1);
            assertThat(pinned.linked()).isTrue();
        });
    }

    @Test
    void anExplicitVersionIsExactlyThatRowAndNotLinkedWhenNotPinned() {
        officium.grant(account, board, Access.OWNER);
        repo.addItem(role("code-reviewer", 1));
        repo.addItem(role("code-reviewer", 2));
        var project = service.createProject(account, "javadaba", board);
        service.update(account, project.id(), 0,
                List.of(new HarnessService.ItemChange("code-reviewer", 1, null)), List.of());

        Optional<HarnessService.PinnedItem> read = service.pinnedItem(board, "code-reviewer", 2);

        assertThat(read).get().satisfies(pinned -> {
            assertThat(pinned.item().version()).isEqualTo(2);
            assertThat(pinned.linked()).isFalse();
        });
    }

    @Test
    void anUnknownRoleIsEmpty() {
        assertThat(service.pinnedItem(board, "no-such-role", null)).isEmpty();
    }

    private static HarnessItem role(String key, int version) {
        return new HarnessItem(key, version, HarnessItemKind.DIRECTIVE, key + " v" + version, "", "# " + key,
                Map.of("exclusiveGroup", "role"), "test", null, null);
    }
}
