from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github" / "demo"))
from review_issue import render_issue


class ReviewIssueTests(unittest.TestCase):
    def fixture(self):
        return (
            {"run_id":"1234","run_attempt":"1","comparison":"code-diff","sample_case":"deviation",
             "language":"go","status":"passed","actual_outcome":"supported_deviation","evidence_item_count":1},
            {"run_id":"1234","run_attempt":"1","comparison":"code-diff","sample_case":"deviation",
             "language":"go","artifacts":[{"artifact_id":"ART-1","role":"implementation","version":"sha256:abc"}]},
            {"items":[{"evidence_id":"EV-1","evidence_type":"call_site","source_path":"src/demo.go",
                       "locator":{"line_start":4}}]},
            {"provider":"mock","model_id":"synthetic-fixture","candidate":{"outcome":"supported_deviation",
              "evidence_ids":["EV-1"],"rationale":"Synthetic example rationale."}},
            {"status":"passed","checks":[{"name":"evidence_refs_valid","passed":True}]},
        )

    def test_render_is_provenance_bound_and_excludes_raw_source(self):
        report, manifest, evidence, model, validation = self.fixture()
        title, body = render_issue(report, manifest, evidence, model, validation,
                                   "https://github.com/owner/repo/actions/runs/1234")
        self.assertIn("run 1234", title)
        self.assertIn("EV-1", body)
        self.assertIn("sha256:abc", body)
        self.assertIn("not a production finding", body)
        self.assertIn("needs_adjudication", body)
        self.assertNotIn("source_excerpt", body)
        self.assertNotIn("raw_prompt", body)

    def test_unvalidated_run_cannot_open_review_issue(self):
        report, manifest, evidence, model, validation = self.fixture()
        validation["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "did not pass validation"):
            render_issue(report, manifest, evidence, model, validation, "https://example.invalid/run")

    def test_missing_run_identity_rejected(self):
        report, manifest, evidence, model, validation = self.fixture()
        report["run_id"] = ""
        with self.assertRaisesRegex(ValueError, "run_id"):
            render_issue(report, manifest, evidence, model, validation, "https://example.invalid/run")


if __name__ == "__main__":
    unittest.main()
