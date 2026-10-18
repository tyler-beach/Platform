from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".poc" / "review_sampling"))
from github_issue_intake import build_frame, build_issue, prepare


class GitHubIssueIntakeTests(unittest.TestCase):
    def report(self):
        return {
            "catalog_hash": "catalog-sha",
            "results": [
                {
                    "event_id": "SCOPE-1",
                    "event_summary": "Synthetic handler call",
                    "scope": {"disposition": "in_scope"},
                    "comparison": {"overall_result": "deviation"},
                    "adr_matches": [{
                        "adr_id": "ADR-001",
                        "adr_version": "2",
                        "title": "Async provider",
                        "comparison_result": "deviation",
                        "candidate_explanation": "Synthetic cue matched.",
                        "requirement_evidence": {"evidence_id": "ADR-001:REQUIREMENT", "path": "docs/adr.md"},
                        "adr_source": {"path": "docs/adr.md", "sha256": "adr-sha", "chunk_id": "ADR-001#2"},
                        "source_observations": [{"evidence_id": "EV-1", "path": "src/handler.go", "line": 10, "excerpt": "private source excerpt", "excerpt_sha256": "obs-sha"}],
                        "evidence_links": [{"link_id": "L-1", "requirement_evidence_id": "ADR-001:REQUIREMENT", "observation_evidence_id": "EV-1", "relationship": "contradicts"}],
                    }],
                },
                {
                    "event_id": "SCOPE-2",
                    "event_summary": "No match synthetic case",
                    "scope": {"disposition": "out_of_scope", "reason": "No applicable active ADR."},
                    "comparison": {"overall_result": "no_applicable_adr"},
                    "adr_matches": [],
                },
            ],
        }

    def test_frame_has_requirement_level_and_no_match_units(self):
        frame, details = build_frame(self.report())
        self.assertEqual(len(frame), 2)
        self.assertEqual({row["outcome"] for row in frame}, {"deviation", "no_deviation"})
        no_match = next(row for row in frame if "NO-APPLICABLE-ADR" in row["unit_id"])
        self.assertEqual(details[no_match["unit_id"]]["comparison_result"], "no_applicable_adr")

    def test_issue_keeps_refs_not_source_excerpt(self):
        report = self.report()
        frame, details = build_frame(report)
        row = frame[0]
        selection = {"selection_reason": "STRATIFIED_RANDOM", "evidence_band": "high", "inclusion_probability": 1.0, "design_weight": 1.0}
        _, body = build_issue(row["unit_id"], selection, details[row["unit_id"]], "https://example.invalid/run")
        self.assertIn("EV-1", body)
        self.assertIn("obs-sha", body)
        self.assertNotIn("private source excerpt", body)
        self.assertIn("not a production-quality conclusion", body)
        self.assertIn("needs_adjudication", body)

    def test_prepare_is_deterministic_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            batch_path = root / "batch.json"
            report_path.write_text(json.dumps(self.report()), encoding="utf-8")
            first, _ = prepare(report_path, batch_path, seed="fixed-seed", per_stratum=1)
            original = batch_path.read_text(encoding="utf-8")
            second, _ = prepare(report_path, batch_path, seed="fixed-seed", per_stratum=1)
            self.assertEqual(first["selected_review_units"], second["selected_review_units"])
            self.assertEqual(original, batch_path.read_text(encoding="utf-8"))
            self.assertEqual(first["frame"]["sha256"], second["frame"]["sha256"])

    def test_unknown_outcome_becomes_inconclusive(self):
        report = self.report()
        report["results"][0]["adr_matches"][0]["comparison_result"] = "new_unrecognized_state"
        frame, _ = build_frame(report)
        self.assertEqual(frame[0]["outcome"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
