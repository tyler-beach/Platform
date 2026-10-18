from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "issue_analyze"))

import issue_package  # noqa: E402

FIXTURE = ROOT / ".poc" / "issue_analyze" / "fixtures" / "sample_issue_body.md"


def _fields_body(*, attested: bool = True, observations: str | None = None) -> str:
    check = "[X]" if attested else "[ ]"
    obs = observations if observations is not None else json.dumps([
        {
            "evidence_id": "EV-TTL",
            "predicate": "session.ttl_seconds",
            "subject": "session",
            "value": 720,
            "locator": {"kind": "tech_spec_claim", "value": "session.ttl_seconds"},
        }
    ], indent=2)
    return f"""### Public / synthetic attestation

- {check} I attest this submission contains only synthetic or explicitly public content and no secrets or confidential source.

### Domains (optional scope filter)

identity

### Tech spec (markdown)

# Spec
Sessions expire after 12 minutes.

### Sample code

const x = 1;

### Observations JSON array

{obs}
"""


class IssuePackageTests(unittest.TestCase):
    def test_sample_issue_package_evaluates(self):
        body = FIXTURE.read_text(encoding="utf-8")
        package = issue_package.package_from_issue(body, issue_number=99)
        self.assertEqual(package["schema_version"], "pathfinder-evidence-package-v1")
        self.assertEqual(package["package_id"], "issue-fixture-session-service")
        # Placeholder digests must be rewritten from content.
        self.assertRegex(package["tech_spec"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(package["tech_spec"]["sha256"], "placeholder")
        report = issue_package.evaluate_package.evaluate_package(package)
        self.assertIn(report["aggregate_status"], {
            "mixed", "all_aligned", "deviations_found", "insufficient_coverage", "not_applicable_only",
        })
        self.assertGreater(report["counts"]["no_deviation_found"] + report["counts"]["supported_deviation"], 0)

    def test_missing_attestation_fails_closed(self):
        with self.assertRaises(issue_package.IntakeError) as ctx:
            issue_package.package_from_issue(_fields_body(attested=False), issue_number=1)
        self.assertIn("attestation", str(ctx.exception).lower())

    def test_fields_assemble_package(self):
        package = issue_package.package_from_issue(_fields_body(), issue_number=7)
        self.assertEqual(package["package_id"], "github-issue-7")
        self.assertEqual(package["scope"]["domains"], ["identity"])
        self.assertEqual(package["observations"][0]["predicate"], "session.ttl_seconds")
        self.assertTrue(package["tech_spec"]["content"].startswith("# Spec"))

    def test_result_comment_omits_source_body(self):
        package = issue_package.package_from_issue(FIXTURE.read_text(encoding="utf-8"), issue_number=3)
        report = issue_package.evaluate_package.evaluate_package(package)
        comment = issue_package.render_result_comment(
            report, run_url="https://example.invalid/run/1", package=package,
        )
        self.assertIn("Aggregate status", comment)
        self.assertIn(report["aggregate_status"], comment)
        self.assertIn(report["report_sha256"], comment)
        self.assertNotIn(package["tech_spec"]["content"], comment)
        self.assertIn("Evidence boundary", comment)

    def test_cli_writes_report_and_comment_without_gh(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            body = work / "body.md"
            body.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            rc = issue_package.main([
                "--issue-number", "42",
                "--body-file", str(body),
                "--work-dir", str(work / "out"),
                "--run-url", "https://example.invalid/run/42",
            ])
            self.assertEqual(rc, 0)
            report = json.loads((work / "out" / "report.json").read_text(encoding="utf-8"))
            comment = (work / "out" / "comment.md").read_text(encoding="utf-8")
            self.assertIn("aggregate_status", report)
            self.assertNotIn("Sessions expire after 12 minutes", comment)

    def test_invalid_observations_error_comment(self):
        bad = _fields_body(observations="not-json")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            body = work / "body.md"
            body.write_text(bad, encoding="utf-8")
            rc = issue_package.main([
                "--issue-number", "5",
                "--body-file", str(body),
                "--work-dir", str(work / "out"),
                "--run-url", "https://example.invalid/run/5",
            ])
            self.assertEqual(rc, 2)
            comment = (work / "out" / "comment.md").read_text(encoding="utf-8")
            self.assertIn("failed", comment.lower())
            self.assertIn("observations", comment.lower())


if __name__ == "__main__":
    unittest.main()
