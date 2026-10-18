from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "issue_analyze"))

import issue_body
import issue_package


class IssueBodyTests(unittest.TestCase):
    def test_build_body_has_attestation_and_sections(self):
        body = issue_body.build_issue_body(
            tech_spec="Sessions expire after 12 minutes.",
            code='package main\n',
            domains="identity, security",
            attested=True,
        )
        self.assertIn("[X]", body)
        self.assertIn("### Tech spec (markdown)", body)
        self.assertIn("Sessions expire after 12 minutes.", body)
        self.assertIn("package main", body)
        self.assertIn("identity, security", body)

    def test_validate_prepare_requires_attestation_and_content(self):
        self.assertIsNotNone(issue_body.validate_prepare(tech_spec="x", code="", attested=False))
        self.assertIsNotNone(issue_body.validate_prepare(tech_spec="", code="", attested=True))
        self.assertIsNone(issue_body.validate_prepare(tech_spec="x", code="", attested=True))

    def test_prepared_body_is_accepted_by_intake(self):
        body = issue_body.build_issue_body(
            tech_spec=(ROOT / ".poc/issue_analyze/fixtures/real_paste_tech_spec.md").read_text(encoding="utf-8"),
            code=(ROOT / ".poc/issue_analyze/fixtures/real_paste_session.go").read_text(encoding="utf-8"),
            domains="identity, security",
            attested=True,
        )
        package = issue_package.package_from_issue(body, issue_number=77)
        self.assertTrue(package["observations"])
        self.assertEqual(package["extraction"]["extractor"], "paste_heuristic_v1")

    def test_url_plan_switches_when_body_is_large(self):
        small = issue_body.github_new_issue_url(
            "tyler-beach/Platform",
            title="[Pathfinder analyze] small",
            body="short body",
        )
        self.assertEqual(small["mode"], "url_body")
        self.assertFalse(small["copy_required"])
        large = issue_body.github_new_issue_url(
            "tyler-beach/Platform",
            title="[Pathfinder analyze] large",
            body="x" * (issue_body.MAX_URL_BODY_CHARS + 10),
        )
        self.assertEqual(large["mode"], "copy_then_template")
        self.assertTrue(large["copy_required"])
        self.assertIn("template=pathfinder-analyze.yml", large["url"])


if __name__ == "__main__":
    unittest.main()
