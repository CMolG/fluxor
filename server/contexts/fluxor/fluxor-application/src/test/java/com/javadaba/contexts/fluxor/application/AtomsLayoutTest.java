package com.javadaba.contexts.fluxor.application;

import com.javadaba.contexts.fluxor.domain.HarnessItem;
import com.javadaba.contexts.fluxor.domain.HarnessItemKind;
import com.javadaba.contexts.fluxor.domain.HarnessProject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * card://JAVA-2009: a project with the atoms skill gets its roles, mods, steps and flows in the
 * market's layout, with the engine and an inventory byte for byte what {@code marketplace.py} writes.
 * The expected inventory below is Python's {@code json.dumps(indent=2, ensure_ascii=False)} output.
 */
class AtomsLayoutTest {

    private static final String EXPECTED_INVENTORY = """
            {
              "flows": [
                {
                  "name": "ship",
                  "description": "Ship it.",
                  "steps": [
                    {
                      "id": "a",
                      "prompt": "Plan ü"
                    }
                  ]
                }
              ],
              "roles": [
                {
                  "name": "architect",
                  "palette": {
                    "a": 1
                  }
                },
                {
                  "name": "backend-engineer",
                  "icon": "MdStorage",
                  "tags": [
                    "api",
                    "db"
                  ]
                }
              ],
              "mods": [],
              "steps": [
                {
                  "name": "review-diff",
                  "description": "Review."
                }
              ]
            }
            """;

    private final FakeHarnessRepository repo = new FakeHarnessRepository();
    private final HarnessService harness = new HarnessService(repo, new FakeOfficiumProjects());
    private final HarnessSnapshotService snapshots = new HarnessSnapshotService(harness, repo, new HarnessWriter(),
            new FakePackRepository());
    private final UUID account = UUID.randomUUID();
    private HarnessProject project;

    @BeforeEach
    void setUp() {
        atom("ship", HarnessItemKind.DIRECTIVE, "flow",
                "{\n  \"name\": \"ship\",\n  \"description\": \"Ship it.\",\n  \"steps\": [\n    {\n      \"id\": \"a\",\n"
                        + "      \"prompt\": \"Plan ü\"\n    }\n  ]\n}");
        atom("architect", HarnessItemKind.DIRECTIVE, "role",
                "{\n  \"name\": \"architect\",\n  \"palette\": {\n    \"a\": 1\n  }\n}");
        atom("backend-engineer", HarnessItemKind.DIRECTIVE, "role",
                "{\n  \"name\": \"backend-engineer\",\n  \"icon\": \"MdStorage\",\n  \"tags\": [\n    \"api\",\n"
                        + "    \"db\"\n  ]\n}");
        atom("review-diff", HarnessItemKind.SKILL, "step",
                "{\n  \"name\": \"review-diff\",\n  \"description\": \"Review.\"\n}");
        repo.addItem(new HarnessItem("atoms", 1, HarnessItemKind.SKILL, "Atoms", "", "# Atoms\n", Map.of(), "test",
                null, null));
        repo.addItem(new HarnessItem("english", 1, HarnessItemKind.DIRECTIVE, "English", "", "English.\n",
                Map.of("activation", "always"), "test", null, null));
        repo.addItem(new HarnessItem(AtomsLayout.ENGINE, 1, HarnessItemKind.SKILL, "Atoms engine", "", "",
                Map.of("atom", "engine", "files", List.of(
                        Map.of("path", "motor.py", "sha256", "a".repeat(64), "size", 10, "executable", true),
                        Map.of("path", "lexicon.json", "sha256", "b".repeat(64), "size", 20, "executable", false))),
                "test", null, null));
        project = harness.createProject(account, "atoms", null);
    }

    private void atom(String key, HarnessItemKind kind, String atom, String card) {
        repo.addItem(new HarnessItem(key, 1, kind, key, "", "# " + key + "\n\n{{OFFICIUM_PROJECT_ID}} stays.\n",
                Map.of("atom", atom, "card", card, "activation", "always"), "test", null, null));
    }

    private Map<String, HarnessSnapshotService.SnapshotFile> pull(String... keys) {
        harness.update(account, project.id(), harness.project(account, project.id()).project().revision(),
                java.util.Arrays.stream(keys).map(k -> new HarnessService.ItemChange(k, null, null)).toList(),
                List.of());
        return snapshots.snapshot(account, project.id()).files().stream()
                .collect(Collectors.toMap(HarnessSnapshotService.SnapshotFile::path, f -> f));
    }

    @Test
    void theInventoryIsWhatPythonWritesForTheSameCards() {
        var files = pull("atoms", "ship", "architect", "backend-engineer", "review-diff");

        assertThat(files.get(".harness/market/inventory.json").content()).isEqualTo(EXPECTED_INVENTORY);
    }

    @Test
    void eachAtomIsItsMarketFileVerbatimAndTheEngineComesFromTheBlobStore() {
        var files = pull("atoms", "architect", "review-diff", "ship");

        assertThat(files.get(".harness/market/roles/architect.md").content())
                .isEqualTo("# architect\n\n{{OFFICIUM_PROJECT_ID}} stays.\n");
        assertThat(files).containsKeys(".harness/market/steps/review-diff.md", ".harness/market/flows/ship.md");
        assertThat(files.get(".harness/market/motor.py").content()).isNull();
        assertThat(files.get(".harness/market/motor.py").sha256()).isEqualTo("a".repeat(64));
        assertThat(files.get(".harness/market/motor.py").executable()).isTrue();
        assertThat(files).doesNotContainKeys(".harness/rules/architect.md", ".harness/skills/review-diff/SKILL.md",
                ".harness/rules/ship.md");
    }

    @Test
    void atomsStayOutOfTheAgentsBlockWhileOtherDirectivesStay() {
        var block = pull("atoms", "architect", "english").get("AGENTS.md").content();

        assertThat(block).contains("@.harness/rules/english.md").doesNotContain("architect");
    }

    @Test
    void withoutTheAtomsSkillARoleIsTheUsualAlwaysReadDirective() {
        var files = pull("architect", "review-diff");

        assertThat(files).containsKeys(".harness/rules/architect.md", ".harness/skills/review-diff/SKILL.md");
        assertThat(files.keySet()).noneMatch(path -> path.startsWith(".harness/market/"));
    }
}
