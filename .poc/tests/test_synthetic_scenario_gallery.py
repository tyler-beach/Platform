from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github" / "demo"))

from build_scenario_gallery import build_gallery, eligible_run, project_live_bundle, verify_fixture_artifact
from test_functional_analysis_ledger import expected_context, make_bundle
import reconcile_functional_analysis as reconciler


class SyntheticScenarioGalleryTests(unittest.TestCase):
    def test_builds_all_nine_validated_workflow_scenarios_with_pinned_inputs(self):
        gallery = build_gallery(ROOT)
        self.assertEqual(gallery["schema_version"], "adr-synthetic-gallery-v1")
        self.assertEqual(gallery["scenario_count"], 9)
        scenarios = gallery["scenarios"]
        self.assertEqual(len(scenarios), 9)
        self.assertEqual(len({scenario["id"] for scenario in scenarios}), 9)
        for scenario in scenarios:
            self.assertEqual(scenario["validation_status"], "passed")
            self.assertTrue(all(check["passed"] for check in scenario["validation_checks"]))
            self.assertEqual(scenario["outcome"], {
                "deviation": "supported_deviation",
                "aligned": "no_deviation_found",
                "insufficient-evidence": "inconclusive",
            }[scenario["sample_case"]])
            self.assertTrue(scenario["stages"])
            self.assertTrue(scenario["evidence"])
            for artifact in scenario["artifacts"]:
                fixture = verify_fixture_artifact(ROOT, {**artifact, "original_fixture_path": artifact["path"]})
                self.assertEqual(artifact["text"], fixture.read_text(encoding="utf-8"))
                self.assertEqual(artifact["sha256"], hashlib.sha256(fixture.read_bytes()).hexdigest())

    def test_rejects_artifact_path_outside_synthetic_fixture_tree(self):
        with self.assertRaisesRegex(ValueError, "approved synthetic fixture"):
            verify_fixture_artifact(ROOT, {
                "role": "implementation", "original_fixture_path": ".poc/fixtures/go/main.go",
                "sha256": "0" * 64, "byte_length": 0,
            })

    def test_projects_only_validated_live_synthetic_workflow_artifact_inputs(self):
        scenario = project_live_bundle(ROOT, make_bundle(), expected_context(), {
            "created_at": "2026-10-17T12:00:00Z", "updated_at": "2026-10-17T12:01:00Z",
        })
        self.assertEqual(scenario["id"], "live-123-2")
        self.assertEqual(scenario["record_type"], "workflow_run")
        self.assertEqual(scenario["outcome"], "supported_deviation")
        self.assertEqual([item["role"] for item in scenario["artifacts"]], ["adr", "implementation", "diff"])
        self.assertEqual(scenario["artifacts"][1]["text"], "callProvider()\n")
        self.assertEqual(scenario["run_url"], "https://github.com/example-org/adr-platform/actions/runs/123")

    def test_rejects_live_artifact_with_fixture_path_not_matching_its_selected_case(self):
        with self.assertRaisesRegex(ValueError, "expected synthetic fixture path"):
            project_live_bundle(ROOT, make_bundle(original_code_path=".poc/fixtures/go/main.go"),
                                expected_context(), {"created_at": "", "updated_at": ""})

    def test_live_run_filter_requires_default_branch_successful_dispatch(self):
        eligible = {"workflow_id": 44, "event": "workflow_dispatch", "head_branch": "main",
                    "status": "completed", "conclusion": "success"}
        self.assertTrue(eligible_run(eligible, 44, "main"))
        for change in ({"event": "pull_request"}, {"head_branch": "feature"},
                       {"conclusion": "failure"}, {"workflow_id": 45}):
            with self.subTest(change=change):
                self.assertFalse(eligible_run({**eligible, **change}, 44, "main"))

    def test_live_import_revalidates_workflow_attempt_before_downloading_bundle(self):
        bundle = make_bundle()

        class FakeAPI:
            def __init__(self, token, repository):
                self.token = token
                self.repository = repository
                self.artifact_lookups = 0

            def get_json(self, path, query=None):
                if path == "/":
                    return {"full_name": self.repository, "default_branch": "main"}
                if path == "/actions/workflows/functional-analysis-demo.yml":
                    return {"id": 44, "path": reconciler.WORKFLOW_PATH}
                if path == "/actions/workflows/44/runs":
                    return {"workflow_runs": [{"id": 123, "run_attempt": 2, "workflow_id": 44,
                        "event": "workflow_dispatch", "head_branch": "main", "status": "completed",
                        "conclusion": "success", "head_sha": "a" * 40}], "total_count": 1}
                if path == "/actions/runs/123/attempts/2":
                    return {"id": 123, "run_attempt": 2, "workflow_id": 44, "event": "workflow_dispatch",
                        "head_branch": "main", "status": "completed", "conclusion": "success", "head_sha": "a" * 40}
                if path == "/actions/runs/123/artifacts":
                    self.artifact_lookups += 1
                    return {"artifacts": [{"id": 789, "name": "functional-analysis-demo-123-2",
                        "expired": False, "size_in_bytes": len(bundle),
                        "digest": "sha256:" + hashlib.sha256(bundle).hexdigest(), "workflow_run": {"id": 123}}]}
                raise AssertionError(f"unexpected GitHub API path: {path}")

            def download_artifact(self, artifact_id, size, digest):
                self.assertion = (artifact_id, size, digest)
                return bundle

        with patch.object(reconciler, "GitHubAPI", FakeAPI):
            scenarios, status = __import__("build_scenario_gallery").collect_live_scenarios(
                ROOT, "example-org/adr-platform", "synthetic-test-token")
        self.assertEqual(status["imported"], 1)
        self.assertEqual(status["rejected"], 0)
        self.assertEqual(scenarios[0]["id"], "live-123-2")


if __name__ == "__main__":
    unittest.main()
