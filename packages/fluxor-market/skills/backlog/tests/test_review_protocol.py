"""The review protocol (references/review-protocol.md) and the review roles say the same things, and say the
whole of them: the evidence before the author's words, the blocking bar stated once, the lens table naming
roles that exist, and the comment shape the board reads."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
MARKET = SKILL.parents[1] / "market"
ROLES = MARKET / "roles"
PROTOCOL = (SKILL / "references" / "review-protocol.md").read_text()
SKILL_MD = (SKILL / "SKILL.md").read_text()
ADAPTER = (SKILL / "references" / "adapter-officium.md").read_text()
SIGNALS = (
    "touches-auth-permissions-or-personal-data",
    "touches-ui",
    "touches-hot-paths-or-heavy-queries",
    "touches-data-schema",
    "touches-infrastructure",
)


def phase_review_roles() -> list[str]:
    roles = []
    for manifest in sorted(ROLES.glob("*.json")):
        data = json.loads(manifest.read_text())
        if "phase-review" in data.get("tags", []):
            roles.append(manifest.stem)
    return roles


def lens_table_roles() -> list[str]:
    table = PROTOCOL.split("## 3.", 1)[1].split("## 4.", 1)[0]
    rows = [line for line in table.splitlines() if line.startswith("| ") and "---" not in line]
    # The first row is the header; the role is the third column, without a domain in brackets.
    return [re.split(r"\s*\(", row.split("|")[3].strip())[0].strip() for row in rows[1:]]


class ReviewProtocol(unittest.TestCase):
    def test_the_evidence_comes_before_the_authors_claims(self):
        evidence = PROTOCOL.index("Evidence pass")
        claims = PROTOCOL.index("Then read the author's comments")
        self.assertLess(evidence, claims)

    def test_the_blocking_bar_is_stated_once_across_the_documents(self):
        sentence = "The blocking threshold is 80"
        documents = [PROTOCOL, SKILL_MD, ADAPTER]
        documents += [role.read_text() for role in ROLES.glob("*.md") if role.stem in phase_review_roles()]
        self.assertEqual(sum(text.count(sentence) for text in documents), 1)
        for text in documents[1:]:
            self.assertNotRegex(text, r"threshold[^.\n]{0,40}\b80\b")

    def test_every_phase_review_role_carries_the_order_and_the_bar(self):
        roles = phase_review_roles()
        self.assertTrue(roles, "no phase-review roles found")
        for role in roles:
            text = (ROLES / f"{role}.md").read_text()
            before_acting = re.search(r"^- \*\*Before acting:\*\*(.*)$", text, re.M)
            self.assertIsNotNone(before_acting, f"{role}: no Before acting bullet")
            # The judged source comes last: the author's comments for a reviewer, the report's recommendation
            # for findings-evaluator, which judges a spike's report.
            self.assertIn(" last;", before_acting.group(1), role)
            self.assertIn("A blocking finding carries its evidence and a confidence", text, role)
            data = json.loads((ROLES / f"{role}.json").read_text())
            self.assertIn("backlog@1", data["requires"]["atoms"], role)

    def test_the_lens_table_names_roles_that_exist(self):
        roles = lens_table_roles()
        self.assertTrue(roles)
        for role in roles:
            self.assertTrue((ROLES / f"{role}.json").exists(), f"lens table names {role}, which is not a role")

    def test_the_lens_table_names_the_five_signals(self):
        table = PROTOCOL.split("## 3.", 1)[1].split("## 4.", 1)[0]
        for signal in SIGNALS:
            self.assertIn(f"`{signal}`", table)

    def test_the_comment_keeps_the_shape_the_board_reads(self):
        self.assertIn("Rules checked:\n| rule | verdict | evidence |", PROTOCOL)
        for label in ("Evidence:", "Lenses:", "Author's comment:", "Findings:"):
            self.assertIn(label, PROTOCOL)


if __name__ == "__main__":
    unittest.main()
