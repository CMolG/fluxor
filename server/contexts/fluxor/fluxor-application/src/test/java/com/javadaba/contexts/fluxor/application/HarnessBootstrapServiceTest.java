package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.application.HarnessBootstrapService.Product;
import org.junit.jupiter.api.Test;

import static com.javadaba.contexts.fluxor.application.HarnessBootstrapService.FLUXOR;
import static com.javadaba.contexts.fluxor.application.HarnessBootstrapService.OFFICIUM;
import static com.javadaba.contexts.fluxor.application.HarnessBootstrapService.instructions;
import static org.assertj.core.api.Assertions.assertThat;

/** JAVA-563: Fluxor's MCP and Officium's tell an agent the same thing, but for what a product is. */
class HarnessBootstrapServiceTest {

    @Test
    void bothProductsShareEveryWordButWhatTheirProductCarries() {
        // The shared text names Fluxor itself (where a harness is chosen), so Officium's name is
        // mapped onto Fluxor's rather than both onto a placeholder.
        assertThat(neutral(OFFICIUM).replace(OFFICIUM.name(), FLUXOR.name())).isEqualTo(neutral(FLUXOR));
    }

    @Test
    void officiumAsksWithTheUsersWordsAndPointsAtTheSupportPage() {
        String text = instructions(OFFICIUM);

        assertThat(text).contains("\"Officium needs to install some skills and hooks so it works correctly with "
                + "your tools. You can see everything that will be installed, and what each piece does, on the "
                + "support page: https://javadaba.com/developers/docs/officium-mcp/setup.")
                .contains("Do you want to continue with the installation? If not, you can resume it at any time "
                        + "by asking me to configure Officium.\"")
                .contains("`harness.setup`", "`harnessProjectId`", "\"Configure Officium\"")
                .doesNotContain("harness.bootstrap");
    }

    @Test
    void fluxorListsTheProjectsItemsAndBootstraps() {
        assertThat(instructions(FLUXOR)).contains("`harness.bootstrap`", "<list the project's items")
                .doesNotContain("harness.setup");
    }

    @Test
    void theConsentTheDeclineAndTheApproveRuleAreInEveryProductsText() {
        for (Product product : new Product[]{FLUXOR, OFFICIUM}) {
            // JAVA-625: the writer is code too, and it updates itself with no per-hash consent.
            assertThat(instructions(product)).contains("Hooks run code on your machine, and fluxor-sync runs at "
                    + "each session start and updates itself from Fluxor.",
                    "`{\"declined\": true}`", "approve --consented --all",
                    "Never run `approve --consented` without the user's yes to those exact hooks.");
        }
    }

    /**
     * JAVA-1116: a harness installed from a local catalog ({@code marketplace.py install}) has
     * {@code .harness/harness.json} and no {@code fluxor.json}, and {@code fluxor-sync init} refuses
     * it. Checking only {@code fluxor.json}, the agent asked to install a harness that was already
     * there, and a yes could not succeed.
     */
    @Test
    void aHarnessFromALocalCatalogCountsAsSetUp() {
        for (Product product : new Product[]{FLUXOR, OFFICIUM}) {
            assertThat(instructions(product)).as(product.name())
                    .contains("`.harness/fluxor.json` or `.harness/harness.json` exists");
        }
    }

    /**
     * JAVA-833: asked "before other work", an agent did the user's task and never asked (0 in 6); asked
     * at the end of its first answer, it asked every time (9 in 9). The question waits for the request,
     * and the project is looked up only once the user said yes.
     */
    @Test
    void theQuestionEndsTheFirstAnswerAfterTheUsersRequest() {
        for (Product product : new Product[]{FLUXOR, OFFICIUM}) {
            assertThat(instructions(product)).as(product.name())
                    .contains(
                            "In every session, check whether `.harness/fluxor.json` or `.harness/harness.json` exists",
                            "- Exists: set up, or declined. Say nothing about it.",
                            "- Missing: do the user's request first, then end your first answer of the session "
                                    + "with step 2's question, once. Step 1 runs only on a yes.",
                            "\"Configure " + product.name() + "\", in any words, starts at step 2 right away.",
                            "1. " + product.findProject(),
                            "2. \"" + product.name() + " needs to install")
                    .doesNotContain("before other work");
        }
    }

    /**
     * Claude Code keeps only the first 2,048 characters of an MCP server's {@code instructions} and
     * appends "… [truncated]" (measured with 2.1.288 in JAVA-696's walk): at 2,227, Officium's text lost
     * step 6's rule for a changed hook (JAVA-832).
     */
    private static final int CLAUDE_CODE_INSTRUCTIONS_LIMIT = 2_048;

    /** Room for a reworded step before the limit cuts the last one again (117 left after JAVA-833). */
    private static final int HEADROOM = 100;

    @Test
    void everyProductsTextFitsWhatClaudeCodeKeepsWithStepFiveLast() {
        for (Product product : new Product[]{FLUXOR, OFFICIUM}) {
            String text = instructions(product);

            assertThat(text.length()).as(product.name()).isLessThanOrEqualTo(
                    CLAUDE_CODE_INSTRUCTIONS_LIMIT - HEADROOM);
            // The tail a cut drops first is the consent rule for a changed hook (ADR 0020).
            assertThat(text).as(product.name()).contains("approve <key>`")
                    .endsWith("add `--consented` only if they say yes.\n");
        }
    }

    /** The text with the product's two passages blanked out: what is left is shared, but for the name. */
    private static String neutral(Product product) {
        return instructions(product)
                .replace(product.findProject(), "<find>")
                .replace(product.whatGetsInstalled(), "<what>");
    }
}
