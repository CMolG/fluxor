package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.FluxorException;
import com.javadaba.contexts.fluxor.domain.ports.OfficiumProjects.Access;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** JAVA-406: only an Officium project's owner links a harness project to it, and only one is linked. */
class HarnessServiceOfficiumLinkTest {

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final FakeOfficiumProjects officium = new FakeOfficiumProjects();
    private final HarnessService service = new HarnessService(repo, officium);
    private final UUID account = UUID.randomUUID();
    private final UUID board = UUID.randomUUID();

    @Test
    void theOwnerLinksAHarnessProjectToTheBoard() {
        officium.grant(account, board, Access.OWNER);

        var project = service.createProject(account, "javadaba", board);

        assertThat(project.officiumProjectId()).isEqualTo(board);
        assertThat(service.projects(account)).extracting(s -> s.project().officiumProjectId()).containsExactly(board);
    }

    @Test
    void aMemberWhoDoesNotOwnTheBoardIsRefused() {
        officium.grant(account, board, Access.EDITOR);

        assertThatThrownBy(() -> service.createProject(account, "javadaba", board))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.httpStatus()).isEqualTo(403);
                    assertThat(ex.code()).isEqualTo("officium_project_owner_required");
                });
        assertThat(service.projects(account)).isEmpty();
    }

    @Test
    void aBoardTheCallerCannotSeeIsNotFound() {
        officium.grant(account, board, Access.NONE);

        assertThatThrownBy(() -> service.createProject(account, "javadaba", board))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.httpStatus()).isEqualTo(404);
                    assertThat(ex.code()).isEqualTo("officium_project_not_found");
                });
        assertThat(service.projects(account)).isEmpty();
    }

    @Test
    void aSecondHarnessProjectCannotLinkTheSameBoard() {
        service.createProject(account, "first", board);

        assertThatThrownBy(() -> service.createProject(account, "second", board))
                .isInstanceOfSatisfying(FluxorException.class, ex -> {
                    assertThat(ex.httpStatus()).isEqualTo(409);
                    assertThat(ex.code()).isEqualTo("officium_project_already_linked");
                });
        assertThat(service.projects(account)).hasSize(1);
    }

    @Test
    void aProjectWithNoBoardNeedsNoOfficiumAnswer() {
        UUID stranger = UUID.randomUUID();
        officium.grant(stranger, board, Access.NONE);

        assertThat(service.createProject(stranger, "standalone", null).officiumProjectId()).isNull();
        assertThat(service.createProject(stranger, "another", null).officiumProjectId()).isNull();
    }
}
