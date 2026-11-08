package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessProject;
import jakarta.enterprise.context.ApplicationScoped;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Sets a project's harness up on the machine an agent runs on (JAVA-162, ADR 0019): the Fluxor
 * MCP's {@code harness.bootstrap}. The MCP cannot write to that disk, so it answers with commands,
 * and the agent runs them: download {@code fluxor-sync} and check its sha256, then {@code init},
 * which trades a one-time code for a device token and pulls.
 *
 * <p>{@link #instructions(Product)} is what an MCP's {@code initialize} tells the agent to do with
 * all this. It is ONE text, so Fluxor's MCP and Officium's (JAVA-563) cannot drift apart. Officium's
 * way in is {@link #setup}, which finds or makes the harness project for an Officium one.
 */
@ApplicationScoped
public class HarnessBootstrapService {

    private final HarnessService harness;
    private final HarnessEnrollmentService enrollments;
    private final HarnessWriter writer;

    public HarnessBootstrapService(HarnessService harness, HarnessEnrollmentService enrollments,
            HarnessWriter writer) {
        this.harness = harness;
        this.enrollments = enrollments;
        this.writer = writer;
    }

    /**
     * Commands that set {@code projectId} up, run from the project's root. 404 for a project the
     * account does not own, before any code is minted.
     *
     * @param apiBase this API's public URL ({@code https://javadaba.com/api}): both the download and
     *     the writer's server
     */
    public Bootstrap bootstrap(UUID accountId, UUID projectId, String apiBase) {
        HarnessProject project = harness.project(accountId, projectId).project();
        HarnessEnrollmentService.Minted code = enrollments.mint(accountId);
        String url = apiBase + HarnessWriter.ROUTE;
        String download = "python3 -c \"import hashlib,pathlib,urllib.request as u;d=u.urlopen(u.Request('" + url
                + "',headers={'User-Agent':'fluxor-sync/1'})).read();assert hashlib.sha256(d).hexdigest()=='"
                + writer.sha256()
                + "','fluxor-sync.py does not match its sha256: not installed';p=pathlib.Path('"
                + HarnessSnapshotService.WRITER + "');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d)\"";
        // `--enroll=<code>`: a base64url code starts with `-` one time in 64, and argparse reads a
        // separate `-...` argument as an option.
        // card://JAVA-2010 (ADR 0038): a harness set up from here is this machine's, kept out of git.
        String init = "python3 " + HarnessSnapshotService.WRITER + " init --enroll=" + code.code() + " --project="
                + project.id() + " --server=" + apiBase + " --storage=local";
        return new Bootstrap(project.id(), project.name(), code.expiresAt(), new Writer(url, writer.sha256()),
                List.of(download, init));
    }

    /**
     * Sets {@code officiumProjectId} up for its harness, for Officium's {@code harness.setup}
     * (JAVA-563), once the user said yes: the account's harness project linked to it (the most
     * recently changed), or a new one named after it; the
     * {@link #OFFICIUM_PRESET}'s missing items added; and the commands {@link #bootstrap} answers.
     * With {@code harnessProjectId}, a project already set up from Fluxor on this machine: the
     * preset on that project, and a pull. Linking a new project is the board owner's alone, and
     * one board has one link (JAVA-406): {@link HarnessService#createProject} refuses otherwise.
     */
    public Setup setup(UUID accountId, UUID officiumProjectId, String officiumProjectName, UUID harnessProjectId,
            String apiBase) {
        if (harnessProjectId != null) {
            HarnessProject project = ensurePresetIfEditable(accountId, harnessProjectId);
            return new Setup(project.id(), project.name(), false, null,
                    List.of("python3 " + HarnessSnapshotService.WRITER + " pull"));
        }
        HarnessProject linked = harness.projects(accountId).stream()
                .map(HarnessService.SharedProject::project)
                .filter(p -> officiumProjectId.equals(p.officiumProjectId()))
                .findFirst()
                .orElse(null);
        HarnessProject project = linked != null
                ? linked
                : harness.createProject(accountId, officiumProjectName, officiumProjectId);
        ensurePresetIfEditable(accountId, project.id());
        Bootstrap bootstrap = bootstrap(accountId, project.id(), apiBase);
        return new Setup(project.id(), project.name(), linked == null, bootstrap.expiresAt(), bootstrap.commands());
    }

    /**
     * A viewer of a shared harness (card://JAVA-2006) sets their machine up to pull it as it is: the
     * preset is added only by someone who may change the project.
     */
    private HarnessProject ensurePresetIfEditable(UUID accountId, UUID projectId) {
        return harness.canEdit(accountId, projectId)
                ? harness.ensurePreset(accountId, projectId, OFFICIUM_PRESET).project()
                : harness.project(accountId, projectId).project();
    }

    /**
     * What an MCP's {@code initialize} tells the agent to do on a project. Only what {@link Product}
     * carries differs between products: the consent, the yes, the no and the approve rule are this
     * one text, word for word, so the two MCPs cannot drift apart.
     *
     * <p>Claude Code keeps only its first 2,048 characters (JAVA-832), so every word here is paid
     * for, and step 5 stays last: a cut drops it first, and the test pins both.
     *
     * <p>The question comes AFTER the user's request, never before it (JAVA-833): an agent will not
     * let a server's instructions put a code-running install ahead of what the user asked, and
     * "ask before other work" was never asked at all, while this order was asked 9 times in 9.
     */
    public static String instructions(Product product) {
        return """
                %1$s works best with a harness: rules, skills and hooks from Fluxor.

                In every session, check whether `.harness/fluxor.json` or `.harness/harness.json` exists \
                at the git root.
                - Exists: set up, or declined. Say nothing about it. If the user says they changed the \
                harness in Fluxor, run `python3 .harness/bin/fluxor-sync.py pull`.
                - Missing: do the user's request first, then end your first answer of the session with \
                step 2's question, once. Step 1 runs only on a yes.
                - "Configure %1$s", in any words, starts at step 2 right away.

                1. %2$s
                2. "%1$s needs to install some skills and hooks so it works correctly with your tools. \
                %3$s Hooks run code on your machine, and fluxor-sync runs at each session start and \
                updates itself from Fluxor. Do you want to continue with the installation? If \
                not, you can resume it at any time by asking me to configure %1$s."
                3. Yes: run the commands step 1's setup operation returns, in order (`python` if no \
                `python3`), then, on that same yes, \
                `python3 .harness/bin/fluxor-sync.py approve --consented --all` to wire the hooks. \
                Say it is set up; hooks take effect next session.
                4. No: write `.harness/fluxor.json` with `{"declined": true}` and do not ask again.
                5. Never run `approve --consented` without the user's yes to those exact hooks. When a \
                pull reports `hook <key> changed` or hooks waiting for consent, run \
                `python3 .harness/bin/fluxor-sync.py approve <key>` (or `--all`), show the user its \
                output, and add `--consented` only if they say yes.
                """.formatted(product.name(), product.findProject(), product.whatGetsInstalled());
    }

    /**
     * What differs between the products whose MCP sets a harness up: the name, how the agent finds
     * the project and which operation sets it up (step 1), and where the user sees what would be
     * installed before saying yes (step 2).
     */
    public record Product(String name, String findProject, String whatGetsInstalled) {
    }

    // Fluxor's question lists the project's items, and it is asked before step 1 finds the project
    // (JAVA-833), so it reads them first: `harness.projects` is read-only and carries them.
    public static final Product FLUXOR = new Product("Fluxor",
            "Query `harness.projects` (none: tell the user to create one in Fluxor, and stop; several: ask "
                    + "which). The setup operation is `harness.bootstrap`, with that project's id.",
            "These would be installed: <list the project's items, read from `harness.projects` before asking, "
                    + "each with what it does, and say which are hooks>.");

    /** The public page of what Officium's setup installs, read from its preset (JAVA-676). */
    public static final String OFFICIUM_SETUP_PAGE = "https://javadaba.com/developers/docs/officium-mcp/setup";

    public static final Product OFFICIUM = new Product("Officium",
            "Take `project.id` from `.harness/config/backlog.json`, else `projects.list` "
                    + "(none: tell the user to create one at https://javadaba.com/officium/app, and stop; several: "
                    + "ask which). The setup operation is `harness.setup`: that `projectId`, plus `harnessProjectId` "
                    + "when `.harness/fluxor.json` names one.",
            "You can see everything that will be installed, and what each piece does, on the support page: "
                    + OFFICIUM_SETUP_PAGE + ".");

    /** The preset Officium's setup adds, from Fluxor's market (JAVA-161). */
    static final String OFFICIUM_PRESET = "officium";

    public record Writer(String url, String sha256) {
    }

    public record Bootstrap(UUID projectId, String projectName, Instant expiresAt, Writer writer,
            List<String> commands) {
    }

    /** {@code expiresAt} is the enrollment code's, null when none was minted (a pull only). */
    public record Setup(UUID harnessProjectId, String harnessProjectName, boolean created, Instant expiresAt,
            List<String> commands) {
    }
}
