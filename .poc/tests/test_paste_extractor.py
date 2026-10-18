from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "requirement_engine"))
sys.path.insert(0, str(ROOT / ".poc" / "issue_analyze"))

import evaluate_package
import issue_package
import paste_extractor

FIXTURES = ROOT / ".poc" / "issue_analyze" / "fixtures"


class PasteExtractorTests(unittest.TestCase):
    def test_messy_markdown_extracts_confident_claims(self):
        text = (FIXTURES / "real_paste_tech_spec.md").read_text(encoding="utf-8")
        package = {
            "schema_version": "pathfinder-evidence-package-v1",
            "package_id": "messy-md",
            "tech_spec": {
                "artifact_id": "tech_spec",
                "path": "issue/tech-spec.md",
                "content": text,
            },
            "observations": [],
        }
        obs = paste_extractor.extract_observations(package)
        by_pred = {item["predicate"]: item["value"] for item in obs}
        self.assertEqual(by_pred["session.ttl_seconds"], 720)
        self.assertEqual(by_pred["security.encryption_at_rest.enabled"], True)
        self.assertEqual(by_pred["security.tls_policy.id"], "legacy-ssl")
        self.assertEqual(by_pred["kubernetes.deployment.replicas"], 2)
        self.assertEqual(by_pred["kubernetes.readiness_probe.present"], True)
        self.assertEqual(by_pred["messaging.consumer.max_retries"], 25)
        self.assertEqual(by_pred["messaging.dlq.present"], False)
        self.assertEqual(by_pred["api.rate_limit.enabled"], True)
        self.assertEqual(by_pred["privacy.sensitive_log.present"], True)
        self.assertEqual(by_pred["supply_chain.license.id"], "MIT")
        # Silence must not invent a false secret observation from markdown alone.
        self.assertNotIn("security.secret_in_source.present", by_pred)

    def test_go_and_python_detect_secrets_and_ttl(self):
        go = (FIXTURES / "real_paste_session.go").read_text(encoding="utf-8")
        py = (FIXTURES / "real_paste_session.py").read_text(encoding="utf-8")
        for lang, content, path in (
            ("go", go, "issue/sample.go"),
            ("python", py, "issue/sample.py"),
        ):
            package = {
                "schema_version": "pathfinder-evidence-package-v1",
                "package_id": f"messy-{lang}",
                "code": [{
                    "artifact_id": "code-0",
                    "path": path,
                    "content": content,
                }],
                "observations": [],
            }
            obs = paste_extractor.extract_observations(package)
            by_pred = {item["predicate"]: item["value"] for item in obs}
            self.assertEqual(by_pred.get("session.ttl_seconds"), 720, lang)
            self.assertIs(by_pred.get("security.secret_in_source.present"), True, lang)
            self.assertIs(by_pred.get("api.auth_middleware.present"), True, lang)

    def test_no_secret_match_does_not_emit_false(self):
        package = {
            "schema_version": "pathfinder-evidence-package-v1",
            "package_id": "clean",
            "code": [{
                "artifact_id": "code-0",
                "path": "issue/sample.py",
                "content": "def add(a, b):\n    return a + b\n",
            }],
            "observations": [],
        }
        obs = paste_extractor.extract_observations(package)
        self.assertFalse(any(item["predicate"] == "security.secret_in_source.present" for item in obs))

    def test_conflicting_ttl_values_drop(self):
        text = "Sessions expire after 12 minutes.\nAlso session TTL of 5 minutes for mobile."
        package = {
            "schema_version": "pathfinder-evidence-package-v1",
            "package_id": "conflict",
            "tech_spec": {"artifact_id": "tech_spec", "path": "t.md", "content": text},
            "observations": [],
        }
        obs = paste_extractor.extract_observations(package)
        self.assertFalse(any(item["predicate"] == "session.ttl_seconds" for item in obs))

    def test_evaluate_package_without_hand_written_observations(self):
        text = (FIXTURES / "real_paste_tech_spec.md").read_text(encoding="utf-8")
        go = (FIXTURES / "real_paste_session.go").read_text(encoding="utf-8")
        package = {
            "schema_version": "pathfinder-evidence-package-v1",
            "package_id": "paste-eval",
            "scope": {"domains": ["identity", "security", "reliability", "messaging", "api", "privacy"]},
            "tech_spec": {"artifact_id": "tech_spec", "path": "issue/tech-spec.md", "content": text},
            "code": [{"artifact_id": "code-0", "path": "issue/sample.go", "content": go}],
        }
        report = evaluate_package.evaluate_package(package)
        self.assertGreater(report["observation_count"], 0)
        self.assertIsNotNone(report.get("extraction"))
        confident = report["counts"]["supported_deviation"] + report["counts"]["no_deviation_found"]
        self.assertGreater(confident, 0)
        self.assertIn(report["aggregate_status"], {"mixed", "deviations_found", "all_aligned"})

    def test_issue_intake_paste_only_no_observations_field(self):
        body = (FIXTURES / "paste_only_issue_body.md").read_text(encoding="utf-8")
        package = issue_package.package_from_issue(body, issue_number=123)
        self.assertTrue(package["observations"])
        self.assertEqual(package["extraction"]["extractor"], "paste_heuristic_v1")
        report = evaluate_package.evaluate_package(package)
        comment = issue_package.render_result_comment(
            report, run_url="https://example.invalid/run", package=package,
        )
        self.assertIn("Paste extractor", comment)
        self.assertNotIn("sk-live-checkout-demo-key", comment)
        self.assertNotIn("Sessions expire after 12 minutes", comment)


if __name__ == "__main__":
    unittest.main()
